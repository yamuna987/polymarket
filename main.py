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
from src.filters.pipeline import create_filter_pipeline
from src.signals.pipeline import create_signal_pipeline
from src.telegram.alert_sender import TelegramAlertSender, format_telegram_alert


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

        # Initialize filter pipeline
        self.filter_pipeline = create_filter_pipeline(self.config, self.api_client)

        # Initialize signal pipeline
        self.signal_pipeline = create_signal_pipeline(self.config, self.api_client)

        # Initialize Telegram alert sender
        telegram_config = self.config.get("telegram", {})
        self.telegram_sender = None
        if telegram_config.get("enabled", False):
            self.telegram_sender = TelegramAlertSender(
                bot_token=telegram_config.get("bot_token"),
                chat_id=telegram_config.get("chat_id"),
                rate_limit_per_second=telegram_config.get("rate_limit_per_second", 1.0)
            )
            self.logger.info("Telegram alert sender initialized")

        # Initialize WebSocket listener
        self.ws_listener = None

        # Statistics
        self.stats = {
            "start_time": datetime.now(),
            "trades_processed": 0,
            "trades_filtered": 0,
            "trades_passed_filters": 0,
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

            # Phase 2: Apply filter pipeline
            should_process, filter_reason, enriched_trade = self.filter_pipeline.process_trade(trade_data)

            if not should_process:
                self.stats["trades_filtered"] += 1
                self.logger.debug(f"Trade filtered: {filter_reason}")
                return

            self.stats["trades_passed_filters"] += 1

            # Phase 3: Detect signals
            signals = self.signal_pipeline.process_trade(enriched_trade)

            if signals:
                self.stats["signals_detected"] += len(signals)

                # Get combined confidence
                combined_confidence = self.signal_pipeline.get_combined_confidence(signals)

                self.logger.info(
                    f"🎯 {len(signals)} signal(s) detected with combined confidence: {combined_confidence:.2f}"
                )

                # Phase 4: Send Telegram alert
                await self._send_alert(enriched_trade, signals, combined_confidence)

            else:
                self.logger.info(f"✓ Trade passed filters but no signals detected")

        except Exception as e:
            self.logger.error(f"Error processing trade: {e}")
            self.stats["api_errors"] += 1

    async def _send_alert(self, trade: dict, signals: list, combined_confidence: float):
        """
        Enrich trade data and send Telegram alert

        Args:
            trade: Enriched trade data
            signals: List of detected signals
            combined_confidence: Combined confidence score
        """
        if not self.telegram_sender:
            self.logger.debug("Telegram sender not configured, skipping alert")
            return

        try:
            # Fetch trader stats if not already in enriched trade
            trader_stats = None
            trader_wallet = trade.get("trader_wallet")

            if trader_wallet and "trader_profile" in trade:
                # Calculate win rate from profile
                profile = trade["trader_profile"]
                positions = self.api_client.get_positions(trader_wallet, limit=100)

                if positions:
                    win_rate = self.api_client.calculate_win_rate(positions)

                    # Calculate total P&L
                    total_pnl = sum(
                        float(pos.get("position_value", 0)) - float(pos.get("cost_basis", 0))
                        for pos in positions
                    )

                    trader_stats = {
                        "win_rate": win_rate,
                        "total_pnl": total_pnl,
                        "total_markets_traded": len(set(pos.get("market_id") for pos in positions))
                    }

            # Format alert message
            message = format_telegram_alert(
                trade=trade,
                signals=signals,
                combined_confidence=combined_confidence,
                trader_stats=trader_stats
            )

            # Queue alert
            success = self.telegram_sender.enqueue_alert(message)

            if success:
                self.stats["alerts_sent"] += 1
                self.logger.info("✓ Alert queued for Telegram")
            else:
                self.logger.warning("Alert queue full, alert dropped")

        except Exception as e:
            self.logger.error(f"Error sending Telegram alert: {e}")

    async def start(self):
        """Start the signal detector"""
        self.running = True

        # Start Telegram sender
        if self.telegram_sender:
            await self.telegram_sender.start()
            self.logger.info("Telegram alert sender started")

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
                filter_stats = self.filter_pipeline.get_stats()
                signal_stats = self.signal_pipeline.get_stats()
                telegram_stats = self.telegram_sender.get_stats() if self.telegram_sender else {}

                self.logger.info("=" * 60)
                self.logger.info("STATISTICS")
                self.logger.info("=" * 60)
                self.logger.info(f"Uptime: {uptime:.0f}s")
                self.logger.info(f"Trades Processed: {self.stats['trades_processed']}")
                self.logger.info(f"Trades Filtered: {self.stats['trades_filtered']}")
                self.logger.info(f"Trades Passed Filters: {self.stats['trades_passed_filters']}")
                self.logger.info(f"Filter Pass Rate: {filter_stats.get('pass_rate_pct', 0):.1f}%")
                self.logger.info(f"Signals Detected: {self.stats['signals_detected']}")
                self.logger.info(f"Multi-Signal Trades: {signal_stats.get('multi_signal_trades', 0)}")
                self.logger.info(f"Alerts Sent: {self.stats['alerts_sent']}")
                self.logger.info(f"API Errors: {self.stats['api_errors']}")
                self.logger.info(f"WebSocket Messages: {ws_stats.get('messages_received', 0)}")
                self.logger.info(f"WebSocket Trades: {ws_stats.get('trades_received', 0)}")
                self.logger.info(
                    f"Cache Hit Rate: {cache_stats.get('hit_rate_pct', 0):.1f}% "
                    f"({cache_stats.get('hits', 0)}/{cache_stats.get('total_requests', 0)})"
                )
                if telegram_stats:
                    self.logger.info(
                        f"Telegram: {telegram_stats.get('messages_sent', 0)} sent, "
                        f"{telegram_stats.get('messages_failed', 0)} failed, "
                        f"{telegram_stats.get('queue_size', 0)} queued"
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

        # Stop Telegram sender
        if self.telegram_sender:
            await self.telegram_sender.stop()
            self.logger.info("Telegram alert sender stopped")

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
