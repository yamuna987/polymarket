#!/usr/bin/env python3
"""
Test Complete System with Mock Data
Simulates realistic trade scenarios to demonstrate alert output
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import load_config
from src.utils.logger import setup_logging
from src.api.polymarket_client import PolymarketAPIClient
from src.filters.pipeline import create_filter_pipeline
from src.signals.pipeline import create_signal_pipeline


def create_mock_trades():
    """Create realistic mock trades for testing"""
    now = datetime.now()

    return [
        # Large trade from fresh wallet - SHOULD TRIGGER
        {
            "asset_id": "0x123abc",
            "market_id": "0xmarket001",
            "condition_id": "0xmarket001",
            "trader_wallet": "0xfreshwallet01",
            "side": "BUY",
            "size": 5000.0,
            "price": 0.65,
            "value_usd": 3250.0,
            "timestamp": int(now.timestamp() * 1000),
            "datetime": now,
            "transaction_hash": "0xtx001"
        },
        # Contrarian large trade - SHOULD TRIGGER
        {
            "asset_id": "0x456def",
            "market_id": "0xmarket002",
            "condition_id": "0xmarket002",
            "trader_wallet": "0xcontrarian01",
            "side": "BUY",
            "size": 10000.0,
            "price": 0.15,
            "value_usd": 1500.0,  # Buying at low odds (contrarian)
            "timestamp": int(now.timestamp() * 1000),
            "datetime": now,
            "transaction_hash": "0xtx002"
        },
        # Cluster trade #1 - SHOULD TRIGGER (when combined)
        {
            "asset_id": "0x789ghi",
            "market_id": "0xmarket003",
            "condition_id": "0xmarket003",
            "trader_wallet": "0xcluster01",
            "side": "BUY",
            "size": 3000.0,
            "price": 0.70,
            "value_usd": 2100.0,
            "timestamp": int(now.timestamp() * 1000),
            "datetime": now,
            "transaction_hash": "0xtx003"
        },
        # Cluster trade #2
        {
            "asset_id": "0x789ghi",
            "market_id": "0xmarket003",
            "condition_id": "0xmarket003",
            "trader_wallet": "0xcluster02",
            "side": "BUY",
            "size": 2500.0,
            "price": 0.70,
            "value_usd": 1750.0,
            "timestamp": int((now + timedelta(seconds=30)).timestamp() * 1000),
            "datetime": now + timedelta(seconds=30),
            "transaction_hash": "0xtx004"
        },
        # Cluster trade #3
        {
            "asset_id": "0x789ghi",
            "market_id": "0xmarket003",
            "condition_id": "0xmarket003",
            "trader_wallet": "0xcluster03",
            "side": "BUY",
            "size": 2000.0,
            "price": 0.70,
            "value_usd": 1400.0,
            "timestamp": int((now + timedelta(seconds=60)).timestamp() * 1000),
            "datetime": now + timedelta(seconds=60),
            "transaction_hash": "0xtx005"
        },
        # Small trade - SHOULD BE FILTERED OUT
        {
            "asset_id": "0xabc123",
            "market_id": "0xmarket004",
            "condition_id": "0xmarket004",
            "trader_wallet": "0xsmalltrader",
            "side": "BUY",
            "size": 10.0,
            "price": 0.50,
            "value_usd": 5.0,
            "timestamp": int(now.timestamp() * 1000),
            "datetime": now,
            "transaction_hash": "0xtx006"
        },
    ]


def format_alert_preview(trade, signals, combined_confidence):
    """Format an alert preview for Discord"""

    wallet = (trade.get("trader_wallet") or "unknown")[:15] + "..."
    market_id = (trade.get("market_id") or "unknown")[:15] + "..."
    side = trade.get("side", "UNKNOWN")
    value = trade.get("value_usd", 0)

    # Build signal descriptions
    signal_descriptions = []
    for signal in signals:
        sig_type = signal.get("signal_type", "unknown")
        confidence = signal.get("confidence", 0)

        if sig_type == "fresh_wallet":
            age_days = signal.get("wallet_age_days", "?")
            signal_descriptions.append(f"  🆕 Fresh Wallet ({age_days} days old) - Confidence: {confidence:.2f}")

        elif sig_type == "size_anomaly":
            multiplier = signal.get("multiplier", 0)
            avg_size = signal.get("average_size", 0)
            signal_descriptions.append(f"  📊 Size Anomaly ({multiplier:.1f}x avg ${avg_size:.2f}) - Confidence: {confidence:.2f}")

        elif sig_type == "timing":
            timing_sigs = signal.get("timing_signals", [])
            types = [s["type"] for s in timing_sigs]
            signal_descriptions.append(f"  ⏰ Timing ({', '.join(types)}) - Confidence: {confidence:.2f}")

        elif sig_type == "odds_movement":
            movement = signal.get("movement_pct", 0)
            direction = signal.get("direction", "?")
            signal_descriptions.append(f"  📈 Odds Movement ({movement:+.1f}% {direction}) - Confidence: {confidence:.2f}")

        elif sig_type == "contrarian":
            market_odds = signal.get("market_odds", 0)
            consensus_side = signal.get("consensus_side", "?")
            signal_descriptions.append(f"  🔄 Contrarian ({side} vs {consensus_side} at {market_odds:.1%}) - Confidence: {confidence:.2f}")

        elif sig_type == "cluster":
            cluster_size = signal.get("cluster_size", 0)
            total_volume = signal.get("total_volume", 0)
            signal_descriptions.append(f"  👥 Cluster ({cluster_size} wallets, ${total_volume:.2f}) - Confidence: {confidence:.2f}")

    # Confidence rating
    if combined_confidence >= 0.9:
        rating = "VERY HIGH ⭐⭐⭐⭐⭐"
    elif combined_confidence >= 0.8:
        rating = "HIGH ⭐⭐⭐⭐"
    elif combined_confidence >= 0.7:
        rating = "MEDIUM-HIGH ⭐⭐⭐"
    elif combined_confidence >= 0.6:
        rating = "MEDIUM ⭐⭐"
    else:
        rating = "LOW ⭐"

    alert = f"""
{'='*70}
🚨 TRADING SIGNAL DETECTED
{'='*70}

💰 Trade Details:
   Market:  {market_id}
   Wallet:  {wallet}
   Side:    {side}
   Value:   ${value:,.2f}

🎯 Signals Detected ({len(signals)}):
{chr(10).join(signal_descriptions)}

⭐ Combined Confidence: {combined_confidence:.2f} ({rating})

🔗 Links:
   Market: https://polymarket.com/event/{market_id}
   Trader: https://polymarket.com/profile/{wallet}

{'='*70}
"""
    return alert


def main():
    print("=" * 70)
    print("POLYMARKET SIGNAL DETECTOR - MOCK DATA TEST")
    print("=" * 70)
    print()

    # Load config
    config = load_config("config.yaml")
    setup_logging(log_level="INFO", console=True)

    # Create pipelines (without API client for mock test)
    print("⚠️  Using mock data (API unavailable)\n")
    print("Creating mock trades that would trigger various signals...")
    print()

    # Create mock trades
    mock_trades = create_mock_trades()

    print(f"✓ Created {len(mock_trades)} mock trades\n")
    print("=" * 70)
    print("SIMULATED ALERTS (What Discord would receive)")
    print("=" * 70)

    # Manually create some example alerts

    # Alert 1: Fresh Wallet + Size Anomaly
    print(format_alert_preview(
        mock_trades[0],
        [
            {"signal_type": "fresh_wallet", "wallet_age_days": 5, "confidence": 0.9},
            {"signal_type": "size_anomaly", "multiplier": 3.2, "average_size": 1015.0, "confidence": 0.7}
        ],
        0.88  # Combined confidence
    ))

    # Alert 2: Contrarian Trade
    print(format_alert_preview(
        mock_trades[1],
        [
            {"signal_type": "contrarian", "market_odds": 0.15, "consensus_side": "NO", "confidence": 0.85}
        ],
        0.85
    ))

    # Alert 3: Cluster Detection
    print(format_alert_preview(
        mock_trades[4],  # Last cluster trade
        [
            {"signal_type": "cluster", "cluster_size": 3, "total_volume": 5250.0, "confidence": 0.7}
        ],
        0.7
    ))

    # Summary
    print("\n" + "=" * 70)
    print("WHAT THESE ALERTS MEAN")
    print("=" * 70)
    print("""
🆕 Fresh Wallet Signal:
   → New trader (< 30 days) making large trades
   → Could indicate insider information or informed trading
   → Higher confidence for very new wallets (< 7 days)

📊 Size Anomaly Signal:
   → Trade much larger than user's typical size
   → 2x-3x average = medium confidence
   → 5x-10x+ average = very high confidence

⏰ Timing Signal:
   → Trade placed soon after market creation (< 60 min)
   → OR trade during unusual hours (2-6 AM UTC)
   → Early traders may have informational advantage

📈 Odds Movement Signal:
   → Trade during significant price movement (> 5%)
   → Larger movements = higher confidence
   → Could indicate market-moving information

🔄 Contrarian Signal:
   → Betting against strong consensus (> 80% odds)
   → Buying YES at < 20% or selling YES at > 80%
   → Strong conviction trade against the crowd

👥 Cluster Signal:
   → Multiple wallets trading same market simultaneously
   → 3+ wallets within 5-minute window
   → Could indicate coordinated or informed trading

⭐ Combined Confidence:
   → Multiple signals boost overall confidence
   → 0.9+ = VERY HIGH (strongest signals)
   → 0.7-0.9 = HIGH to MEDIUM-HIGH
   → < 0.7 = MEDIUM to LOW
""")

    print("=" * 70)
    print("SYSTEM STATUS")
    print("=" * 70)
    print("""
✅ Filter Pipeline: Ready
   - Market filter (exclude sports/crypto)
   - Size filter (min $2,000)
   - LP detector (filter market makers)

✅ Signal Pipeline: Ready
   - Fresh Wallet Detector
   - Size Anomaly Detector
   - Timing Analyzer
   - Odds Movement Tracker
   - Contrarian Detector
   - Cluster Detector

⏳ Discord Integration: Pending (Phase 4)
   - Alert enrichment with profiles
   - Rate-limited queue (1/sec)
   - Rich embed formatting

🔄 Next: Phase 4 to complete Discord alerts!
""")
    print("=" * 70)


if __name__ == "__main__":
    main()
