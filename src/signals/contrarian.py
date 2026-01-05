#!/usr/bin/env python3
"""
Contrarian Detector
Detects trades against strong market consensus
"""

import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class ContrarianDetector:
    """Detect contrarian trades against consensus"""

    def __init__(
        self,
        api_client,
        consensus_threshold: float = 0.80,
        cache_ttl: int = 60
    ):
        """
        Initialize contrarian detector

        Args:
            api_client: Polymarket API client instance
            consensus_threshold: Probability threshold for consensus (0.80 = 80%)
            cache_ttl: Cache TTL in seconds (default 1 minute)
        """
        self.api_client = api_client
        self.consensus_threshold = consensus_threshold
        self.cache_ttl = cache_ttl

        # Cache market odds
        self.odds_cache = {}  # {market_id: (odds, cached_time)}

        logger.info(
            f"ContrarianDetector initialized - Consensus threshold: {consensus_threshold * 100}%"
        )

    def detect(self, trade: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Detect if trade is contrarian

        Args:
            trade: Trade dictionary

        Returns:
            Tuple of (is_signal: bool, signal_data: dict)
        """
        market_id = trade.get("market_id") or trade.get("condition_id")
        asset_id = trade.get("asset_id")
        side = trade.get("side", "").upper()

        if not market_id or not asset_id:
            return False, None

        # Get current market odds
        market_odds = self._get_market_odds(asset_id)

        if market_odds is None:
            return False, None

        # Determine if contrarian
        is_contrarian = False
        consensus_side = None

        if side == "BUY":
            # Buying YES when consensus is NO (low odds)
            if market_odds < (1 - self.consensus_threshold):
                is_contrarian = True
                consensus_side = "NO"

        elif side == "SELL":
            # Selling YES (buying NO) when consensus is YES (high odds)
            if market_odds > self.consensus_threshold:
                is_contrarian = True
                consensus_side = "YES"

        if is_contrarian:
            confidence = self._calculate_confidence(market_odds, side)

            signal_data = {
                "signal_type": "contrarian",
                "side": side,
                "market_odds": round(market_odds, 3),
                "consensus_side": consensus_side,
                "consensus_strength": round(abs(market_odds - 0.5) * 2, 3),
                "confidence": confidence
            }

            logger.info(
                f"🔄 Contrarian trade detected: {side} against {consensus_side} consensus "
                f"(odds: {market_odds:.1%}, confidence: {confidence:.2f})"
            )

            return True, signal_data

        return False, None

    def _get_market_odds(self, asset_id: str) -> Optional[float]:
        """
        Get current market odds with caching

        Args:
            asset_id: Asset/token ID

        Returns:
            Market odds (0.0 - 1.0) or None
        """
        from datetime import datetime

        # Check cache
        if asset_id in self.odds_cache:
            odds, cached_time = self.odds_cache[asset_id]

            # Check if cache is still valid
            age = (datetime.now() - cached_time).total_seconds()
            if age < self.cache_ttl:
                return odds

        # Fetch from API
        try:
            odds_data = self.api_client.get_market_odds(asset_id)

            if odds_data and "mid" in odds_data:
                odds = float(odds_data["mid"])

                # Cache result
                self.odds_cache[asset_id] = (odds, datetime.now())

                return odds

        except Exception as e:
            logger.debug(f"Error fetching market odds for {asset_id}: {e}")

        return None

    def _calculate_confidence(self, market_odds: float, side: str) -> float:
        """
        Calculate confidence based on consensus strength

        Args:
            market_odds: Current market odds
            side: Trade side (BUY or SELL)

        Returns:
            Confidence score (0.0 - 1.0)
        """
        # Calculate how far from 50/50 the odds are
        # Stronger consensus = higher confidence in contrarian signal

        if side == "BUY":
            # Buying YES when odds are low
            consensus_strength = 1 - market_odds
        else:
            # Selling YES when odds are high
            consensus_strength = market_odds

        # Scale to confidence score
        if consensus_strength >= 0.95:
            return 1.0
        elif consensus_strength >= 0.90:
            return 0.9
        elif consensus_strength >= 0.85:
            return 0.8
        else:
            return 0.7

    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics"""
        return {
            "consensus_threshold": self.consensus_threshold,
            "cached_markets": len(self.odds_cache)
        }
