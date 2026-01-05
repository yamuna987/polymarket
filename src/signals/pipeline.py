#!/usr/bin/env python3
"""
Signal Detection Pipeline
Coordinates all signal detectors
"""

import logging
from typing import Dict, Any, List, Optional

from .fresh_wallet import FreshWalletDetector
from .size_anomaly import SizeAnomalyDetector
from .timing import TimingAnalyzer
from .odds_movement import OddsMovementTracker
from .contrarian import ContrarianDetector
from .cluster import ClusterDetector

logger = logging.getLogger(__name__)


class SignalPipeline:
    """Coordinate multiple signal detectors"""

    def __init__(
        self,
        fresh_wallet: Optional[FreshWalletDetector] = None,
        size_anomaly: Optional[SizeAnomalyDetector] = None,
        timing: Optional[TimingAnalyzer] = None,
        odds_movement: Optional[OddsMovementTracker] = None,
        contrarian: Optional[ContrarianDetector] = None,
        cluster: Optional[ClusterDetector] = None
    ):
        """
        Initialize signal pipeline

        Args:
            fresh_wallet: Fresh wallet detector
            size_anomaly: Size anomaly detector
            timing: Timing analyzer
            odds_movement: Odds movement tracker
            contrarian: Contrarian detector
            cluster: Cluster detector
        """
        self.detectors = {
            "fresh_wallet": fresh_wallet,
            "size_anomaly": size_anomaly,
            "timing": timing,
            "odds_movement": odds_movement,
            "contrarian": contrarian,
            "cluster": cluster
        }

        # Remove None detectors
        self.detectors = {k: v for k, v in self.detectors.items() if v is not None}

        # Statistics
        self.stats = {
            "total_trades_analyzed": 0,
            "total_signals_detected": 0,
            "signals_by_type": {name: 0 for name in self.detectors.keys()},
            "multi_signal_trades": 0
        }

        enabled = list(self.detectors.keys())
        logger.info(f"SignalPipeline initialized - Enabled detectors: {', '.join(enabled)}")

    def process_trade(self, trade: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a trade through all signal detectors

        Args:
            trade: Trade dictionary

        Returns:
            List of detected signals
        """
        self.stats["total_trades_analyzed"] += 1

        detected_signals = []

        # Run each detector
        for detector_name, detector in self.detectors.items():
            try:
                is_signal, signal_data = detector.detect(trade)

                if is_signal and signal_data:
                    # Add detector name and enrichment
                    signal_data["detector"] = detector_name
                    signal_data["trade_summary"] = {
                        "market_id": trade.get("market_id", "unknown")[:10] + "...",
                        "wallet": (trade.get("trader_wallet") or "unknown")[:10] + "...",
                        "side": trade.get("side"),
                        "value_usd": trade.get("value_usd", 0)
                    }

                    detected_signals.append(signal_data)

                    # Update stats
                    self.stats["signals_by_type"][detector_name] += 1

            except Exception as e:
                logger.error(f"Error in {detector_name} detector: {e}")

        # Track signals
        if detected_signals:
            self.stats["total_signals_detected"] += len(detected_signals)

            if len(detected_signals) > 1:
                self.stats["multi_signal_trades"] += 1

            logger.info(
                f"🎯 Detected {len(detected_signals)} signal(s): "
                f"{[s['signal_type'] for s in detected_signals]}"
            )

        return detected_signals

    def get_combined_confidence(self, signals: List[Dict[str, Any]]) -> float:
        """
        Calculate combined confidence from multiple signals

        Args:
            signals: List of signal dictionaries

        Returns:
            Combined confidence score (0.0 - 1.0)
        """
        if not signals:
            return 0.0

        # Get individual confidences
        confidences = [s.get("confidence", 0.5) for s in signals]

        # Multiple signals boost confidence
        if len(signals) == 1:
            return confidences[0]

        # Average + boost for multiple signals
        avg_confidence = sum(confidences) / len(confidences)
        multi_signal_boost = min(0.2 * (len(signals) - 1), 0.3)

        combined = min(avg_confidence + multi_signal_boost, 1.0)

        return round(combined, 2)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get pipeline statistics

        Returns:
            Stats dictionary
        """
        stats = {
            "total_trades_analyzed": self.stats["total_trades_analyzed"],
            "total_signals_detected": self.stats["total_signals_detected"],
            "multi_signal_trades": self.stats["multi_signal_trades"],
            "signals_by_type": self.stats["signals_by_type"].copy()
        }

        # Add detector-specific stats
        for name, detector in self.detectors.items():
            if hasattr(detector, "get_stats"):
                stats[f"{name}_detector"] = detector.get_stats()

        return stats

    def reset_stats(self):
        """Reset pipeline statistics"""
        self.stats = {
            "total_trades_analyzed": 0,
            "total_signals_detected": 0,
            "signals_by_type": {name: 0 for name in self.detectors.keys()},
            "multi_signal_trades": 0
        }
        logger.info("Signal pipeline statistics reset")

    def cleanup(self, max_age_hours: int = 24):
        """
        Clean up old data from detectors

        Args:
            max_age_hours: Maximum age to keep in hours
        """
        for name, detector in self.detectors.items():
            if hasattr(detector, "cleanup_old_history"):
                detector.cleanup_old_history(max_age_hours)
            elif hasattr(detector, "cleanup_old_trades"):
                detector.cleanup_old_trades(max_age_hours)

        logger.info(f"Cleaned up old data from signal detectors")


def create_signal_pipeline(config: Dict[str, Any], api_client) -> SignalPipeline:
    """
    Factory function to create signal pipeline from configuration

    Args:
        config: Configuration dictionary
        api_client: Polymarket API client instance

    Returns:
        Configured SignalPipeline instance
    """
    signal_config = config.get("signal_detection", {})

    # Create fresh wallet detector
    fresh_wallet = FreshWalletDetector(
        api_client=api_client,
        fresh_threshold_days=signal_config.get("fresh_wallet_days", 30),
        cache_ttl=3600
    )

    # Create size anomaly detector
    size_anomaly = SizeAnomalyDetector(
        api_client=api_client,
        anomaly_multiplier=signal_config.get("size_anomaly_multiplier", 2.0),
        min_trades_for_comparison=5,
        cache_ttl=600
    )

    # Create timing analyzer
    timing = TimingAnalyzer(
        api_client=api_client,
        early_trade_minutes=signal_config.get("timing_minutes_after_creation", 60),
        unusual_hour_start=2,
        unusual_hour_end=6
    )

    # Create odds movement tracker
    odds_movement = OddsMovementTracker(
        api_client=api_client,
        movement_threshold_pct=signal_config.get("odds_movement_threshold_pct", 5.0),
        lookback_minutes=60,
        max_history=100
    )

    # Create contrarian detector
    contrarian = ContrarianDetector(
        api_client=api_client,
        consensus_threshold=signal_config.get("contrarian_consensus_threshold", 0.80),
        cache_ttl=60
    )

    # Create cluster detector
    cluster = ClusterDetector(
        api_client=api_client,
        min_wallets=signal_config.get("cluster_min_wallets", 3),
        time_window_seconds=signal_config.get("cluster_time_window", 300),
        similarity_threshold=0.7,
        max_history=1000
    )

    # Create pipeline
    pipeline = SignalPipeline(
        fresh_wallet=fresh_wallet,
        size_anomaly=size_anomaly,
        timing=timing,
        odds_movement=odds_movement,
        contrarian=contrarian,
        cluster=cluster
    )

    logger.info("Signal pipeline created from configuration")

    return pipeline
