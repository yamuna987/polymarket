#!/usr/bin/env python3
"""
Timing Analyzer
Detects trades placed shortly after market creation or at unusual times
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, time

logger = logging.getLogger(__name__)


class TimingAnalyzer:
    """Analyze trade timing for signals"""

    def __init__(
        self,
        api_client,
        early_trade_minutes: int = 60,
        unusual_hour_start: int = 2,
        unusual_hour_end: int = 6
    ):
        """
        Initialize timing analyzer

        Args:
            api_client: Polymarket API client instance
            early_trade_minutes: Minutes after market creation to flag
            unusual_hour_start: Start of unusual hours (UTC)
            unusual_hour_end: End of unusual hours (UTC)
        """
        self.api_client = api_client
        self.early_trade_minutes = early_trade_minutes
        self.unusual_hour_start = unusual_hour_start
        self.unusual_hour_end = unusual_hour_end

        # Cache market creation times
        self.market_cache = {}  # {market_id: created_at}

        logger.info(
            f"TimingAnalyzer initialized - Early trade: {early_trade_minutes}min, "
            f"Unusual hours: {unusual_hour_start}:00-{unusual_hour_end}:00 UTC"
        )

    def detect(self, trade: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Detect timing-based signals

        Args:
            trade: Trade dictionary

        Returns:
            Tuple of (is_signal: bool, signal_data: dict)
        """
        signals = []

        # Check for early trade
        is_early, minutes_after_creation = self.is_early_trade(trade)
        if is_early:
            signals.append({
                "type": "early_trade",
                "minutes_after_creation": minutes_after_creation
            })

        # Check for unusual time
        is_unusual_time, hour = self.is_unusual_time(trade)
        if is_unusual_time:
            signals.append({
                "type": "unusual_time",
                "hour_utc": hour
            })

        if signals:
            confidence = self._calculate_confidence(signals)

            signal_data = {
                "signal_type": "timing",
                "timing_signals": signals,
                "confidence": confidence
            }

            logger.info(
                f"⏰ Timing signal detected: {[s['type'] for s in signals]} "
                f"(confidence: {confidence:.2f})"
            )

            return True, signal_data

        return False, None

    def is_early_trade(self, trade: Dict[str, Any]) -> Tuple[bool, Optional[int]]:
        """
        Check if trade was placed shortly after market creation

        Args:
            trade: Trade dictionary

        Returns:
            Tuple of (is_early: bool, minutes_after: int)
        """
        market_id = trade.get("market_id") or trade.get("condition_id")
        trade_time = trade.get("datetime") or trade.get("trade_timestamp")

        if not market_id or not trade_time:
            return False, None

        # Get market creation time
        market_created = self._get_market_creation_time(market_id)

        if not market_created:
            return False, None

        # Ensure both are datetime objects
        if isinstance(trade_time, (int, float)):
            trade_time = datetime.fromtimestamp(trade_time / 1000)

        # Calculate time difference
        time_diff = trade_time - market_created
        minutes_after = int(time_diff.total_seconds() / 60)

        is_early = 0 <= minutes_after <= self.early_trade_minutes

        return is_early, minutes_after if is_early else None

    def is_unusual_time(self, trade: Dict[str, Any]) -> Tuple[bool, Optional[int]]:
        """
        Check if trade was placed during unusual hours

        Args:
            trade: Trade dictionary

        Returns:
            Tuple of (is_unusual: bool, hour: int)
        """
        trade_time = trade.get("datetime") or trade.get("trade_timestamp")

        if not trade_time:
            return False, None

        # Ensure datetime object
        if isinstance(trade_time, (int, float)):
            trade_time = datetime.fromtimestamp(trade_time / 1000)

        # Get hour in UTC
        hour = trade_time.hour

        # Check if in unusual hours range
        is_unusual = self.unusual_hour_start <= hour < self.unusual_hour_end

        return is_unusual, hour if is_unusual else None

    def _get_market_creation_time(self, market_id: str) -> Optional[datetime]:
        """
        Get market creation time with caching

        Args:
            market_id: Market ID

        Returns:
            Creation datetime or None
        """
        # Check cache
        if market_id in self.market_cache:
            return self.market_cache[market_id]

        # For now, return None as we don't have market creation API
        # In production, you'd fetch this from the market metadata API
        # or maintain a local database of markets
        self.market_cache[market_id] = None
        return None

    def _calculate_confidence(self, signals: list) -> float:
        """
        Calculate confidence based on timing signals

        Args:
            signals: List of timing signal dictionaries

        Returns:
            Confidence score (0.0 - 1.0)
        """
        # Multiple timing signals = higher confidence
        if len(signals) >= 2:
            return 0.8

        # Check signal type
        signal_type = signals[0]["type"]

        if signal_type == "early_trade":
            minutes = signals[0].get("minutes_after_creation", 60)
            # Earlier = higher confidence
            if minutes <= 5:
                return 0.9
            elif minutes <= 15:
                return 0.8
            elif minutes <= 30:
                return 0.7
            else:
                return 0.6

        elif signal_type == "unusual_time":
            # Dead of night trades
            return 0.7

        return 0.6

    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics"""
        return {
            "early_trade_minutes": self.early_trade_minutes,
            "unusual_hour_start": self.unusual_hour_start,
            "unusual_hour_end": self.unusual_hour_end,
            "cached_markets": len(self.market_cache)
        }
