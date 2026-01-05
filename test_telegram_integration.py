#!/usr/bin/env python3
"""
Test Telegram Integration
Demonstrates alert formatting without actually sending to Telegram
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.telegram.alert_sender import format_telegram_alert


def main():
    print("=" * 70)
    print("TELEGRAM ALERT INTEGRATION - PREVIEW TEST")
    print("=" * 70)
    print()
    print("This test shows what alerts will look like when sent to Telegram.")
    print("The alerts are formatted in HTML for rich formatting.")
    print()
    print("=" * 70)
    print()

    # Example 1: Fresh Wallet + Size Anomaly
    print("EXAMPLE 1: Fresh Wallet + Size Anomaly Signal")
    print("=" * 70)

    trade1 = {
        "market_id": "0x1a2b3c4d5e6f7890abcdef1234567890abcdef12",
        "trader_wallet": "0xfreshwallet0123456789abcdef",
        "side": "BUY",
        "value_usd": 5000.0
    }

    signals1 = [
        {
            "signal_type": "fresh_wallet",
            "wallet_age_days": 3,
            "confidence": 0.95
        },
        {
            "signal_type": "size_anomaly",
            "multiplier": 4.2,
            "average_size": 1190.0,
            "confidence": 0.75
        }
    ]

    trader_stats1 = {
        "win_rate": 0.82,
        "total_pnl": 12450.50,
        "total_markets_traded": 15
    }

    message1 = format_telegram_alert(trade1, signals1, 0.92, trader_stats1)
    print(message1)
    print()

    # Example 2: Contrarian Trade
    print("EXAMPLE 2: Contrarian Signal")
    print("=" * 70)

    trade2 = {
        "market_id": "0x9876543210fedcba0987654321fedcba09876543",
        "trader_wallet": "0xcontrarian9876543210fedcba",
        "side": "BUY",
        "value_usd": 8500.0
    }

    signals2 = [
        {
            "signal_type": "contrarian",
            "market_odds": 0.12,
            "consensus_side": "NO",
            "confidence": 0.88
        }
    ]

    trader_stats2 = {
        "win_rate": 0.73,
        "total_pnl": 8920.25,
        "total_markets_traded": 42
    }

    message2 = format_telegram_alert(trade2, signals2, 0.88, trader_stats2)
    print(message2)
    print()

    # Example 3: Cluster Detection
    print("EXAMPLE 3: Cluster Signal")
    print("=" * 70)

    trade3 = {
        "market_id": "0xabcdef1234567890abcdef1234567890abcdef12",
        "trader_wallet": "0xcluster0123456789abcdef01",
        "side": "BUY",
        "value_usd": 3200.0
    }

    signals3 = [
        {
            "signal_type": "cluster",
            "cluster_size": 5,
            "total_volume": 15750.0,
            "confidence": 0.78
        }
    ]

    message3 = format_telegram_alert(trade3, signals3, 0.78, None)
    print(message3)
    print()

    # Example 4: Multi-Signal (Very High Confidence)
    print("EXAMPLE 4: Multi-Signal Alert (Very High Confidence)")
    print("=" * 70)

    trade4 = {
        "market_id": "0xmultisignal1234567890abcdef1234567890abcd",
        "trader_wallet": "0xwhale0123456789abcdef0123",
        "side": "BUY",
        "value_usd": 25000.0
    }

    signals4 = [
        {
            "signal_type": "fresh_wallet",
            "wallet_age_days": 2,
            "confidence": 0.98
        },
        {
            "signal_type": "size_anomaly",
            "multiplier": 8.5,
            "average_size": 2940.0,
            "confidence": 0.92
        },
        {
            "signal_type": "timing",
            "timing_signals": [
                {"type": "early_entry", "minutes_after_creation": 15},
                {"type": "unusual_hours", "hour_utc": 3}
            ],
            "confidence": 0.85
        }
    ]

    trader_stats4 = {
        "win_rate": 0.91,
        "total_pnl": 45670.80,
        "total_markets_traded": 8
    }

    message4 = format_telegram_alert(trade4, signals4, 0.94, trader_stats4)
    print(message4)
    print()

    # Summary
    print("=" * 70)
    print("SETUP INSTRUCTIONS")
    print("=" * 70)
    print("""
To enable Telegram alerts:

1. Create a Telegram Bot:
   - Open Telegram and search for @BotFather
   - Send /newbot and follow the prompts
   - Copy the bot token (looks like: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)

2. Get Your Chat ID:
   - Add your bot to a chat or start a conversation with it
   - Send any message to the bot
   - Visit: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   - Look for "chat":{"id": YOUR_CHAT_ID in the response

3. Configure .env file:
   - Copy .env.example to .env
   - Set TELEGRAM_BOT_TOKEN=your_bot_token_here
   - Set TELEGRAM_CHAT_ID=your_chat_id_here

4. Enable in config.yaml:
   - Ensure telegram.enabled is set to true
   - Adjust rate_limit_per_second if needed (default: 1)

5. Run the system:
   - python main.py (for live monitoring)
   - Alerts will be sent to your Telegram chat automatically

Note: Telegram rate limits are ~30 messages/second per bot, but we use
1 message/second by default to avoid overwhelming the chat.
""")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
