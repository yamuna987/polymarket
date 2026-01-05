#!/usr/bin/env python3
"""
LP (Liquidity Provider) Detector
Identifies and filters out liquidity providers based on balanced positions
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class LPDetector:
    """Detect and filter liquidity providers"""

    def __init__(
        self,
        api_client,
        balance_threshold: float = 0.4,
        cache_ttl: int = 300
    ):
        """
        Initialize LP detector

        Args:
            api_client: Polymarket API client instance
            balance_threshold: Max deviation from 50/50 (0.4 = 40-60% split)
            cache_ttl: Cache TTL in seconds (default 5 minutes)
        """
        self.api_client = api_client
        self.balance_threshold = balance_threshold
        self.cache_ttl = cache_ttl

        # Cache LP status by wallet
        self.lp_cache = {}  # {wallet: (is_lp: bool, timestamp: datetime)}

        logger.info(
            f"LPDetector initialized - Balance threshold: {balance_threshold}, "
            f"Cache TTL: {cache_ttl}s"
        )

    def should_process_trade(self, trade: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Determine if a trade should be processed (not from an LP)

        Args:
            trade: Trade dictionary with trader_wallet

        Returns:
            Tuple of (should_process: bool, reason: str)
        """
        wallet = trade.get("trader_wallet") or trade.get("user") or trade.get("proxyWallet")

        if not wallet:
            logger.debug("No wallet address found in trade, allowing by default")
            return True, None

        # Check if wallet is an LP
        is_lp = self.is_liquidity_provider(wallet)

        if is_lp:
            return False, f"Wallet is likely an LP: {wallet[:10]}..."

        return True, None

    def is_liquidity_provider(self, wallet_address: str) -> bool:
        """
        Check if a wallet is likely a liquidity provider

        Args:
            wallet_address: Wallet address to check

        Returns:
            True if wallet is likely an LP
        """
        # Check cache first
        if wallet_address in self.lp_cache:
            is_lp, cached_time = self.lp_cache[wallet_address]

            # Check if cache is still valid
            age = (datetime.now() - cached_time).total_seconds()
            if age < self.cache_ttl:
                logger.debug(f"LP cache hit for {wallet_address[:10]}... (age: {age:.0f}s)")
                return is_lp

        # Fetch positions and check for balance
        try:
            is_lp = self.api_client.check_balanced_positions(
                wallet_address,
                threshold=self.balance_threshold
            )

            # Cache result
            self.lp_cache[wallet_address] = (is_lp, datetime.now())

            logger.debug(f"Wallet {wallet_address[:10]}... LP status: {is_lp}")

            return is_lp

        except Exception as e:
            logger.error(f"Error checking LP status for {wallet_address}: {e}")
            # On error, assume not an LP (fail open)
            return False

    def get_lp_analysis(self, wallet_address: str) -> Dict[str, Any]:
        """
        Get detailed LP analysis for a wallet

        Args:
            wallet_address: Wallet address

        Returns:
            Analysis dictionary
        """
        try:
            positions = self.api_client.get_positions(wallet_address)

            if not positions:
                return {
                    "is_lp": False,
                    "reason": "No open positions",
                    "position_count": 0,
                    "balanced_markets": 0
                }

            # Group positions by market
            markets = {}
            for pos in positions:
                market_id = pos.get("conditionId")
                if not market_id:
                    continue

                if market_id not in markets:
                    markets[market_id] = {"yes": 0, "no": 0}

                outcome = pos.get("outcome", "").lower()
                size = pos.get("size", 0) or 0

                if "yes" in outcome:
                    markets[market_id]["yes"] += size
                elif "no" in outcome:
                    markets[market_id]["no"] += size

            # Count balanced markets
            balanced_markets = 0
            market_balances = []

            for market_id, market_data in markets.items():
                total = market_data["yes"] + market_data["no"]
                if total > 0:
                    yes_ratio = market_data["yes"] / total

                    is_balanced = abs(yes_ratio - 0.5) <= self.balance_threshold

                    market_balances.append({
                        "market_id": market_id[:10] + "...",
                        "yes_ratio": yes_ratio,
                        "is_balanced": is_balanced
                    })

                    if is_balanced:
                        balanced_markets += 1

            # Determine if LP (>50% of markets are balanced)
            is_lp = balanced_markets > len(markets) * 0.5 if markets else False

            return {
                "is_lp": is_lp,
                "reason": f"{balanced_markets}/{len(markets)} markets balanced",
                "position_count": len(positions),
                "market_count": len(markets),
                "balanced_markets": balanced_markets,
                "balance_ratio": balanced_markets / len(markets) if markets else 0,
                "market_details": market_balances[:5]  # Top 5 markets
            }

        except Exception as e:
            logger.error(f"Error analyzing LP status for {wallet_address}: {e}")
            return {
                "is_lp": False,
                "reason": f"Error: {str(e)}",
                "position_count": 0
            }

    def clear_cache(self):
        """Clear the LP cache"""
        self.lp_cache.clear()
        logger.info("LP cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get detector statistics

        Returns:
            Stats dictionary
        """
        # Count cached LPs vs non-LPs
        lp_count = sum(1 for is_lp, _ in self.lp_cache.values() if is_lp)
        non_lp_count = len(self.lp_cache) - lp_count

        return {
            "balance_threshold": self.balance_threshold,
            "cache_ttl_seconds": self.cache_ttl,
            "cached_wallets": len(self.lp_cache),
            "cached_lps": lp_count,
            "cached_non_lps": non_lp_count
        }
