#!/usr/bin/env python3
"""
Test Complete System
Test filters + signals with real data and show alert previews
"""

import sys
from pathlib import Path
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import load_config
from src.utils.logger import setup_logging
from src.api.polymarket_client import PolymarketAPIClient
from src.filters.pipeline import create_filter_pipeline
from src.signals.pipeline import create_signal_pipeline


def format_alert_preview(trade, signals, combined_confidence):
    """Format an alert preview for Discord"""

    # Extract trade info
    wallet = (trade.get("trader_wallet") or "unknown")[:10] + "..."
    market_id = (trade.get("market_id") or "unknown")[:10] + "..."
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
            signal_descriptions.append(f"  📊 Size Anomaly ({multiplier:.1f}x average ${avg_size:.2f}) - Confidence: {confidence:.2f}")

        elif sig_type == "timing":
            timing_sigs = signal.get("timing_signals", [])
            types = [s["type"] for s in timing_sigs]
            signal_descriptions.append(f"  ⏰ Timing Signal ({', '.join(types)}) - Confidence: {confidence:.2f}")

        elif sig_type == "odds_movement":
            movement = signal.get("movement_pct", 0)
            direction = signal.get("direction", "?")
            signal_descriptions.append(f"  📈 Odds Movement ({movement:+.1f}% {direction}) - Confidence: {confidence:.2f}")

        elif sig_type == "contrarian":
            market_odds = signal.get("market_odds", 0)
            consensus_side = signal.get("consensus_side", "?")
            signal_descriptions.append(f"  🔄 Contrarian ({side} vs {consensus_side} consensus at {market_odds:.1%}) - Confidence: {confidence:.2f}")

        elif sig_type == "cluster":
            cluster_size = signal.get("cluster_size", 0)
            total_volume = signal.get("total_volume", 0)
            signal_descriptions.append(f"  👥 Cluster ({cluster_size} wallets, ${total_volume:.2f} volume) - Confidence: {confidence:.2f}")

    # Format the alert
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

⭐ Combined Confidence: {combined_confidence:.2f} ({_confidence_to_rating(combined_confidence)})

🔗 Links:
   Market: https://polymarket.com/event/{market_id}
   Trader: https://polymarket.com/profile/{wallet}

{'='*70}
"""
    return alert


def _confidence_to_rating(confidence):
    """Convert confidence score to rating"""
    if confidence >= 0.9:
        return "VERY HIGH ⭐⭐⭐⭐⭐"
    elif confidence >= 0.8:
        return "HIGH ⭐⭐⭐⭐"
    elif confidence >= 0.7:
        return "MEDIUM-HIGH ⭐⭐⭐"
    elif confidence >= 0.6:
        return "MEDIUM ⭐⭐"
    else:
        return "LOW ⭐"


def test_complete_system():
    """Test complete system with filters and signals"""
    print("=" * 70)
    print("POLYMARKET SIGNAL DETECTOR - COMPLETE SYSTEM TEST")
    print("=" * 70)
    print()

    # Load config and setup logging
    config = load_config("config.yaml")
    setup_logging(log_level="INFO", console=True)

    # Create API client
    api_config = config.get("api", {})
    api_client = PolymarketAPIClient(api_config)

    # Create filter pipeline
    filter_pipeline = create_filter_pipeline(config, api_client)

    # Create signal pipeline
    signal_pipeline = create_signal_pipeline(config, api_client)

    print("✓ Pipelines initialized\n")
    print("Fetching recent trades from Polymarket...")

    # Fetch trades
    trades = api_client.get_trades(limit=100, taker_only=True)

    if not trades:
        print("✗ No trades fetched")
        return

    print(f"✓ Fetched {len(trades)} trades\n")
    print("=" * 70)
    print("PROCESSING TRADES THROUGH COMPLETE PIPELINE")
    print("=" * 70)
    print()

    alerts_generated = 0

    # Process each trade
    for i, trade in enumerate(trades):
        # Convert to internal format
        trade_data = {
            "asset_id": trade.get("asset"),
            "market_id": trade.get("conditionId"),
            "condition_id": trade.get("conditionId"),
            "trader_wallet": trade.get("proxyWallet"),
            "side": trade.get("side"),
            "size": float(trade.get("size", 0)),
            "price": float(trade.get("price", 0)),
            "value_usd": float(trade.get("size", 0)) * float(trade.get("price", 0)),
            "timestamp": trade.get("timestamp"),
            "datetime": datetime.fromtimestamp(trade.get("timestamp", 0) / 1000) if trade.get("timestamp") else datetime.now(),
            "transaction_hash": trade.get("transactionHash")
        }

        # Phase 2: Apply filters
        should_process, filter_reason, enriched_trade = filter_pipeline.process_trade(trade_data)

        if not should_process:
            continue

        # Phase 3: Detect signals
        signals = signal_pipeline.process_trade(enriched_trade)

        if signals:
            # Calculate combined confidence
            combined_confidence = signal_pipeline.get_combined_confidence(signals)

            # Generate alert preview
            alert = format_alert_preview(enriched_trade, signals, combined_confidence)
            print(alert)

            alerts_generated += 1

            # Limit output
            if alerts_generated >= 5:
                print("\n(Showing first 5 alerts only...)\n")
                break

    # Print summary statistics
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    filter_stats = filter_pipeline.get_stats()
    signal_stats = signal_pipeline.get_stats()

    print(f"\n📊 Filter Statistics:")
    print(f"   Total Trades:        {filter_stats['total_trades_processed']}")
    print(f"   Passed Filters:      {filter_stats['passed_all_filters']}")
    print(f"   Pass Rate:           {filter_stats['pass_rate_pct']:.1f}%")
    print(f"   Filtered by Market:  {filter_stats['filtered_by_market']}")
    print(f"   Filtered by Size:    {filter_stats['filtered_by_size']}")
    print(f"   Filtered by LP:      {filter_stats['filtered_by_lp']}")

    print(f"\n🎯 Signal Statistics:")
    print(f"   Trades Analyzed:     {signal_stats['total_trades_analyzed']}")
    print(f"   Signals Detected:    {signal_stats['total_signals_detected']}")
    print(f"   Multi-Signal Trades: {signal_stats['multi_signal_trades']}")

    if signal_stats['signals_by_type']:
        print(f"\n   Signals by Type:")
        for sig_type, count in signal_stats['signals_by_type'].items():
            if count > 0:
                print(f"      {sig_type}: {count}")

    print(f"\n🚨 Alerts Generated:    {alerts_generated}")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

    # Cleanup
    api_client.close()


if __name__ == "__main__":
    test_complete_system()
