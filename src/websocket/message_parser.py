#!/usr/bin/env python3
"""
WebSocket Message Parser
Utilities for parsing and validating WebSocket messages
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MessageParser:
    """Parser for Polymarket WebSocket messages"""

    @staticmethod
    def parse_trade(data: Dict[str, Any]) -> Optional[Dict]:
        """
        Parse last_trade_price message

        Args:
            data: Raw message data

        Returns:
            Parsed trade dictionary or None if invalid
        """
        try:
            trade = {
                "asset_id": data.get("asset_id"),
                "market_id": data.get("market"),
                "condition_id": data.get("market"),  # Same as market_id
                "price": float(data.get("price", 0)),
                "size": float(data.get("size", 0)),
                "side": data.get("side"),
                "timestamp": int(data.get("timestamp", 0)),
                "fee_rate_bps": data.get("fee_rate_bps"),
                "message_type": "trade"
            }

            # Calculate derived fields
            trade["value_usd"] = trade["price"] * trade["size"]
            trade["datetime"] = datetime.fromtimestamp(trade["timestamp"] / 1000)

            # Validate required fields
            if not all([trade["asset_id"], trade["market_id"], trade["price"], trade["size"]]):
                logger.warning(f"Invalid trade message: missing required fields")
                return None

            return trade

        except Exception as e:
            logger.error(f"Error parsing trade message: {e}")
            return None

    @staticmethod
    def parse_book(data: Dict[str, Any]) -> Optional[Dict]:
        """
        Parse book message

        Args:
            data: Raw message data

        Returns:
            Parsed orderbook dictionary or None if invalid
        """
        try:
            book = {
                "asset_id": data.get("asset_id"),
                "market_id": data.get("market"),
                "timestamp": int(data.get("timestamp", 0)),
                "hash": data.get("hash"),
                "bids": [],
                "asks": [],
                "message_type": "book"
            }

            # Parse book levels
            if "book" in data:
                book_data = data["book"]
                book["bids"] = [
                    {"price": float(level["price"]), "size": float(level["size"])}
                    for level in book_data.get("bids", [])
                ]
                book["asks"] = [
                    {"price": float(level["price"]), "size": float(level["size"])}
                    for level in book_data.get("asks", [])
                ]

            book["datetime"] = datetime.fromtimestamp(book["timestamp"] / 1000)

            return book

        except Exception as e:
            logger.error(f"Error parsing book message: {e}")
            return None

    @staticmethod
    def parse_price_change(data: Dict[str, Any]) -> Optional[Dict]:
        """
        Parse price_change message

        Args:
            data: Raw message data

        Returns:
            Parsed price change dictionary or None if invalid
        """
        try:
            price_change = {
                "market_id": data.get("market"),
                "changes": [],
                "message_type": "price_change"
            }

            # Parse price changes
            if "changes" in data:
                for change in data["changes"]:
                    price_change["changes"].append({
                        "asset_id": change.get("asset_id"),
                        "price": float(change.get("price", 0)),
                        "size": float(change.get("size", 0)),
                        "side": change.get("side"),
                        "hash": change.get("hash")
                    })

            # Also include best bid/ask if available
            if "best_bid" in data:
                price_change["best_bid"] = float(data["best_bid"])
            if "best_ask" in data:
                price_change["best_ask"] = float(data["best_ask"])

            return price_change

        except Exception as e:
            logger.error(f"Error parsing price_change message: {e}")
            return None

    @staticmethod
    def extract_user_from_trade(trade: Dict[str, Any]) -> Optional[str]:
        """
        Extract user wallet address from trade data if available

        Args:
            trade: Trade dictionary

        Returns:
            Wallet address or None
        """
        # Note: WebSocket trade messages may not include user info
        # This would need to be enriched from the REST API
        return trade.get("user") or trade.get("maker") or trade.get("taker")

    @staticmethod
    def is_large_trade(trade: Dict[str, Any], threshold_usd: float = 2000) -> bool:
        """
        Check if trade is above size threshold

        Args:
            trade: Trade dictionary
            threshold_usd: Minimum trade size in USD

        Returns:
            True if trade is large
        """
        return trade.get("value_usd", 0) >= threshold_usd

    @staticmethod
    def get_trade_direction(trade: Dict[str, Any]) -> str:
        """
        Get normalized trade direction

        Args:
            trade: Trade dictionary

        Returns:
            "BUY" or "SELL"
        """
        side = trade.get("side", "").upper()
        return "BUY" if side == "BUY" else "SELL"

    @staticmethod
    def format_timestamp(timestamp_ms: int) -> str:
        """
        Format timestamp to readable string

        Args:
            timestamp_ms: Timestamp in milliseconds

        Returns:
            Formatted datetime string
        """
        try:
            dt = datetime.fromtimestamp(timestamp_ms / 1000)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "Invalid timestamp"
