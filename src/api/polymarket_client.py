#!/usr/bin/env python3
"""
Polymarket API Client
Wrapper for all Polymarket API interactions
"""

import requests
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PolymarketAPIClient:
    """Client for interacting with Polymarket APIs"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the API client

        Args:
            config: Configuration dictionary with API URLs and settings
        """
        self.clob_url = config.get("clob_url", "https://clob.polymarket.com")
        self.gamma_url = config.get("gamma_url", "https://gamma-api.polymarket.com")
        self.data_url = config.get("data_url", "https://data-api.polymarket.com")

        self.timeout = config.get("request_timeout", 30)
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay", 2)

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Polymarket-Signal-Detector/1.0"
        })

    def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        retries: int = 0
    ) -> Optional[Any]:
        """
        Make HTTP request with retry logic

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL to request
            params: Query parameters
            json_data: JSON body data
            retries: Current retry count

        Returns:
            Response JSON data or None on error
        """
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")

            if retries < self.max_retries:
                wait_time = self.retry_delay * (2 ** retries)
                logger.info(f"Retrying in {wait_time}s... (attempt {retries + 1}/{self.max_retries})")
                time.sleep(wait_time)
                return self._make_request(method, url, params, json_data, retries + 1)

            logger.error(f"Max retries reached for {url}")
            return None

    # ==================== TRADE ENDPOINTS ====================

    def get_trades(
        self,
        limit: int = 100,
        offset: int = 0,
        market: Optional[str] = None,
        user: Optional[str] = None,
        side: Optional[str] = None,
        taker_only: bool = True
    ) -> List[Dict]:
        """
        Get trades from the Data API

        Args:
            limit: Number of results (max 10000)
            offset: Pagination offset
            market: Filter by market condition ID
            user: Filter by user wallet address
            side: Filter by side (BUY or SELL)
            taker_only: Only return taker trades

        Returns:
            List of trade objects
        """
        url = f"{self.data_url}/trades"
        params = {
            "limit": min(limit, 10000),
            "offset": offset,
            "takerOnly": str(taker_only).lower()
        }

        if market:
            params["market"] = market
        if user:
            params["user"] = user
        if side:
            params["side"] = side

        data = self._make_request("GET", url, params=params)
        return data if data else []

    # ==================== MARKET ENDPOINTS ====================

    def get_markets(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Get markets from Gamma API

        Args:
            limit: Number of results
            offset: Pagination offset

        Returns:
            List of market objects
        """
        url = f"{self.gamma_url}/markets"
        params = {"limit": limit, "offset": offset}

        data = self._make_request("GET", url, params=params)
        return data if data else []

    def search_markets(self, query: str) -> List[Dict]:
        """
        Search for markets

        Args:
            query: Search query string

        Returns:
            List of matching markets
        """
        url = f"{self.gamma_url}/public-search"
        params = {"query": query}

        data = self._make_request("GET", url, params=params)
        return data if data else []

    def get_market_odds(self, token_id: str) -> Optional[Dict]:
        """
        Get current market odds (midpoint)

        Args:
            token_id: Token ID

        Returns:
            Market odds data
        """
        url = f"{self.clob_url}/midpoint"
        params = {"token_id": token_id}

        return self._make_request("GET", url, params=params)

    def get_price(self, token_id: str, side: str) -> Optional[Dict]:
        """
        Get market price for specific side

        Args:
            token_id: Token ID
            side: BUY or SELL

        Returns:
            Price data
        """
        url = f"{self.clob_url}/price"
        params = {"token_id": token_id, "side": side}

        return self._make_request("GET", url, params=params)

    # ==================== USER/PROFILE ENDPOINTS ====================

    def get_profile(self, wallet_address: str) -> Optional[Dict]:
        """
        Get user profile from Gamma API

        Args:
            wallet_address: User's wallet address

        Returns:
            Profile data with createdAt, name, pseudonym, verified badge
        """
        url = f"{self.gamma_url}/public-profile"
        params = {"address": wallet_address}

        return self._make_request("GET", url, params=params)

    def get_positions(
        self,
        wallet_address: str,
        limit: int = 1000,
        sort_by: str = "CASHPNL"
    ) -> List[Dict]:
        """
        Get open positions for a wallet

        Args:
            wallet_address: User's wallet address
            limit: Number of results
            sort_by: Sort field (CASHPNL, etc.)

        Returns:
            List of open positions
        """
        url = f"{self.data_url}/positions"
        params = {
            "user": wallet_address,
            "limit": limit,
            "sortBy": sort_by,
            "sortDirection": "DESC"
        }

        data = self._make_request("GET", url, params=params)
        return data if data else []

    def get_closed_positions(
        self,
        wallet_address: str,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Get closed positions for a wallet

        Args:
            wallet_address: User's wallet address
            limit: Number of results

        Returns:
            List of closed positions
        """
        url = f"{self.data_url}/closed-positions"
        params = {
            "user": wallet_address,
            "limit": limit
        }

        data = self._make_request("GET", url, params=params)
        return data if data else []

    def get_total_markets_traded(self, wallet_address: str) -> int:
        """
        Get total number of markets traded by user

        Args:
            wallet_address: User's wallet address

        Returns:
            Total markets traded
        """
        url = f"{self.data_url}/traded"
        params = {"user": wallet_address}

        data = self._make_request("GET", url, params=params)
        if data:
            return data.get("traded", 0)
        return 0

    # ==================== ANALYTICS METHODS ====================

    def calculate_win_rate(self, wallet_address: str) -> float:
        """
        Calculate win rate for a wallet based on closed positions

        Args:
            wallet_address: User's wallet address

        Returns:
            Win rate as decimal (0.0 - 1.0)
        """
        closed_positions = self.get_closed_positions(wallet_address)

        if not closed_positions:
            return 0.0

        wins = sum(1 for p in closed_positions if (p.get("pnl", 0) or 0) > 0)
        total = len(closed_positions)

        return wins / total if total > 0 else 0.0

    def get_user_stats(self, wallet_address: str) -> Dict:
        """
        Get comprehensive user statistics

        Args:
            wallet_address: User's wallet address

        Returns:
            Dictionary with user stats
        """
        profile = self.get_profile(wallet_address)
        positions = self.get_positions(wallet_address)
        closed_positions = self.get_closed_positions(wallet_address)
        total_markets = self.get_total_markets_traded(wallet_address)

        # Calculate total P&L
        open_pnl = sum(p.get("cashPnl", 0) or 0 for p in positions)
        closed_pnl = sum(p.get("pnl", 0) or 0 for p in closed_positions)
        total_pnl = open_pnl + closed_pnl

        # Calculate win rate
        win_rate = self.calculate_win_rate(wallet_address)

        return {
            "wallet": wallet_address,
            "profile": profile,
            "total_markets_traded": total_markets,
            "open_positions": len(positions),
            "closed_positions": len(closed_positions),
            "total_pnl": total_pnl,
            "open_pnl": open_pnl,
            "closed_pnl": closed_pnl,
            "win_rate": win_rate,
            "joined_date": profile.get("createdAt") if profile else None,
            "display_name": (
                profile.get("name") or profile.get("pseudonym")
                if profile else wallet_address[:8]
            )
        }

    def is_fresh_wallet(self, wallet_address: str, days_threshold: int = 30) -> bool:
        """
        Check if wallet is considered "fresh" (recently created)

        Args:
            wallet_address: User's wallet address
            days_threshold: Maximum days old to be considered fresh

        Returns:
            True if wallet is fresh
        """
        profile = self.get_profile(wallet_address)

        if not profile or "createdAt" not in profile:
            return False

        created_at = datetime.fromisoformat(profile["createdAt"].replace("Z", "+00:00"))
        age = datetime.now(created_at.tzinfo) - created_at

        return age.days <= days_threshold

    def get_average_trade_size(self, wallet_address: str, limit: int = 100) -> float:
        """
        Calculate average trade size for a user

        Args:
            wallet_address: User's wallet address
            limit: Number of recent trades to consider

        Returns:
            Average trade size in USD
        """
        trades = self.get_trades(user=wallet_address, limit=limit)

        if not trades:
            return 0.0

        total_size = sum(
            (t.get("size", 0) or 0) * (t.get("price", 0) or 0)
            for t in trades
        )

        return total_size / len(trades) if trades else 0.0

    def check_balanced_positions(self, wallet_address: str, threshold: float = 0.4) -> bool:
        """
        Check if user has balanced positions (potential LP)

        Args:
            wallet_address: User's wallet address
            threshold: Maximum deviation from 50/50 split (0.4 = 40-60%)

        Returns:
            True if positions are balanced (likely LP)
        """
        positions = self.get_positions(wallet_address)

        if not positions:
            return False

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

        # Check for balanced positions
        balanced_markets = 0
        for market_data in markets.values():
            total = market_data["yes"] + market_data["no"]
            if total > 0:
                yes_ratio = market_data["yes"] / total
                # Check if ratio is close to 0.5 (within threshold)
                if abs(yes_ratio - 0.5) <= threshold:
                    balanced_markets += 1

        # If more than 50% of markets have balanced positions, likely an LP
        return balanced_markets > len(markets) * 0.5 if markets else False

    def close(self):
        """Close the HTTP session"""
        self.session.close()
