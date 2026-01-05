#!/usr/bin/env python3
"""
Telegram Alert Sender
Sends trading signal alerts to Telegram using Bot API
"""

import asyncio
import logging
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)


class TelegramAlertSender:
    """Send alerts to Telegram"""

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        rate_limit_per_second: float = 1.0,
        max_queue_size: int = 100
    ):
        """
        Initialize Telegram alert sender

        Args:
            bot_token: Telegram bot token
            chat_id: Chat ID to send messages to
            rate_limit_per_second: Max messages per second
            max_queue_size: Maximum queue size
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.rate_limit = rate_limit_per_second
        self.max_queue_size = max_queue_size

        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        # Message queue
        self.queue = deque(maxlen=max_queue_size)

        # Statistics
        self.stats = {
            "messages_sent": 0,
            "messages_failed": 0,
            "queue_overflows": 0,
            "last_sent_time": None
        }

        # Queue processor task
        self.queue_task = None
        self.running = False

        logger.info(
            f"TelegramAlertSender initialized - Rate limit: {rate_limit_per_second}/sec, "
            f"Queue size: {max_queue_size}"
        )

    async def start(self):
        """Start the queue processor"""
        self.running = True
        self.queue_task = asyncio.create_task(self._process_queue())
        logger.info("Telegram alert sender started")

    async def stop(self):
        """Stop the queue processor"""
        self.running = False
        if self.queue_task:
            self.queue_task.cancel()
            try:
                await self.queue_task
            except asyncio.CancelledError:
                pass
        logger.info("Telegram alert sender stopped")

    def enqueue_alert(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Add alert to queue

        Args:
            message: Message text (supports HTML or Markdown)
            parse_mode: Parse mode (HTML or Markdown)

        Returns:
            True if queued successfully
        """
        if len(self.queue) >= self.max_queue_size:
            self.stats["queue_overflows"] += 1
            logger.warning("Alert queue full, dropping message")
            return False

        self.queue.append({
            "text": message,
            "parse_mode": parse_mode,
            "queued_at": datetime.now()
        })

        logger.debug(f"Alert queued (queue size: {len(self.queue)})")
        return True

    async def _process_queue(self):
        """Process message queue with rate limiting"""
        delay = 1.0 / self.rate_limit

        while self.running:
            try:
                if self.queue:
                    message = self.queue.popleft()
                    await self._send_message(message)
                    await asyncio.sleep(delay)
                else:
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing queue: {e}")
                await asyncio.sleep(1)

    async def _send_message(self, message: Dict[str, Any]):
        """
        Send message to Telegram

        Args:
            message: Message dictionary with text and parse_mode
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "chat_id": self.chat_id,
                    "text": message["text"],
                    "parse_mode": message.get("parse_mode", "HTML"),
                    "disable_web_page_preview": True
                }

                async with session.post(self.api_url, json=payload, timeout=10) as response:
                    if response.status == 200:
                        self.stats["messages_sent"] += 1
                        self.stats["last_sent_time"] = datetime.now()
                        logger.info("✓ Alert sent to Telegram")
                    else:
                        error_text = await response.text()
                        self.stats["messages_failed"] += 1
                        logger.error(f"Failed to send Telegram message: {response.status} - {error_text}")

        except Exception as e:
            self.stats["messages_failed"] += 1
            logger.error(f"Error sending Telegram message: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get sender statistics"""
        return {
            "messages_sent": self.stats["messages_sent"],
            "messages_failed": self.stats["messages_failed"],
            "queue_size": len(self.queue),
            "queue_overflows": self.stats["queue_overflows"],
            "last_sent_time": self.stats["last_sent_time"].isoformat() if self.stats["last_sent_time"] else None
        }


def format_telegram_alert(
    trade: Dict[str, Any],
    signals: list,
    combined_confidence: float,
    trader_stats: Optional[Dict[str, Any]] = None
) -> str:
    """
    Format alert for Telegram (HTML)

    Args:
        trade: Trade dictionary
        signals: List of detected signals
        combined_confidence: Combined confidence score
        trader_stats: Optional trader statistics

    Returns:
        Formatted HTML message
    """
    # Extract trade info
    market_id = trade.get("market_id", "unknown")[:12] + "..."
    wallet = trade.get("trader_wallet", "unknown")
    wallet_short = wallet[:10] + "..." if len(wallet) > 10 else wallet
    side = trade.get("side", "UNKNOWN")
    value = trade.get("value_usd", 0)

    # Confidence emoji
    if combined_confidence >= 0.9:
        conf_emoji = "🔥🔥🔥🔥🔥"
        conf_text = "VERY HIGH"
    elif combined_confidence >= 0.8:
        conf_emoji = "🔥🔥🔥🔥"
        conf_text = "HIGH"
    elif combined_confidence >= 0.7:
        conf_emoji = "🔥🔥🔥"
        conf_text = "MEDIUM-HIGH"
    elif combined_confidence >= 0.6:
        conf_emoji = "🔥🔥"
        conf_text = "MEDIUM"
    else:
        conf_emoji = "🔥"
        conf_text = "LOW"

    # Build signal descriptions
    signal_lines = []
    for signal in signals:
        sig_type = signal.get("signal_type", "unknown")

        if sig_type == "fresh_wallet":
            age = signal.get("wallet_age_days", "?")
            signal_lines.append(f"🆕 <b>Fresh Wallet</b> ({age} days old)")

        elif sig_type == "size_anomaly":
            mult = signal.get("multiplier", 0)
            signal_lines.append(f"📊 <b>Size Anomaly</b> ({mult:.1f}x average)")

        elif sig_type == "timing":
            types = [s["type"] for s in signal.get("timing_signals", [])]
            signal_lines.append(f"⏰ <b>Timing</b> ({', '.join(types)})")

        elif sig_type == "odds_movement":
            pct = signal.get("movement_pct", 0)
            direction = signal.get("direction", "?")
            signal_lines.append(f"📈 <b>Odds Movement</b> ({pct:+.1f}% {direction})")

        elif sig_type == "contrarian":
            odds = signal.get("market_odds", 0)
            consensus = signal.get("consensus_side", "?")
            signal_lines.append(f"🔄 <b>Contrarian</b> (vs {consensus} at {odds:.0%})")

        elif sig_type == "cluster":
            size = signal.get("cluster_size", 0)
            signal_lines.append(f"👥 <b>Cluster</b> ({size} wallets)")

    signals_text = "\n".join(signal_lines)

    # Trader stats section
    trader_section = ""
    if trader_stats:
        win_rate = trader_stats.get("win_rate", 0)
        total_pnl = trader_stats.get("total_pnl", 0)
        markets = trader_stats.get("total_markets_traded", 0)

        trader_section = f"""
📊 <b>Trader Stats:</b>
   Win Rate: {win_rate:.1%}
   Total P&L: ${total_pnl:,.2f}
   Markets Traded: {markets}
"""

    # Build final message
    message = f"""
🚨 <b>TRADING SIGNAL DETECTED</b>

💰 <b>Trade:</b>
   Market: <code>{market_id}</code>
   Side: {side}
   Value: ${value:,.2f}

🎯 <b>Signals ({len(signals)}):</b>
{signals_text}

{conf_emoji} <b>Confidence: {combined_confidence:.2f}</b> ({conf_text})
{trader_section}
🔗 <a href="https://polymarket.com/event/{market_id}">View Market</a>
👤 <a href="https://polymarket.com/profile/{wallet}">View Trader</a>
"""

    return message.strip()
