#!/usr/bin/env python3
"""
Size Filter
Filters trades based on USD value
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SizeFilter:
    """Filter trades by minimum USD value"""

    def __init__(self, min_trade_size_usd: float = 2000):
        """
        Initialize size filter

        Args:
            min_trade_size_usd: Minimum trade value in USD to process
        """
        self.min_trade_size_usd = min_trade_size_usd

        logger.info(f"SizeFilter initialized - Minimum: ${min_trade_size_usd}")

    def should_process_trade(self, trade: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Determine if a trade meets the minimum size requirement

        Args:
            trade: Trade dictionary with size and price or value_usd

        Returns:
            Tuple of (should_process: bool, reason: str)
        """
        # Try to get value_usd directly
        value_usd = trade.get("value_usd")

        # If not present, calculate from size * price
        if value_usd is None:
            size = trade.get("size", 0)
            price = trade.get("price", 0)
            value_usd = size * price

        # Check against threshold
        if value_usd < self.min_trade_size_usd:
            return False, f"Trade too small: ${value_usd:.2f} < ${self.min_trade_size_usd}"

        return True, None

    def get_trade_value(self, trade: Dict[str, Any]) -> float:
        """
        Get the USD value of a trade

        Args:
            trade: Trade dictionary

        Returns:
            USD value as float
        """
        value_usd = trade.get("value_usd")

        if value_usd is None:
            size = trade.get("size", 0)
            price = trade.get("price", 0)
            value_usd = size * price

        return float(value_usd)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get filter statistics

        Returns:
            Stats dictionary
        """
        return {
            "min_trade_size_usd": self.min_trade_size_usd
        }
