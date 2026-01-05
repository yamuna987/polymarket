#!/usr/bin/env python3
"""
WebSocket Listener for Polymarket CLOB
Connects to real-time trade stream and processes messages
"""

import asyncio
import websockets
import json
import logging
from typing import Callable, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class PolymarketWebSocketListener:
    """WebSocket client for Polymarket real-time data"""

    def __init__(
        self,
        websocket_url: str,
        on_trade_callback: Optional[Callable] = None,
        on_book_callback: Optional[Callable] = None,
        on_price_change_callback: Optional[Callable] = None
    ):
        """
        Initialize WebSocket listener

        Args:
            websocket_url: WebSocket URL to connect to
            on_trade_callback: Callback function for trade messages
            on_book_callback: Callback function for book messages
            on_price_change_callback: Callback function for price change messages
        """
        self.websocket_url = websocket_url
        self.on_trade_callback = on_trade_callback
        self.on_book_callback = on_book_callback
        self.on_price_change_callback = on_price_change_callback

        self.websocket = None
        self.running = False
        self.reconnect_delay = 5
        self.max_reconnect_delay = 60

        # Statistics
        self.messages_received = 0
        self.trades_received = 0
        self.last_message_time = None
        self.connection_start_time = None

    async def connect(self):
        """Establish WebSocket connection"""
        try:
            logger.info(f"Connecting to WebSocket: {self.websocket_url}")
            self.websocket = await websockets.connect(self.websocket_url)
            self.connection_start_time = datetime.now()
            logger.info("WebSocket connected successfully")

            # Subscribe to market channel
            await self.subscribe_to_market()

            return True

        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            return False

    async def subscribe_to_market(self):
        """Subscribe to the market channel"""
        try:
            subscribe_message = {
                "type": "subscribe",
                "channel": "market"
            }

            await self.websocket.send(json.dumps(subscribe_message))
            logger.info("Subscribed to market channel")

        except Exception as e:
            logger.error(f"Failed to subscribe to market channel: {e}")

    async def listen(self):
        """
        Main listening loop
        Continuously receives and processes messages
        """
        self.running = True
        current_reconnect_delay = self.reconnect_delay

        while self.running:
            try:
                # Connect if not connected
                if not self.websocket:
                    connected = await self.connect()
                    if not connected:
                        logger.warning(f"Retrying connection in {current_reconnect_delay}s...")
                        await asyncio.sleep(current_reconnect_delay)
                        current_reconnect_delay = min(
                            current_reconnect_delay * 2,
                            self.max_reconnect_delay
                        )
                        continue

                # Reset reconnect delay on successful connection
                current_reconnect_delay = self.reconnect_delay

                # Receive message
                message = await self.websocket.recv()
                self.last_message_time = datetime.now()
                self.messages_received += 1

                # Process message
                await self.process_message(message)

            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"WebSocket connection closed: {e}")
                self.websocket = None
                await asyncio.sleep(current_reconnect_delay)

            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
                await asyncio.sleep(1)

    async def process_message(self, message: str):
        """
        Process incoming WebSocket message

        Args:
            message: Raw message string
        """
        try:
            data = json.loads(message)

            # Determine message type
            message_type = data.get("event_type") or data.get("type")

            if not message_type:
                logger.debug(f"Unknown message format: {message[:100]}")
                return

            # Route to appropriate handler
            if message_type == "last_trade_price":
                await self.handle_trade(data)

            elif message_type == "book":
                await self.handle_book(data)

            elif message_type == "price_change":
                await self.handle_price_change(data)

            elif message_type in ["tick_size_change", "best_bid_ask", "new_market", "market_resolved"]:
                logger.debug(f"Received {message_type} message")
                # Can add handlers for these later

            else:
                logger.debug(f"Unhandled message type: {message_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message as JSON: {e}")

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def handle_trade(self, data: Dict[str, Any]):
        """
        Handle trade message

        Args:
            data: Trade message data
        """
        try:
            self.trades_received += 1

            # Extract trade information
            trade = {
                "asset_id": data.get("asset_id"),
                "market_id": data.get("market"),
                "price": float(data.get("price", 0)),
                "size": float(data.get("size", 0)),
                "side": data.get("side"),
                "timestamp": data.get("timestamp"),
                "fee_rate_bps": data.get("fee_rate_bps"),
                "message_type": "trade"
            }

            # Calculate trade value in USD
            trade["value_usd"] = trade["price"] * trade["size"]

            logger.debug(
                f"Trade: {trade['side']} {trade['size']} @ ${trade['price']} "
                f"(${trade['value_usd']:.2f}) - Market: {trade['market_id']}"
            )

            # Call callback if provided
            if self.on_trade_callback:
                await self.on_trade_callback(trade)

        except Exception as e:
            logger.error(f"Error handling trade message: {e}")

    async def handle_book(self, data: Dict[str, Any]):
        """
        Handle orderbook message

        Args:
            data: Book message data
        """
        try:
            # Call callback if provided
            if self.on_book_callback:
                await self.on_book_callback(data)

        except Exception as e:
            logger.error(f"Error handling book message: {e}")

    async def handle_price_change(self, data: Dict[str, Any]):
        """
        Handle price change message

        Args:
            data: Price change message data
        """
        try:
            # Call callback if provided
            if self.on_price_change_callback:
                await self.on_price_change_callback(data)

        except Exception as e:
            logger.error(f"Error handling price change message: {e}")

    async def stop(self):
        """Stop the WebSocket listener"""
        logger.info("Stopping WebSocket listener...")
        self.running = False

        if self.websocket:
            await self.websocket.close()
            self.websocket = None

        logger.info("WebSocket listener stopped")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get listener statistics

        Returns:
            Dictionary with stats
        """
        uptime = None
        if self.connection_start_time:
            uptime = (datetime.now() - self.connection_start_time).total_seconds()

        return {
            "running": self.running,
            "connected": self.websocket is not None,
            "messages_received": self.messages_received,
            "trades_received": self.trades_received,
            "last_message_time": self.last_message_time.isoformat() if self.last_message_time else None,
            "uptime_seconds": uptime
        }


async def main():
    """Test the WebSocket listener"""
    async def on_trade(trade):
        print(f"[TRADE] {trade['side']} {trade['size']} @ ${trade['price']:.4f} = ${trade['value_usd']:.2f}")

    listener = PolymarketWebSocketListener(
        websocket_url="wss://ws-subscriptions-clob.polymarket.com/ws/market",
        on_trade_callback=on_trade
    )

    try:
        await listener.listen()
    except KeyboardInterrupt:
        await listener.stop()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    asyncio.run(main())
