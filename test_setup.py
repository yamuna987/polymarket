#!/usr/bin/env python3
"""
Test Setup Script
Quick test to verify the setup is working
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import load_config, get_database_url
from src.utils.logger import setup_logging
from src.database.models import DatabaseManager
from src.api.polymarket_client import PolymarketAPIClient
from src.api.cache import APICache


def test_configuration():
    """Test configuration loading"""
    print("Testing configuration loading...")
    try:
        config = load_config("config.yaml")
        print("✓ Configuration loaded successfully")
        print(f"  - API URLs configured: {len(config.get('api', {}))} endpoints")
        print(f"  - Database type: {config['database']['type']}")
        return config
    except Exception as e:
        print(f"✗ Configuration loading failed: {e}")
        return None


def test_logging(config):
    """Test logging setup"""
    print("\nTesting logging setup...")
    try:
        log_config = config.get("logging", {})
        logger = setup_logging(
            log_level="INFO",
            console=True
        )
        logger.info("Test log message")
        print("✓ Logging configured successfully")
        return True
    except Exception as e:
        print(f"✗ Logging setup failed: {e}")
        return False


def test_database(config):
    """Test database connection"""
    print("\nTesting database setup...")
    try:
        db_url = get_database_url(config)
        print(f"  - Database URL: {db_url}")

        db_manager = DatabaseManager(db_url)
        db_manager.create_tables()

        print("✓ Database initialized successfully")
        print(f"  - Tables created")
        return True
    except Exception as e:
        print(f"✗ Database setup failed: {e}")
        return False


def test_api_client(config):
    """Test API client"""
    print("\nTesting API client...")
    try:
        api_config = config.get("api", {})
        client = PolymarketAPIClient(api_config)

        # Test a simple API call
        print("  - Testing API connectivity...")
        # Get recent trades (this is a read-only endpoint)
        trades = client.get_trades(limit=1)

        if trades is not None:
            print(f"✓ API client working - fetched {len(trades)} trades")
        else:
            print("⚠ API client initialized but could not fetch data")

        client.close()
        return True
    except Exception as e:
        print(f"✗ API client test failed: {e}")
        return False


def test_cache():
    """Test caching system"""
    print("\nTesting cache system...")
    try:
        cache = APICache(profile_ttl=60, market_ttl=60)

        # Test profile cache
        cache.set_profile("test_wallet", {"name": "Test User"})
        result = cache.get_profile("test_wallet")

        if result and result.get("name") == "Test User":
            print("✓ Cache system working")
            stats = cache.get_stats()
            print(f"  - Hit rate: {stats['hit_rate_pct']:.1f}%")
            return True
        else:
            print("✗ Cache not working properly")
            return False
    except Exception as e:
        print(f"✗ Cache test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("POLYMARKET SIGNAL DETECTOR - SETUP TEST")
    print("=" * 60)

    results = []

    # Test configuration
    config = test_configuration()
    results.append(config is not None)

    if not config:
        print("\n✗ Cannot continue without valid configuration")
        return

    # Test logging
    results.append(test_logging(config))

    # Test database
    results.append(test_database(config))

    # Test API client
    results.append(test_api_client(config))

    # Test cache
    results.append(test_cache())

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n✓ ALL TESTS PASSED - System is ready!")
        print("\nNext steps:")
        print("1. Set your Discord webhook URL in .env file")
        print("2. Run: python main.py")
    else:
        print("\n✗ Some tests failed - please fix the issues above")

    print("=" * 60)


if __name__ == "__main__":
    main()
