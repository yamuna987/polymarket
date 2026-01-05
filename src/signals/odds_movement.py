#!/usr/bin/env python3
"""
Odds Movement Tracker
Detects trades during significant price movements
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


class OddsMovementTracker:
    """Track and detect significant odds movements"""

    def __init__(
        self,
        api_client,
        movement_threshold_pct: float = 5.0,
        lookback_minutes: int = 60,
        max_history: int = 100
    ):
        """
        Initialize odds movement tracker

        Args:
            api_client: Polymarket API client instance
            movement_threshold_pct: Percentage movement to flag (5.0 = 5%)
            lookback_minutes: Time window to track movements
            max_history: Maximum price points to store per market
        """
        self.api_client = api_client
        self.movement_threshold_pct = movement_threshold_pct
        self.lookback_minutes = lookback_minutes
        self.max_history = max_history

        # Track price history per market
        # {market_id: deque([(timestamp, price), ...])}
        self.price_history = {}

        logger.info(
            f"OddsMovementTracker initialized - Threshold: {movement_threshold_pct}%, "
            f"Lookback: {lookback_minutes}min"
        )

    def detect(self, trade: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Detect if trade occurred during significant odds movement

        Args:
            trade: Trade dictionary

        Returns:
            Tuple of (is_signal: bool, signal_data: dict)
        """
        market_id = trade.get("market_id") or trade.get("condition_id")
        trade_price = trade.get("price")
        trade_time = trade.get("datetime") or trade.get("trade_timestamp")

        if not market_id or trade_price is None or not trade_time:
            return False, None

        # Ensure datetime object
        if isinstance(trade_time, (int, float)):
            trade_time = datetime.fromtimestamp(trade_time / 1000)

        # Update price history
        self._update_price_history(market_id, trade_time, trade_price)

        # Calculate recent movement
        movement_pct, old_price, time_span_minutes = self._calculate_movement(
            market_id,
            trade_time
        )

        if movement_pct is not None and abs(movement_pct) >= self.movement_threshold_pct:
            confidence = self._calculate_confidence(abs(movement_pct))

            signal_data = {
                "signal_type": "odds_movement",
                "market_id": market_id,
                "current_price": trade_price,
                "previous_price": old_price,
                "movement_pct": round(movement_pct, 2),
                "time_span_minutes": time_span_minutes,
                "direction": "up" if movement_pct > 0 else "down",
                "confidence": confidence
            }

            logger.info(
                f"📈 Odds movement detected: {abs(movement_pct):.1f}% in {time_span_minutes}min "
                f"({old_price:.3f} → {trade_price:.3f}, confidence: {confidence:.2f})"
            )

            return True, signal_data

        return False, None

    def _update_price_history(self, market_id: str, timestamp: datetime, price: float):
        """
        Update price history for a market

        Args:
            market_id: Market ID
            timestamp: Price timestamp
            price: Price value
        """
        if market_id not in self.price_history:
            self.price_history[market_id] = deque(maxlen=self.max_history)

        self.price_history[market_id].append((timestamp, price))

    def _calculate_movement(
        self,
        market_id: str,
        current_time: datetime
    ) -> Tuple[Optional[float], Optional[float], Optional[int]]:
        """
        Calculate price movement within lookback window

        Args:
            market_id: Market ID
            current_time: Current timestamp

        Returns:
            Tuple of (movement_pct, old_price, time_span_minutes)
        """
        if market_id not in self.price_history:
            return None, None, None

        history = self.price_history[market_id]

        if len(history) < 2:
            return None, None, None

        # Get current price (most recent)
        current_timestamp, current_price = history[-1]

        # Find oldest price within lookback window
        cutoff_time = current_time - timedelta(minutes=self.lookback_minutes)

        old_price = None
        old_timestamp = None

        for timestamp, price in history:
            if timestamp >= cutoff_time:
                if old_price is None:
                    old_price = price
                    old_timestamp = timestamp
                break

        if old_price is None or old_price == 0:
            return None, None, None

        # Calculate percentage movement
        movement_pct = ((current_price - old_price) / old_price) * 100

        # Calculate time span
        time_span = (current_timestamp - old_timestamp).total_seconds() / 60

        return movement_pct, old_price, int(time_span)

    def _calculate_confidence(self, movement_pct: float) -> float:
        """
        Calculate confidence based on movement magnitude

        Args:
            movement_pct: Percentage movement (absolute value)

        Returns:
            Confidence score (0.0 - 1.0)
        """
        # Larger movements = higher confidence
        if movement_pct >= 20:
            return 1.0
        elif movement_pct >= 15:
            return 0.9
        elif movement_pct >= 10:
            return 0.8
        elif movement_pct >= 7:
            return 0.7
        else:
            return 0.6

    def cleanup_old_history(self, max_age_hours: int = 24):
        """
        Clean up old price history

        Args:
            max_age_hours: Maximum age to keep in hours
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        markets_to_remove = []

        for market_id, history in self.price_history.items():
            if history and history[-1][0] < cutoff_time:
                markets_to_remove.append(market_id)

        for market_id in markets_to_remove:
            del self.price_history[market_id]

        if markets_to_remove:
            logger.info(f"Cleaned up {len(markets_to_remove)} old market histories")

    def get_stats(self) -> Dict[str, Any]:
        """Get tracker statistics"""
        total_price_points = sum(len(h) for h in self.price_history.values())

        return {
            "movement_threshold_pct": self.movement_threshold_pct,
            "lookback_minutes": self.lookback_minutes,
            "tracked_markets": len(self.price_history),
            "total_price_points": total_price_points
        }
