#!/usr/bin/env python3
"""
Send a test alert to Telegram to verify configuration
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.telegram.alert_sender import TelegramAlertSender, format_telegram_alert
from src.utils.config import load_config


async def main():
    print("=" * 70)
    print("TELEGRAM TEST - SENDING REAL ALERT")
    print("=" * 70)
    print()

    # Load config
    config = load_config()
    telegram_config = config.get("telegram", {})

    if not telegram_config.get("enabled"):
        print("❌ Telegram is not enabled in config.yaml")
        print("   Set telegram.enabled: true")
        return

    bot_token = telegram_config.get("bot_token")
    chat_id = telegram_config.get("chat_id")

    if not bot_token or not chat_id:
        print("❌ Telegram credentials not configured")
        print("   Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        return

    print(f"✓ Bot Token: {bot_token[:20]}...")
    print(f"✓ Chat ID: {chat_id}")
    print()

    # Create test alert data
    test_trade = {
        "market_id": "0xTEST1234567890abcdef1234567890abcdef12",
        "trader_wallet": "0xTESTwallet0123456789abcdef",
        "side": "BUY",
        "value_usd": 10000.0
    }

    test_signals = [
        {
            "signal_type": "fresh_wallet",
            "wallet_age_days": 5,
            "confidence": 0.90
        },
        {
            "signal_type": "size_anomaly",
            "multiplier": 3.5,
            "average_size": 2857.0,
            "confidence": 0.80
        }
    ]

    test_trader_stats = {
        "win_rate": 0.85,
        "total_pnl": 15000.00,
        "total_markets_traded": 20
    }

    # Initialize sender
    print("Initializing Telegram sender...")
    sender = TelegramAlertSender(
        bot_token=bot_token,
        chat_id=chat_id,
        rate_limit_per_second=1.0
    )

    await sender.start()
    print("✓ Telegram sender started")
    print()

    # Format and send alert
    print("Formatting test alert...")
    message = format_telegram_alert(
        trade=test_trade,
        signals=test_signals,
        combined_confidence=0.88,
        trader_stats=test_trader_stats
    )

    print("Sending to Telegram...")
    success = sender.enqueue_alert(message)

    if success:
        print("✓ Alert queued")
        # Wait for it to send
        await asyncio.sleep(2)

        stats = sender.get_stats()
        if stats.get("messages_sent", 0) > 0:
            print()
            print("=" * 70)
            print("✅ SUCCESS! Alert sent to Telegram")
            print("=" * 70)
            print()
            print("Check your Telegram chat - you should see a test alert!")
            print()
            print(f"Stats: {stats['messages_sent']} sent, {stats['messages_failed']} failed")
        else:
            print(f"⚠️  Alert queued but not sent yet. Stats: {stats}")
    else:
        print("❌ Failed to queue alert (queue full)")

    # Cleanup
    await sender.stop()
    print()
    print("Test complete!")


if __name__ == "__main__":
    asyncio.run(main())
