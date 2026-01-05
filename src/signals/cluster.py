#!/usr/bin/env python3
"""
Cluster Detector
Detects coordinated trading from multiple wallets
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class ClusterDetector:
    """Detect coordinated trading clusters"""

    def __init__(
        self,
        api_client,
        min_wallets: int = 3,
        time_window_seconds: int = 300,
        similarity_threshold: float = 0.7,
        max_history: int = 1000
    ):
        """
        Initialize cluster detector

        Args:
            api_client: Polymarket API client instance
            min_wallets: Minimum wallets to consider a cluster
            time_window_seconds: Time window for clustering (default 5 min)
            similarity_threshold: Wallet similarity threshold (0-1)
            max_history: Maximum trades to track
        """
        self.api_client = api_client
        self.min_wallets = min_wallets
        self.time_window_seconds = time_window_seconds
        self.similarity_threshold = similarity_threshold
        self.max_history = max_history

        # Track recent trades by market
        # {market_id: deque([(timestamp, wallet, side, size), ...])}
        self.recent_trades = defaultdict(lambda: deque(maxlen=max_history))

        # Track wallet similarities
        self.wallet_similarities = {}  # {(wallet1, wallet2): similarity_score}

        logger.info(
            f"ClusterDetector initialized - Min wallets: {min_wallets}, "
            f"Time window: {time_window_seconds}s"
        )

    def detect(self, trade: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Detect if trade is part of a trading cluster

        Args:
            trade: Trade dictionary

        Returns:
            Tuple of (is_signal: bool, signal_data: dict)
        """
        market_id = trade.get("market_id") or trade.get("condition_id")
        wallet = trade.get("trader_wallet") or trade.get("user") or trade.get("proxyWallet")
        side = trade.get("side")
        size = trade.get("value_usd", 0)
        trade_time = trade.get("datetime") or trade.get("trade_timestamp")

        if not market_id or not wallet or not side or not trade_time:
            return False, None

        # Ensure datetime object
        if isinstance(trade_time, (int, float)):
            trade_time = datetime.fromtimestamp(trade_time / 1000)

        # Add to recent trades
        self.recent_trades[market_id].append((trade_time, wallet, side, size))

        # Detect cluster
        cluster_wallets = self._find_cluster(market_id, trade_time, wallet, side)

        if len(cluster_wallets) >= self.min_wallets:
            confidence = self._calculate_confidence(len(cluster_wallets), cluster_wallets)

            # Get cluster statistics
            cluster_stats = self._get_cluster_stats(
                market_id,
                trade_time,
                cluster_wallets
            )

            signal_data = {
                "signal_type": "cluster",
                "market_id": market_id,
                "cluster_size": len(cluster_wallets),
                "cluster_wallets": [w[:10] + "..." for w in list(cluster_wallets)[:5]],
                "same_side": cluster_stats["same_side"],
                "total_volume": cluster_stats["total_volume"],
                "time_span_seconds": cluster_stats["time_span"],
                "confidence": confidence
            }

            logger.info(
                f"👥 Cluster detected: {len(cluster_wallets)} wallets trading {side} "
                f"within {cluster_stats['time_span']}s "
                f"(volume: ${cluster_stats['total_volume']:.2f}, confidence: {confidence:.2f})"
            )

            return True, signal_data

        return False, None

    def _find_cluster(
        self,
        market_id: str,
        current_time: datetime,
        current_wallet: str,
        current_side: str
    ) -> set:
        """
        Find wallets that traded in similar pattern

        Args:
            market_id: Market ID
            current_time: Current trade time
            current_wallet: Current wallet
            current_side: Current trade side

        Returns:
            Set of wallet addresses in cluster
        """
        if market_id not in self.recent_trades:
            return {current_wallet}

        cutoff_time = current_time - timedelta(seconds=self.time_window_seconds)
        cluster = {current_wallet}

        # Find wallets trading same market, same side, within time window
        for timestamp, wallet, side, size in self.recent_trades[market_id]:
            if timestamp < cutoff_time:
                continue

            if wallet == current_wallet:
                continue

            # Same side within time window
            if side == current_side:
                cluster.add(wallet)

        return cluster

    def _get_cluster_stats(
        self,
        market_id: str,
        current_time: datetime,
        cluster_wallets: set
    ) -> Dict[str, Any]:
        """
        Get statistics for a cluster

        Args:
            market_id: Market ID
            current_time: Current time
            cluster_wallets: Set of wallets in cluster

        Returns:
            Cluster statistics dictionary
        """
        cutoff_time = current_time - timedelta(seconds=self.time_window_seconds)

        trades_in_cluster = [
            (timestamp, wallet, side, size)
            for timestamp, wallet, side, size in self.recent_trades[market_id]
            if timestamp >= cutoff_time and wallet in cluster_wallets
        ]

        if not trades_in_cluster:
            return {
                "same_side": True,
                "total_volume": 0,
                "time_span": 0
            }

        sides = [side for _, _, side, _ in trades_in_cluster]
        sizes = [size for _, _, _, size in trades_in_cluster]
        timestamps = [ts for ts, _, _, _ in trades_in_cluster]

        same_side = len(set(sides)) == 1
        total_volume = sum(sizes)
        time_span = int((max(timestamps) - min(timestamps)).total_seconds())

        return {
            "same_side": same_side,
            "total_volume": total_volume,
            "time_span": time_span
        }

    def _calculate_confidence(self, cluster_size: int, cluster_wallets: set) -> float:
        """
        Calculate confidence based on cluster characteristics

        Args:
            cluster_size: Number of wallets in cluster
            cluster_wallets: Set of wallet addresses

        Returns:
            Confidence score (0.0 - 1.0)
        """
        # Larger clusters = higher confidence
        if cluster_size >= 10:
            return 1.0
        elif cluster_size >= 7:
            return 0.9
        elif cluster_size >= 5:
            return 0.8
        else:
            return 0.7

    def cleanup_old_trades(self, max_age_hours: int = 24):
        """
        Clean up old trade history

        Args:
            max_age_hours: Maximum age to keep in hours
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        markets_to_remove = []

        for market_id, trades in self.recent_trades.items():
            # Remove old trades
            while trades and trades[0][0] < cutoff_time:
                trades.popleft()

            # Mark market for removal if no recent trades
            if not trades:
                markets_to_remove.append(market_id)

        for market_id in markets_to_remove:
            del self.recent_trades[market_id]

        if markets_to_remove:
            logger.info(f"Cleaned up {len(markets_to_remove)} old market trade histories")

    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics"""
        total_trades = sum(len(t) for t in self.recent_trades.values())

        return {
            "min_wallets": self.min_wallets,
            "time_window_seconds": self.time_window_seconds,
            "tracked_markets": len(self.recent_trades),
            "total_tracked_trades": total_trades
        }
