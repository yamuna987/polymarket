#!/usr/bin/env python3
"""
Test Filter Pipeline
Test filters with real API data
"""

import sys
from pathlib import Path
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import load_config
from src.utils.logger import setup_logging
from src.api.polymarket_client import PolymarketAPIClient
from src.filters.pipeline import create_filter_pipeline


def test_filters():
    """Test filter pipeline with real trades"""
    print("=" * 60)
    print("FILTER PIPELINE TEST")
    print("=" * 60)

    # Load config and setup logging
    config = load_config("config.yaml")
    setup_logging(log_level="INFO", console=True)

    # Create API client
    api_config = config.get("api", {})
    api_client = PolymarketAPIClient(api_config)

    # Create filter pipeline
    filter_pipeline = create_filter_pipeline(config, api_client)

    print("\nFetching recent trades from Polymarket...")

    # Fetch recent trades
    trades = api_client.get_trades(limit=50, taker_only=True)

    if not trades:
        print("✗ No trades fetched")
        return

    print(f"✓ Fetched {len(trades)} trades\n")

    print("Testing filter pipeline:")
    print("-" * 60)

    # Process each trade through the filter pipeline
    for i, trade in enumerate(trades):
        # Convert API trade format to our internal format
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
            "transaction_hash": trade.get("transactionHash")
        }

        # Process through filters
        should_process, filter_reason, enriched_trade = filter_pipeline.process_trade(trade_data)

        status = "✓ PASS" if should_process else "✗ FILTERED"
        print(f"{i+1:2d}. {status} - ${trade_data['value_usd']:8.2f} - {trade_data['side']:4s} - {filter_reason or 'Passed all filters'}")

    # Print statistics
    print("\n" + "=" * 60)
    print("FILTER STATISTICS")
    print("=" * 60)

    stats = filter_pipeline.get_stats()

    print(f"Total Trades:        {stats['total_trades_processed']}")
    print(f"Passed Filters:      {stats['passed_all_filters']}")
    print(f"Filtered Out:        {stats['total_trades_processed'] - stats['passed_all_filters']}")
    print(f"Pass Rate:           {stats['pass_rate_pct']:.1f}%")
    print()
    print(f"Filtered by Market:  {stats['filtered_by_market']}")
    print(f"Filtered by Size:    {stats['filtered_by_size']}")
    print(f"Filtered by LP:      {stats['filtered_by_lp']}")

    # Top filter reasons
    if stats['top_filter_reasons']:
        print("\nTop Filter Reasons:")
        for reason_data in stats['top_filter_reasons']:
            print(f"  - {reason_data['reason']}: {reason_data['count']}")

    # Filter configuration
    print("\n" + "=" * 60)
    print("FILTER CONFIGURATION")
    print("=" * 60)

    if 'market_filter' in stats:
        print(f"Market Filter:")
        print(f"  - Excluded Categories: {stats['market_filter']['excluded_categories']}")
        print(f"  - Timeframe Days: {stats['market_filter']['market_timeframe_days']}")

    if 'size_filter' in stats:
        print(f"\nSize Filter:")
        print(f"  - Minimum Trade Size: ${stats['size_filter']['min_trade_size_usd']}")

    if 'lp_detector' in stats:
        print(f"\nLP Detector:")
        print(f"  - Balance Threshold: {stats['lp_detector']['balance_threshold']}")
        print(f"  - Cached Wallets: {stats['lp_detector']['cached_wallets']}")
        print(f"  - Cached LPs: {stats['lp_detector']['cached_lps']}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

    # Cleanup
    api_client.close()


if __name__ == "__main__":
    test_filters()
