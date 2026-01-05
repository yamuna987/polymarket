#!/usr/bin/env python3
"""
Caching layer for API responses
Reduces redundant API calls and improves performance
"""

import time
import logging
from typing import Any, Optional, Dict, Callable
from functools import wraps
from cachetools import TTLCache

logger = logging.getLogger(__name__)


class APICache:
    """Cache manager for API responses"""

    def __init__(self, profile_ttl: int = 3600, market_ttl: int = 1800):
        """
        Initialize cache

        Args:
            profile_ttl: Time-to-live for profile data (seconds)
            market_ttl: Time-to-live for market data (seconds)
        """
        self.profile_cache = TTLCache(maxsize=10000, ttl=profile_ttl)
        self.market_cache = TTLCache(maxsize=5000, ttl=market_ttl)
        self.stats_cache = TTLCache(maxsize=5000, ttl=300)  # 5 minutes
        self.user_trades_cache = TTLCache(maxsize=5000, ttl=600)  # 10 minutes

        self.hits = 0
        self.misses = 0

    def get_profile(self, wallet_address: str) -> Optional[Dict]:
        """
        Get cached profile data

        Args:
            wallet_address: Wallet address

        Returns:
            Cached profile data or None
        """
        if wallet_address in self.profile_cache:
            self.hits += 1
            logger.debug(f"Cache hit: profile {wallet_address}")
            return self.profile_cache[wallet_address]

        self.misses += 1
        return None

    def set_profile(self, wallet_address: str, data: Dict):
        """
        Cache profile data

        Args:
            wallet_address: Wallet address
            data: Profile data to cache
        """
        self.profile_cache[wallet_address] = data
        logger.debug(f"Cached profile: {wallet_address}")

    def get_market(self, market_id: str) -> Optional[Dict]:
        """
        Get cached market data

        Args:
            market_id: Market ID

        Returns:
            Cached market data or None
        """
        if market_id in self.market_cache:
            self.hits += 1
            logger.debug(f"Cache hit: market {market_id}")
            return self.market_cache[market_id]

        self.misses += 1
        return None

    def set_market(self, market_id: str, data: Dict):
        """
        Cache market data

        Args:
            market_id: Market ID
            data: Market data to cache
        """
        self.market_cache[market_id] = data
        logger.debug(f"Cached market: {market_id}")

    def get_user_stats(self, wallet_address: str) -> Optional[Dict]:
        """
        Get cached user stats

        Args:
            wallet_address: Wallet address

        Returns:
            Cached stats or None
        """
        if wallet_address in self.stats_cache:
            self.hits += 1
            return self.stats_cache[wallet_address]

        self.misses += 1
        return None

    def set_user_stats(self, wallet_address: str, data: Dict):
        """
        Cache user stats

        Args:
            wallet_address: Wallet address
            data: Stats data to cache
        """
        self.stats_cache[wallet_address] = data

    def get_user_trades(self, wallet_address: str) -> Optional[list]:
        """
        Get cached user trades

        Args:
            wallet_address: Wallet address

        Returns:
            Cached trades or None
        """
        if wallet_address in self.user_trades_cache:
            self.hits += 1
            return self.user_trades_cache[wallet_address]

        self.misses += 1
        return None

    def set_user_trades(self, wallet_address: str, data: list):
        """
        Cache user trades

        Args:
            wallet_address: Wallet address
            data: Trades data to cache
        """
        self.user_trades_cache[wallet_address] = data

    def clear(self):
        """Clear all caches"""
        self.profile_cache.clear()
        self.market_cache.clear()
        self.stats_cache.clear()
        self.user_trades_cache.clear()
        logger.info("All caches cleared")

    def get_stats(self) -> Dict:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": total_requests,
            "hit_rate_pct": round(hit_rate, 2),
            "profile_cache_size": len(self.profile_cache),
            "market_cache_size": len(self.market_cache),
            "stats_cache_size": len(self.stats_cache),
            "trades_cache_size": len(self.user_trades_cache)
        }


def cached_call(cache: APICache, cache_type: str, key_func: Callable):
    """
    Decorator for caching function calls

    Args:
        cache: Cache instance
        cache_type: Type of cache (profile, market, stats, trades)
        key_func: Function to generate cache key from arguments

    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = key_func(*args, **kwargs)

            # Try to get from cache
            if cache_type == "profile":
                cached_data = cache.get_profile(cache_key)
                if cached_data is not None:
                    return cached_data
            elif cache_type == "market":
                cached_data = cache.get_market(cache_key)
                if cached_data is not None:
                    return cached_data
            elif cache_type == "stats":
                cached_data = cache.get_user_stats(cache_key)
                if cached_data is not None:
                    return cached_data
            elif cache_type == "trades":
                cached_data = cache.get_user_trades(cache_key)
                if cached_data is not None:
                    return cached_data

            # Call function and cache result
            result = func(*args, **kwargs)

            if result is not None:
                if cache_type == "profile":
                    cache.set_profile(cache_key, result)
                elif cache_type == "market":
                    cache.set_market(cache_key, result)
                elif cache_type == "stats":
                    cache.set_user_stats(cache_key, result)
                elif cache_type == "trades":
                    cache.set_user_trades(cache_key, result)

            return result

        return wrapper
    return decorator
