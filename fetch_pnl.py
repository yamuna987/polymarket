#!/usr/bin/env python3
"""
Polymarket P&L Fetcher
Fetches profit/loss data for a list of wallet addresses using the Polymarket Data API
"""

import requests
import csv
import time
from datetime import datetime, timedelta

# Polymarket API base URLs
BASE_URL = "https://data-api.polymarket.com"
GAMMA_API_URL = "https://gamma-api.polymarket.com"

# Your wallet list
WALLETS = [
    {"category": "Crypto", "username": "02a923d2f6edbc894e76357104e654b27a0d9071e", "wallet": "0x2a923d2f6edbc894e76357104e654b27a0d9071e"},
    {"category": "Sports", "username": "0x7fB7Ad0d194D7123e711e7db6C9D418fAc14E33d", "wallet": "0x7fb7ad0d194d7123e711e7db6c9d418fac14e33d"},
    {"category": "Crypto", "username": "0xa95bfdb", "wallet": "0xebf79787ab928c803cbef6fa8e0abe42b9e1da78"},
    {"category": "Tech", "username": "0xafEe", "wallet": "0xee50a31c3f5a7c77824b12a941a54388a2827ed6"},
    {"category": "Economics", "username": "0xe639e41094bbeae18g3e6d1790c17299183f082a", "wallet": "0xe639e41094bbeae18f3e6d1790c17299183f082a"},
    {"category": "Finance", "username": "50Whence", "wallet": "0x3cf3e8d5427aed066a7a5926980600f6c3cf87b3"},
    {"category": "Mentions, Culture, Tech", "username": "aenews2", "wallet": "0x44c1dfe43260c94ed4f1d00de2e1f80fb113ebc1"},
    {"category": "Politics, Crypto", "username": "alexmulti", "wallet": "0xd0c042c08f755ff940249f62745e82d356345565"},
    {"category": "Finance, Culture", "username": "Anjun", "wallet": "0x43372356634781eea88d61bbdd7824cdce958882"},
    {"category": "Mentions", "username": "Anon1792681", "wallet": "0x2139ff880571f8223a56544ca433756b8d014b34"},
    {"category": "Mentions", "username": "ANudeEgg", "wallet": "0x62d2bcd198bb6eab8b7eeb9d2061815dc02b9eb7"},
    {"category": "Finance, Mentions", "username": "Apsalar", "wallet": "0xd42f6a1634a3707e27cbae14ca966068e5d1047d"},
    {"category": "Finance, Economics", "username": "ArmageddonRewardsBilly", "wallet": "0xc8ab97a9089a9ff7e6ef0688e6e591a066946418"},
    {"category": "Mentions", "username": "Axios", "wallet": "0x03626d34381b0337387b0e8464c898f772009661"},
    {"category": "Mentions", "username": "bama124", "wallet": "0xe5c8026239919339b988fdb150a7ef4ea196d3e7"},
    {"category": "Politics", "username": "BetTom42", "wallet": "0x885783760858e1bd5dd09a3c3f916cfa251ac270"},
    {"category": "Economics", "username": "bobe2", "wallet": "0xed107a85a4585a381e48c7f7ca4144909e7dd2e5"},
    {"category": "Mentions", "username": "BuckMySalls", "wallet": "0x509587cbb541251c74f261df3421f1fcc9fdc97c"},
    {"category": "Mentions", "username": "Car", "wallet": "0x7c3db723f1d4d8cb9c550095203b686cb11e5c6b"},
    {"category": "Finance", "username": "chilling", "wallet": "0x5a181dcf3eb53a09fb32b20a5a9312fb8d26f689"},
    {"category": "Finance, Culture, Economics", "username": "cigarettes", "wallet": "0xd218e474776403a330142299f7796e8ba32eb5c9"},
    {"category": "Crypto", "username": "Circus", "wallet": "0x28065f1b88027422274fb33e1e22bf3dad5736e7"},
    {"category": "Crypto", "username": "coinman2", "wallet": "0x55be7aa03ecfbe37aa5460db791205f7ac9ddca3"},
    {"category": "Crypto", "username": "ComTruise", "wallet": "0xeee92f1cc6d6e0ad0b4ffda20b01cf3678e27ecb"},
    {"category": "Culture", "username": "debased", "wallet": "0x24c8cf69a0e0a17eee21f69d29752bfa32e823e1"},
    {"category": "Tech", "username": "Dropper", "wallet": "0x6bab41a0dc40d6dd4c1a915b8c01969479fd1292"},
    {"category": "Finance, Crypto", "username": "elPolloLoco", "wallet": "0xa2f1fecf1cc7db65a46588f764b6691533052d22"},
    {"category": "Mentions", "username": "Eridpnc", "wallet": "0xfcb034faade540c47ad37e582f6e0c762feac865"},
    {"category": "Tech", "username": "Euan", "wallet": "0xdd225a03cd7ed89e3931906c67c75ab31cf89ef1"},
    {"category": "Crypto", "username": "f705fa045201391d9632b7f3cde06a5e24453ca7", "wallet": "0xf705fa045201391d9632b7f3cde06a5e24453ca7"},
    {"category": "Sports", "username": "fengdubiying", "wallet": "0x17db3fcd93ba12d38382a0cade24b200185c5f6d"},
    {"category": "Politics", "username": "Fredi9999", "wallet": "0x1f2dd6d473f3e824cd2f8a89d9c69fb96f6ad0cf"},
    {"category": "Tech", "username": "Funfzig", "wallet": "0x5e9c76f30788f31f6c6867f5f44b1e95a7a7cd75"},
    {"category": "Sports", "username": "gmpm", "wallet": "0x14964aefa2cd7caff7878b3820a690a03c5aa429"},
    {"category": "Crypto", "username": "HaileyWelch", "wallet": "0x80cd8310aa624521e9e1b2b53b568cafb0ef0273"},
    {"category": "Sports", "username": "ilovecircle", "wallet": "0xa9878e59934ab507f9039bcb917c1bae0451141d"},
    {"category": "Culture,Economics", "username": "ImJustKen", "wallet": "0x9d84ce0306f8551e02efef1680475fc0f1dc1344"},
    {"category": "Culture", "username": "influenz.eth", "wallet": "0xe8dd7741ccb12350957ec71e9ee332e0d1e6ec86"},
    {"category": "Crypto", "username": "justdance", "wallet": "0xcc500cbcc8b7cf5bd21975ebbea34f21b5644c82"},
    {"category": "Crypto", "username": "kingofcoinflips", "wallet": "0xe9c6312464b52aa3eff13d822b003282075995c9"},
    {"category": "Politics", "username": "Len9311238", "wallet": "0x78b9ac44a6d7d7a076c14e0ad518b301b63c6b76"},
    {"category": "Mentions", "username": "MALDEMER", "wallet": "0xc6154a43bc53f7c267d295b29510a030c489221d"},
    {"category": "Politics", "username": "mikatrade77", "wallet": "0x23786fdad0073692157c6d7dc81f281843a35fcb"},
    {"category": "Tech", "username": "MotherTheresa", "wallet": "0x42a6ddf7cf7032972b0bfe32775e8109c5171b64"},
    {"category": "Finance", "username": "NotGambid", "wallet": "0xd205ced392d30c050e42b0fe0a08787b7583859a"},
    {"category": "Economics", "username": "pako", "wallet": "0x71edffd0d70a1da823ff07a3c6fc81457294d338"},
    {"category": "Finance", "username": "PolymaREKT", "wallet": "0xde242261bcd8d4320113f12230da34d705ca25a8"},
    {"category": "Sports", "username": "primm", "wallet": "0xd38b71f3e8ed1af71983e5c309eac3dfa9b35029"},
    {"category": "Politics", "username": "PrincessCaro", "wallet": "0x8119010a6e589062aa03583bb3f39ca632d9f887"},
    {"category": "Tech", "username": "ProfessionalPunter", "wallet": "0x22e4248bdb066f65c9f11cd66cdd3719a28eef1c"},
    {"category": "Politics", "username": "RepTrump", "wallet": "0x863134d00841b2e200492805a01e1e2f5defaa53"},
    {"category": "Sports", "username": "RN1", "wallet": "0x2005d16a84ceefa912d4e380cd32e7ff827875ea"},
    {"category": "Tech", "username": "ro0k", "wallet": "0x75049bd489194be19c45c31ed311e556411c9c69"},
    {"category": "Culture", "username": "SaylorMoon", "wallet": "0xecb14ac6e9ca447ce2f2912e6217b43d7b655da3"},
    {"category": "Economics", "username": "ScarletRot", "wallet": "0xf743f416caa37f672e8434a9132f681a8fa0ac84"},
    {"category": "Economics", "username": "scoobydoolover", "wallet": "0x08ce2678c929934de9edea698a998aea9dbc295e"},
    {"category": "Culture", "username": "scottilicious", "wallet": "0x000d257d2dc7616feaef4ae0f14600fdf50a758e"},
    {"category": "Economics", "username": "SemyonMarmeladov", "wallet": "0x37e4728b3c4607fb2b3b205386bb1d1fb1a8c991"},
    {"category": "Tech", "username": "send-tips-plz", "wallet": "0x17ce7c9a7f768bfa98946caf7d64c9e051f5beec"},
    {"category": "Sports", "username": "SeriouslySirius", "wallet": "0x16b29c50f2439faf627209b2ac0c7bbddaa8a881"},
    {"category": "Sports", "username": "simonbanza", "wallet": "0x5350afcd8bd8ceffdf4da32420d6d31be0822fda"},
    {"category": "Crypto", "username": "stonksgoup", "wallet": "0x4a38e6e0330c2463fb5ac2188a620634039abfe8"},
    {"category": "Sports", "username": "swisstony", "wallet": "0x204f72f35326db932158cba6adff0b9a1da95e14"},
    {"category": "Sports", "username": "tazcot", "wallet": "0x343d4466dc323b850e5249394894c7381d91456e"},
    {"category": "Politics", "username": "Theo4", "wallet": "0x56687bf447db6ffa42ffe2204a05edaa20f55839"},
    {"category": "Tech", "username": "tourists", "wallet": "0xc6dd722558dbfbd8fa780efcbe819ed8c6604b9f"},
    {"category": "Politics", "username": "walletmobile", "wallet": "0xe9ad918c7678cd38b12603a762e638a5d1ee7091"},
    {"category": "Culture", "username": "wokerjoesleeper", "wallet": "0x63d43bbb87f85af03b8f2f9e2fad7b54334fa2f1"},
    {"category": "Culture", "username": "WordleAddict", "wallet": "0xe25b9180f5687aa85bd94ee309bb72a464320f1b"},
    {"category": "Economics", "username": "YatSen", "wallet": "0x5bffcf561bcae83af680ad600cb99f1184d6ffbe"},
    {"category": "Tech", "username": "yyds233", "wallet": "0xc451017789fcf171e04a0e42d5e0bf083c2f2609"},
    {"category": "Politics", "username": "zxgngl", "wallet": "0xd235973291b2b75ff4070e9c0b01728c520b0f29"},
]


def get_positions_pnl(wallet_address):
    """Fetch current positions and calculate total P&L for a wallet"""
    url = f"{BASE_URL}/positions"
    params = {
        "user": wallet_address,
        "limit": 1000,
        "sortBy": "CASHPNL",
        "sortDirection": "DESC"
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        positions = response.json()

        total_cash_pnl = sum(p.get("cashPnl", 0) or 0 for p in positions)
        total_realized_pnl = sum(p.get("realizedPnl", 0) or 0 for p in positions)
        total_initial_value = sum(p.get("initialValue", 0) or 0 for p in positions)
        total_current_value = sum(p.get("currentValue", 0) or 0 for p in positions)
        num_positions = len(positions)

        return {
            "open_positions": num_positions,
            "total_cash_pnl": total_cash_pnl,
            "total_realized_pnl": total_realized_pnl,
            "total_initial_value": total_initial_value,
            "total_current_value": total_current_value,
        }
    except Exception as e:
        print(f"Error fetching positions for {wallet_address}: {e}")
        return None


def get_closed_positions_pnl(wallet_address):
    """Fetch closed positions P&L for a wallet"""
    url = f"{BASE_URL}/closed-positions"
    params = {
        "user": wallet_address,
        "limit": 1000,
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        positions = response.json()

        total_pnl = sum(p.get("pnl", 0) or 0 for p in positions)
        num_closed = len(positions)

        return {
            "closed_positions": num_closed,
            "closed_pnl": total_pnl,
        }
    except Exception as e:
        print(f"Error fetching closed positions for {wallet_address}: {e}")
        return None


def get_profile_info(wallet_address):
    """Get profile info from the gamma API including join date"""
    url = f"{GAMMA_API_URL}/public-profile"
    params = {"address": wallet_address}

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return {
                "created_at": data.get("createdAt"),
                "name": data.get("name"),
                "pseudonym": data.get("pseudonym"),
                "verified": data.get("verifiedBadge", False)
            }
    except Exception as e:
        print(f"Error fetching profile for {wallet_address}: {e}")
    return None


def get_total_markets_traded(wallet_address):
    """Get total number of markets a user has traded"""
    url = f"{BASE_URL}/traded"
    params = {"user": wallet_address}

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("traded", 0)
    except Exception as e:
        print(f"Error fetching traded markets for {wallet_address}: {e}")
        return 0


def calculate_pnl_for_period(wallet_address, start_timestamp, end_timestamp):
    """Calculate realized P&L for a specific time period using closed positions"""
    url = f"{BASE_URL}/closed-positions"
    params = {
        "user": wallet_address,
        "limit": 1000  # Get all closed positions
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        positions = response.json()

        total_pnl = 0
        for position in positions:
            timestamp = position.get("timestamp", 0)
            # Only count positions closed within the time period
            if start_timestamp <= timestamp <= end_timestamp:
                pnl = position.get("realizedPnl", 0) or 0
                total_pnl += pnl

        return total_pnl
    except Exception as e:
        print(f"Error calculating P&L for period: {e}")
        return 0


def get_time_period_pnl(wallet_address):
    """Get P&L for different time periods (1D, 1W, 1M, All time)"""
    now = int(time.time())
    one_day = 24 * 60 * 60
    one_week = 7 * one_day
    one_month = 30 * one_day

    return {
        "pnl_1d": calculate_pnl_for_period(wallet_address, now - one_day, now),
        "pnl_1w": calculate_pnl_for_period(wallet_address, now - one_week, now),
        "pnl_1m": calculate_pnl_for_period(wallet_address, now - one_month, now),
        "pnl_all": calculate_pnl_for_period(wallet_address, 0, now)
    }


def fetch_all_wallets():
    """Fetch P&L data for all wallets"""
    results = []

    for i, wallet_info in enumerate(WALLETS):
        wallet = wallet_info["wallet"]
        username = wallet_info["username"]
        category = wallet_info["category"]

        print(f"[{i+1}/{len(WALLETS)}] Fetching data for {username}...")

        # Get profile info (join date)
        profile_data = get_profile_info(wallet)

        # Get total markets traded
        total_traded = get_total_markets_traded(wallet)

        # Get open positions P&L
        positions_data = get_positions_pnl(wallet)

        # Get closed positions P&L
        closed_data = get_closed_positions_pnl(wallet)

        # Get time-period P&L
        print(f"  → Calculating time-period P&L...")
        period_pnl = get_time_period_pnl(wallet)

        result = {
            "category": category,
            "username": username,
            "wallet": wallet,
            "profile_url": f"https://polymarket.com/profile/{wallet}",
        }

        # Add profile info
        if profile_data:
            result.update({
                "joined_date": profile_data.get("created_at", "N/A"),
                "display_name": profile_data.get("name") or profile_data.get("pseudonym", "N/A"),
                "verified": profile_data.get("verified", False)
            })
        else:
            result.update({
                "joined_date": "N/A",
                "display_name": "N/A",
                "verified": False
            })

        # Add total predictions (markets traded)
        result["total_predictions"] = total_traded

        if positions_data:
            result.update({
                "open_positions": positions_data["open_positions"],
                "open_cash_pnl": round(positions_data["total_cash_pnl"], 2),
                "open_realized_pnl": round(positions_data["total_realized_pnl"], 2),
                "open_initial_value": round(positions_data["total_initial_value"], 2),
                "open_current_value": round(positions_data["total_current_value"], 2),
            })
        else:
            result.update({
                "open_positions": 0,
                "open_cash_pnl": 0,
                "open_realized_pnl": 0,
                "open_initial_value": 0,
                "open_current_value": 0,
            })

        if closed_data:
            result.update({
                "closed_positions": closed_data["closed_positions"],
                "closed_pnl": round(closed_data["closed_pnl"], 2),
            })
        else:
            result.update({
                "closed_positions": 0,
                "closed_pnl": 0,
            })

        # Calculate total P&L
        result["total_pnl"] = round(result["open_cash_pnl"] + result["closed_pnl"], 2)

        # Add time-period P&L
        result.update({
            "pnl_1d": round(period_pnl["pnl_1d"], 2),
            "pnl_1w": round(period_pnl["pnl_1w"], 2),
            "pnl_1m": round(period_pnl["pnl_1m"], 2),
            "pnl_all_time": round(period_pnl["pnl_all"], 2)
        })

        results.append(result)

        # Rate limiting - be nice to the API
        time.sleep(1)  # Increased to 1 second due to more API calls

    return results


def save_to_csv(results, filename):
    """Save results to CSV file"""
    if not results:
        print("No results to save")
        return

    fieldnames = [
        "category", "username", "display_name", "wallet", "profile_url",
        "joined_date", "verified", "total_predictions",
        "open_positions", "open_cash_pnl", "open_realized_pnl",
        "open_initial_value", "open_current_value",
        "closed_positions", "closed_pnl", "total_pnl",
        "pnl_1d", "pnl_1w", "pnl_1m", "pnl_all_time"
    ]

    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Results saved to {filename}")


def main():
    print("=" * 60)
    print("Polymarket P&L Fetcher")
    print("=" * 60)
    print(f"Fetching data for {len(WALLETS)} wallets...")
    print()

    results = fetch_all_wallets()

    # Sort by total P&L descending
    results.sort(key=lambda x: x["total_pnl"], reverse=True)

    # Save to CSV
    output_file = "polymarket_pnl_results.csv"
    save_to_csv(results, output_file)

    # Print summary
    print()
    print("=" * 60)
    print("TOP 10 BY TOTAL P&L")
    print("=" * 60)
    for i, r in enumerate(results[:10]):
        print(f"{i+1}. {r['username']}: ${r['total_pnl']:,.2f}")

    print()
    print("=" * 60)
    print("BOTTOM 10 BY TOTAL P&L")
    print("=" * 60)
    for i, r in enumerate(results[-10:]):
        print(f"{len(results)-9+i}. {r['username']}: ${r['total_pnl']:,.2f}")


if __name__ == "__main__":
    main()
