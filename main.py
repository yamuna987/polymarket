#!/usr/bin/env python3
"""
Polymarket Signal Detector - Main Entry Point

Real-time trading signal detection system for Polymarket
"""

import asyncio
import signal
import sys
from datetime import datetime
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import setup_logging
from src.utils.config import load_config, get_database_url
from src.database.models import DatabaseManager
from src.api.polymarket_client import PolymarketAPIClient
from src.api.cache import APICache
from src.websocket.listener import PolymarketWebSocketListener


class SignalDetector:
    """Main application class for signal detection"""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the signal detector

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = load_config(config_path)

        # Setup logging
        log_config = self.config.get("logging", {})
        self.logger = setup_logging(
            log_file=log_config.get("file"),
            log_level=log_config.get("level", "INFO"),
            console=log_config.get("console", True),
            log_format=log_config.get("format")
        )

        self.logger.info("=" * 60)
        self.logger.info("Polymarket Signal Detector Starting...")
        self.logger.info("=" * 60)

        # Initialize database
        db_url = get_database_url(self.config)
        self.db_manager = DatabaseManager(db_url)
        self.db_manager.create_tables()

        # Initialize API client
        api_config = self.config.get("api", {})
        self.api_client = PolymarketAPIClient(api_config)

        # Initialize cache
        cache_config = self.config.get("cache", {})
        self.cache = APICache(
            profile_ttl=cache_config.get("profile_ttl", 3600),
            market_ttl=cache_config.get("market_ttl", 1800)
        )

        # Initialize WebSocket listener
        self.ws_listener = None

        # Statistics
        self.stats = {
            "start_time": datetime.now(),
            "trades_processed": 0,
            "signals_detected": 0,
            "alerts_sent": 0,
            "api_errors": 0
        }

        # Shutdown flag
        self.running = False

    async def on_trade_received(self, trade_data: dict):
        """
        Callback for when a trade is received from WebSocket

        Args:
            trade_data: Trade data from WebSocket
        """
        try:
            self.stats["trades_processed"] += 1

            self.logger.info(
                f"[TRADE] {trade_data['side']} {trade_data['size']:.2f} @ "
                f"${trade_data['price']:.4f} = ${trade_data['value_usd']:.2f} "
                f"(Market: {trade_data['market_id'][:10]}...)"
            )

            # TODO: Phase 2 - Apply filters
            # - Market filter (category, timeframe)
            # - Size filter (< $2000)
            # - LP detection

            # TODO: Phase 3 - Detect signals
            # - Fresh wallet
            # - Size anomaly
            # - Timing
            # - Odds movement
            # - Contrarian
            # - Cluster

            # TODO: Phase 4 - Enrich and alert
            # - Fetch user profile
            # - Calculate win rate
            # - Send to Discord

            # For now, just store the trade (if we have wallet info)
            # Note: WebSocket trades may not include wallet address
            # We'd need to enrich this from the REST API

        except Exception as e:
            self.logger.error(f"Error processing trade: {e}")
            self.stats["api_errors"] += 1

    async def start(self):
        """Start the signal detector"""
        self.running = True

        self.logger.info("Initializing WebSocket listener...")

        # Create WebSocket listener
        ws_url = self.config["api"]["websocket_url"]
        self.ws_listener = PolymarketWebSocketListener(
            websocket_url=ws_url,
            on_trade_callback=self.on_trade_received
        )

        # Start monitoring tasks
        monitoring_task = asyncio.create_task(self.monitor_stats())

        self.logger.info("Starting WebSocket listener...")
        self.logger.info("Press Ctrl+C to stop")

        try:
            # Start listening (this runs indefinitely)
            await self.ws_listener.listen()

        except asyncio.CancelledError:
            self.logger.info("Received shutdown signal")

        finally:
            # Cleanup
            monitoring_task.cancel()
            await self.shutdown()

    async def monitor_stats(self):
        """Periodically print statistics"""
        interval = self.config.get("monitoring", {}).get("stats_interval", 60)

        while self.running:
            try:
                await asyncio.sleep(interval)

                # Print stats
                uptime = (datetime.now() - self.stats["start_time"]).total_seconds()
                ws_stats = self.ws_listener.get_stats() if self.ws_listener else {}
                cache_stats = self.cache.get_stats()

                self.logger.info("=" * 60)
                self.logger.info("STATISTICS")
                self.logger.info("=" * 60)
                self.logger.info(f"Uptime: {uptime:.0f}s")
                self.logger.info(f"Trades Processed: {self.stats['trades_processed']}")
                self.logger.info(f"Signals Detected: {self.stats['signals_detected']}")
                self.logger.info(f"Alerts Sent: {self.stats['alerts_sent']}")
                self.logger.info(f"API Errors: {self.stats['api_errors']}")
                self.logger.info(f"WebSocket Messages: {ws_stats.get('messages_received', 0)}")
                self.logger.info(f"WebSocket Trades: {ws_stats.get('trades_received', 0)}")
                self.logger.info(
                    f"Cache Hit Rate: {cache_stats.get('hit_rate_pct', 0):.1f}% "
                    f"({cache_stats.get('hits', 0)}/{cache_stats.get('total_requests', 0)})"
                )
                self.logger.info("=" * 60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitor_stats: {e}")

    async def shutdown(self):
        """Cleanup and shutdown"""
        self.logger.info("Shutting down...")
        self.running = False

        # Stop WebSocket
        if self.ws_listener:
            await self.ws_listener.stop()

        # Close API client
        if self.api_client:
            self.api_client.close()

        # Print final stats
        self.logger.info("=" * 60)
        self.logger.info("FINAL STATISTICS")
        self.logger.info("=" * 60)
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds()
        self.logger.info(f"Total Runtime: {uptime:.0f}s")
        self.logger.info(f"Total Trades: {self.stats['trades_processed']}")
        self.logger.info(f"Total Signals: {self.stats['signals_detected']}")
        self.logger.info(f"Total Alerts: {self.stats['alerts_sent']}")
        self.logger.info("=" * 60)
        self.logger.info("Shutdown complete")


def main():
    """Main entry point"""
    # Create signal detector
    detector = SignalDetector()

    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        print("\n\nShutdown requested... cleaning up...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the detector
    try:
        asyncio.run(detector.start())
    except KeyboardInterrupt:
        print("\n\nShutdown requested...")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
