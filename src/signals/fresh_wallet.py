#!/usr/bin/env python3
"""
Fresh Wallet Detector
Detects trades from newly created wallets
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FreshWalletDetector:
    """Detect trades from fresh/new wallets"""

    def __init__(
        self,
        api_client,
        fresh_threshold_days: int = 30,
        cache_ttl: int = 3600
    ):
        """
        Initialize fresh wallet detector

        Args:
            api_client: Polymarket API client instance
            fresh_threshold_days: Days threshold to consider wallet "fresh"
            cache_ttl: Cache TTL in seconds (default 1 hour)
        """
        self.api_client = api_client
        self.fresh_threshold_days = fresh_threshold_days
        self.cache_ttl = cache_ttl

        # Cache wallet ages
        self.wallet_cache = {}  # {wallet: (created_at, cached_time)}

        logger.info(
            f"FreshWalletDetector initialized - Threshold: {fresh_threshold_days} days, "
            f"Cache TTL: {cache_ttl}s"
        )

    def detect(self, trade: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Detect if trade is from a fresh wallet

        Args:
            trade: Trade dictionary

        Returns:
            Tuple of (is_signal: bool, signal_data: dict)
        """
        wallet = trade.get("trader_wallet") or trade.get("user") or trade.get("proxyWallet")

        if not wallet:
            return False, None

        # Check if wallet is fresh
        is_fresh, wallet_age_days, created_at = self.is_fresh_wallet(wallet)

        if is_fresh:
            confidence = self._calculate_confidence(wallet_age_days)

            signal_data = {
                "signal_type": "fresh_wallet",
                "wallet": wallet,
                "wallet_age_days": wallet_age_days,
                "created_at": created_at.isoformat() if created_at else None,
                "threshold_days": self.fresh_threshold_days,
                "confidence": confidence
            }

            logger.info(
                f"🆕 Fresh wallet detected: {wallet[:10]}... "
                f"(age: {wallet_age_days} days, confidence: {confidence:.2f})"
            )

            return True, signal_data

        return False, None

    def is_fresh_wallet(self, wallet_address: str) -> Tuple[bool, Optional[int], Optional[datetime]]:
        """
        Check if wallet is fresh

        Args:
            wallet_address: Wallet address

        Returns:
            Tuple of (is_fresh: bool, age_days: int, created_at: datetime)
        """
        # Check cache first
        if wallet_address in self.wallet_cache:
            created_at, cached_time = self.wallet_cache[wallet_address]

            # Check if cache is still valid
            age = (datetime.now() - cached_time).total_seconds()
            if age < self.cache_ttl:
                if created_at:
                    wallet_age = (datetime.now(created_at.tzinfo) - created_at).days
                    is_fresh = wallet_age <= self.fresh_threshold_days
                    return is_fresh, wallet_age, created_at
                else:
                    return False, None, None

        # Fetch profile from API
        try:
            profile = self.api_client.get_profile(wallet_address)

            if not profile or "createdAt" not in profile:
                # Cache negative result
                self.wallet_cache[wallet_address] = (None, datetime.now())
                return False, None, None

            created_at_str = profile["createdAt"]
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

            # Cache result
            self.wallet_cache[wallet_address] = (created_at, datetime.now())

            # Calculate age
            wallet_age = (datetime.now(created_at.tzinfo) - created_at).days

            is_fresh = wallet_age <= self.fresh_threshold_days

            return is_fresh, wallet_age, created_at

        except Exception as e:
            logger.error(f"Error checking fresh wallet for {wallet_address}: {e}")
            return False, None, None

    def _calculate_confidence(self, wallet_age_days: int) -> float:
        """
        Calculate confidence score based on wallet age

        Args:
            wallet_age_days: Wallet age in days

        Returns:
            Confidence score (0.0 - 1.0)
        """
        # Newer wallets get higher confidence
        # 0 days = 1.0 confidence
        # threshold days = 0.5 confidence
        if wallet_age_days <= 0:
            return 1.0

        confidence = max(0.5, 1.0 - (wallet_age_days / self.fresh_threshold_days * 0.5))
        return round(confidence, 2)

    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics"""
        # Count fresh vs non-fresh cached wallets
        fresh_count = 0
        non_fresh_count = 0

        for created_at, _ in self.wallet_cache.values():
            if created_at:
                wallet_age = (datetime.now(created_at.tzinfo) - created_at).days
                if wallet_age <= self.fresh_threshold_days:
                    fresh_count += 1
                else:
                    non_fresh_count += 1

        return {
            "fresh_threshold_days": self.fresh_threshold_days,
            "cached_wallets": len(self.wallet_cache),
            "cached_fresh_wallets": fresh_count,
            "cached_non_fresh_wallets": non_fresh_count
        }
