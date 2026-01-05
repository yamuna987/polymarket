#!/usr/bin/env python3
"""
Market Filter
Filters trades based on market category and timeframe
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MarketFilter:
    """Filter trades by market category and timeframe"""

    def __init__(
        self,
        api_client,
        excluded_categories: List[str] = None,
        market_timeframe_days: int = 30
    ):
        """
        Initialize market filter

        Args:
            api_client: Polymarket API client instance
            excluded_categories: List of categories to exclude (e.g., ['sports', 'crypto'])
            market_timeframe_days: Only track markets ending within N days
        """
        self.api_client = api_client
        self.excluded_categories = [cat.lower() for cat in (excluded_categories or [])]
        self.market_timeframe_days = market_timeframe_days

        # Cache market metadata
        self.market_cache = {}

        logger.info(
            f"MarketFilter initialized - Excluded: {self.excluded_categories}, "
            f"Timeframe: {market_timeframe_days} days"
        )

    def should_process_trade(self, trade: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Determine if a trade should be processed based on market criteria

        Args:
            trade: Trade dictionary with market_id/condition_id

        Returns:
            Tuple of (should_process: bool, reason: str)
        """
        market_id = trade.get("market_id") or trade.get("condition_id")

        if not market_id:
            return False, "No market ID found"

        # Get market metadata
        market_info = self._get_market_info(market_id)

        if not market_info:
            logger.debug(f"Market info not found for {market_id}, allowing by default")
            return True, None

        # Check category filter
        if self.excluded_categories:
            market_category = (market_info.get("category") or "").lower()

            # Also check tags for category matching
            tags = market_info.get("tags", [])
            if isinstance(tags, list):
                tag_categories = [tag.lower() for tag in tags if isinstance(tag, str)]
            else:
                tag_categories = []

            for excluded in self.excluded_categories:
                if excluded in market_category:
                    return False, f"Excluded category: {market_category}"

                # Check if any tags match excluded categories
                for tag in tag_categories:
                    if excluded in tag:
                        return False, f"Excluded tag: {tag}"

        # Check timeframe filter
        if self.market_timeframe_days > 0:
            end_date = market_info.get("end_date") or market_info.get("endDate")

            if end_date:
                try:
                    # Parse end date (could be ISO string or timestamp)
                    if isinstance(end_date, str):
                        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    elif isinstance(end_date, (int, float)):
                        end_dt = datetime.fromtimestamp(end_date / 1000)
                    else:
                        end_dt = end_date

                    # Calculate days until market ends
                    now = datetime.now(end_dt.tzinfo) if end_dt.tzinfo else datetime.now()
                    days_until_end = (end_dt - now).days

                    if days_until_end > self.market_timeframe_days:
                        return False, f"Market ends too far out: {days_until_end} days"

                    if days_until_end < 0:
                        return False, f"Market already ended {abs(days_until_end)} days ago"

                except Exception as e:
                    logger.warning(f"Error parsing end date for market {market_id}: {e}")

        return True, None

    def _get_market_info(self, market_id: str) -> Optional[Dict]:
        """
        Get market information with caching

        Args:
            market_id: Market/condition ID

        Returns:
            Market info dictionary or None
        """
        # Check cache first
        if market_id in self.market_cache:
            return self.market_cache[market_id]

        # Fetch from API
        try:
            # Try searching for the market
            # Note: This is a simplified approach - in production you'd want to
            # use a more efficient endpoint or maintain a market database
            markets = self.api_client.get_markets(limit=1)

            # For now, we'll just cache an empty dict to avoid repeated API calls
            # In a production system, you'd query the specific market or maintain
            # a local database of market metadata
            self.market_cache[market_id] = {}

            logger.debug(f"Cached empty market info for {market_id}")
            return {}

        except Exception as e:
            logger.error(f"Error fetching market info for {market_id}: {e}")
            return None

    def get_market_metadata(self, market_id: str) -> Dict[str, Any]:
        """
        Get detailed market metadata for enrichment

        Args:
            market_id: Market/condition ID

        Returns:
            Market metadata dictionary
        """
        info = self._get_market_info(market_id)

        return {
            "market_id": market_id,
            "category": info.get("category") if info else None,
            "tags": info.get("tags") if info else None,
            "end_date": info.get("end_date") or info.get("endDate") if info else None,
            "title": info.get("title") if info else None
        }

    def clear_cache(self):
        """Clear the market cache"""
        self.market_cache.clear()
        logger.info("Market cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get filter statistics

        Returns:
            Stats dictionary
        """
        return {
            "excluded_categories": self.excluded_categories,
            "market_timeframe_days": self.market_timeframe_days,
            "cached_markets": len(self.market_cache)
        }
