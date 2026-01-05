#!/usr/bin/env python3
"""
Filter Pipeline
Coordinates all trade filters in sequence
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

from .market_filter import MarketFilter
from .size_filter import SizeFilter
from .lp_detector import LPDetector

logger = logging.getLogger(__name__)


class FilterPipeline:
    """Coordinate multiple filters in a pipeline"""

    def __init__(
        self,
        market_filter: Optional[MarketFilter] = None,
        size_filter: Optional[SizeFilter] = None,
        lp_detector: Optional[LPDetector] = None
    ):
        """
        Initialize filter pipeline

        Args:
            market_filter: Market filter instance
            size_filter: Size filter instance
            lp_detector: LP detector instance
        """
        self.market_filter = market_filter
        self.size_filter = size_filter
        self.lp_detector = lp_detector

        # Statistics
        self.stats = {
            "total_trades": 0,
            "passed_all_filters": 0,
            "filtered_by_market": 0,
            "filtered_by_size": 0,
            "filtered_by_lp": 0,
            "filter_reasons": {}
        }

        enabled_filters = []
        if market_filter:
            enabled_filters.append("market")
        if size_filter:
            enabled_filters.append("size")
        if lp_detector:
            enabled_filters.append("lp")

        logger.info(f"FilterPipeline initialized - Enabled filters: {', '.join(enabled_filters)}")

    def process_trade(self, trade: Dict[str, Any]) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Process a trade through all filters

        Args:
            trade: Trade dictionary

        Returns:
            Tuple of (should_process: bool, filter_reason: str, enriched_trade: dict)
        """
        self.stats["total_trades"] += 1

        enriched_trade = trade.copy()
        enriched_trade["filter_results"] = {}

        # 1. Market Filter
        if self.market_filter:
            should_process, reason = self.market_filter.should_process_trade(trade)
            enriched_trade["filter_results"]["market"] = {
                "passed": should_process,
                "reason": reason
            }

            if not should_process:
                self.stats["filtered_by_market"] += 1
                self._record_filter_reason("market", reason)
                logger.debug(f"Trade filtered by market: {reason}")
                return False, f"Market filter: {reason}", enriched_trade

        # 2. Size Filter
        if self.size_filter:
            should_process, reason = self.size_filter.should_process_trade(trade)
            trade_value = self.size_filter.get_trade_value(trade)
            enriched_trade["filter_results"]["size"] = {
                "passed": should_process,
                "reason": reason,
                "value_usd": trade_value
            }

            if not should_process:
                self.stats["filtered_by_size"] += 1
                self._record_filter_reason("size", reason)
                logger.debug(f"Trade filtered by size: {reason}")
                return False, f"Size filter: {reason}", enriched_trade

        # 3. LP Detector
        if self.lp_detector:
            should_process, reason = self.lp_detector.should_process_trade(trade)
            enriched_trade["filter_results"]["lp"] = {
                "passed": should_process,
                "reason": reason
            }

            if not should_process:
                self.stats["filtered_by_lp"] += 1
                self._record_filter_reason("lp", reason)
                logger.debug(f"Trade filtered by LP: {reason}")
                return False, f"LP filter: {reason}", enriched_trade

        # All filters passed
        self.stats["passed_all_filters"] += 1
        logger.info(
            f"✓ Trade passed all filters - "
            f"Value: ${enriched_trade.get('value_usd', 0):.2f}, "
            f"Market: {trade.get('market_id', 'unknown')[:10]}..."
        )

        return True, None, enriched_trade

    def _record_filter_reason(self, filter_name: str, reason: Optional[str]):
        """
        Record why a trade was filtered for statistics

        Args:
            filter_name: Name of the filter
            reason: Reason string
        """
        key = f"{filter_name}: {reason}" if reason else filter_name

        if key not in self.stats["filter_reasons"]:
            self.stats["filter_reasons"][key] = 0

        self.stats["filter_reasons"][key] += 1

    def get_stats(self) -> Dict[str, Any]:
        """
        Get pipeline statistics

        Returns:
            Stats dictionary
        """
        total = self.stats["total_trades"]
        passed = self.stats["passed_all_filters"]

        pass_rate = (passed / total * 100) if total > 0 else 0

        stats = {
            "total_trades_processed": total,
            "passed_all_filters": passed,
            "pass_rate_pct": round(pass_rate, 2),
            "filtered_by_market": self.stats["filtered_by_market"],
            "filtered_by_size": self.stats["filtered_by_size"],
            "filtered_by_lp": self.stats["filtered_by_lp"],
            "top_filter_reasons": self._get_top_filter_reasons(5)
        }

        # Add individual filter stats
        if self.market_filter:
            stats["market_filter"] = self.market_filter.get_stats()

        if self.size_filter:
            stats["size_filter"] = self.size_filter.get_stats()

        if self.lp_detector:
            stats["lp_detector"] = self.lp_detector.get_stats()

        return stats

    def _get_top_filter_reasons(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get top reasons for filtering

        Args:
            limit: Number of top reasons to return

        Returns:
            List of reason dictionaries
        """
        sorted_reasons = sorted(
            self.stats["filter_reasons"].items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [
            {"reason": reason, "count": count}
            for reason, count in sorted_reasons[:limit]
        ]

    def reset_stats(self):
        """Reset pipeline statistics"""
        self.stats = {
            "total_trades": 0,
            "passed_all_filters": 0,
            "filtered_by_market": 0,
            "filtered_by_size": 0,
            "filtered_by_lp": 0,
            "filter_reasons": {}
        }
        logger.info("Pipeline statistics reset")

    def clear_caches(self):
        """Clear all filter caches"""
        if self.market_filter:
            self.market_filter.clear_cache()

        if self.lp_detector:
            self.lp_detector.clear_cache()

        logger.info("All filter caches cleared")


def create_filter_pipeline(config: Dict[str, Any], api_client) -> FilterPipeline:
    """
    Factory function to create filter pipeline from configuration

    Args:
        config: Configuration dictionary
        api_client: Polymarket API client instance

    Returns:
        Configured FilterPipeline instance
    """
    filter_config = config.get("filters", {})

    # Create market filter
    market_filter = MarketFilter(
        api_client=api_client,
        excluded_categories=filter_config.get("excluded_categories", []),
        market_timeframe_days=filter_config.get("market_timeframe_days", 30)
    )

    # Create size filter
    size_filter = SizeFilter(
        min_trade_size_usd=filter_config.get("min_trade_size_usd", 2000)
    )

    # Create LP detector
    lp_detector = LPDetector(
        api_client=api_client,
        balance_threshold=0.4,  # 40-60% split
        cache_ttl=300  # 5 minutes
    )

    # Create pipeline
    pipeline = FilterPipeline(
        market_filter=market_filter,
        size_filter=size_filter,
        lp_detector=lp_detector
    )

    logger.info("Filter pipeline created from configuration")

    return pipeline
