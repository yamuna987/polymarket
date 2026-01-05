#!/usr/bin/env python3
"""
Size Anomaly Detector
Detects trades that are significantly larger than a user's average
"""

import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class SizeAnomalyDetector:
    """Detect unusually large trades for a user"""

    def __init__(
        self,
        api_client,
        anomaly_multiplier: float = 2.0,
        min_trades_for_comparison: int = 5,
        cache_ttl: int = 600
    ):
        """
        Initialize size anomaly detector

        Args:
            api_client: Polymarket API client instance
            anomaly_multiplier: Multiplier to consider trade anomalous (2.0 = 2x average)
            min_trades_for_comparison: Minimum trades needed to calculate average
            cache_ttl: Cache TTL in seconds (default 10 minutes)
        """
        self.api_client = api_client
        self.anomaly_multiplier = anomaly_multiplier
        self.min_trades_for_comparison = min_trades_for_comparison
        self.cache_ttl = cache_ttl

        # Cache user average trade sizes
        self.average_cache = {}  # {wallet: (avg_size, cached_time)}

        logger.info(
            f"SizeAnomalyDetector initialized - Multiplier: {anomaly_multiplier}x, "
            f"Min trades: {min_trades_for_comparison}"
        )

    def detect(self, trade: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Detect if trade is unusually large for this user

        Args:
            trade: Trade dictionary

        Returns:
            Tuple of (is_signal: bool, signal_data: dict)
        """
        wallet = trade.get("trader_wallet") or trade.get("user") or trade.get("proxyWallet")
        trade_size = trade.get("value_usd", 0)

        if not wallet or trade_size <= 0:
            return False, None

        # Get user's average trade size
        avg_size, trade_count = self.get_average_trade_size(wallet)

        if avg_size is None or trade_count < self.min_trades_for_comparison:
            logger.debug(
                f"Not enough trade history for {wallet[:10]}... "
                f"({trade_count} trades, need {self.min_trades_for_comparison})"
            )
            return False, None

        # Check if current trade is anomalous
        threshold = avg_size * self.anomaly_multiplier

        if trade_size >= threshold:
            # Calculate how many times larger than average
            multiplier = trade_size / avg_size if avg_size > 0 else 0

            confidence = self._calculate_confidence(multiplier)

            signal_data = {
                "signal_type": "size_anomaly",
                "wallet": wallet,
                "trade_size": trade_size,
                "average_size": avg_size,
                "multiplier": round(multiplier, 2),
                "threshold": threshold,
                "trade_count": trade_count,
                "confidence": confidence
            }

            logger.info(
                f"📊 Size anomaly detected: ${trade_size:.2f} is {multiplier:.1f}x "
                f"larger than avg ${avg_size:.2f} for {wallet[:10]}... "
                f"(confidence: {confidence:.2f})"
            )

            return True, signal_data

        return False, None

    def get_average_trade_size(self, wallet_address: str) -> Tuple[Optional[float], int]:
        """
        Get average trade size for a wallet

        Args:
            wallet_address: Wallet address

        Returns:
            Tuple of (average_size: float, trade_count: int)
        """
        from datetime import datetime

        # Check cache first
        if wallet_address in self.average_cache:
            avg_size, trade_count, cached_time = self.average_cache[wallet_address]

            # Check if cache is still valid
            age = (datetime.now() - cached_time).total_seconds()
            if age < self.cache_ttl:
                return avg_size, trade_count

        # Calculate from API
        try:
            avg_size = self.api_client.get_average_trade_size(
                wallet_address,
                limit=100
            )

            # Get trade count (approximate from recent trades)
            trades = self.api_client.get_trades(user=wallet_address, limit=100)
            trade_count = len(trades) if trades else 0

            # Cache result
            self.average_cache[wallet_address] = (avg_size, trade_count, datetime.now())

            return avg_size, trade_count

        except Exception as e:
            logger.error(f"Error getting average trade size for {wallet_address}: {e}")
            return None, 0

    def _calculate_confidence(self, multiplier: float) -> float:
        """
        Calculate confidence score based on size multiplier

        Args:
            multiplier: How many times larger than average

        Returns:
            Confidence score (0.0 - 1.0)
        """
        # Higher multipliers = higher confidence
        # 2x = 0.6, 5x = 0.8, 10x+ = 1.0
        if multiplier >= 10:
            return 1.0
        elif multiplier >= 5:
            return 0.8
        elif multiplier >= 3:
            return 0.7
        else:
            return 0.6

    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics"""
        return {
            "anomaly_multiplier": self.anomaly_multiplier,
            "min_trades_for_comparison": self.min_trades_for_comparison,
            "cached_wallets": len(self.average_cache)
        }
