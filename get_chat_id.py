#!/usr/bin/env python3
"""
Helper script to get your Telegram Chat ID

Usage:
1. Start a conversation with your bot on Telegram
2. Send any message to the bot (e.g., "Hello")
3. Run this script: python get_chat_id.py
"""

import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

if not bot_token or bot_token == "your_bot_token_here":
    print("❌ Error: TELEGRAM_BOT_TOKEN not set in .env file")
    exit(1)

print("=" * 70)
print("TELEGRAM CHAT ID FINDER")
print("=" * 70)
print()
print("Fetching updates from Telegram...")
print()

# Get updates from Telegram
url = f"https://api.telegram.org/bot{bot_token}/getUpdates"

try:
    response = requests.get(url)
    data = response.json()

    if not data.get("ok"):
        print(f"❌ Error: {data.get('description', 'Unknown error')}")
        exit(1)

    updates = data.get("result", [])

    if not updates:
        print("❌ No messages found!")
        print()
        print("Please follow these steps:")
        print("1. Open Telegram and search for your bot")
        print("2. Start a conversation and send any message (e.g., 'Hello')")
        print("3. Run this script again")
        print()
        exit(0)

    # Find all unique chat IDs
    chat_ids = set()
    for update in updates:
        if "message" in update:
            chat_id = update["message"]["chat"]["id"]
            chat_type = update["message"]["chat"]["type"]
            chat_ids.add((chat_id, chat_type))

    if not chat_ids:
        print("❌ No chat IDs found in updates")
        exit(1)

    print("✅ Found the following chats:")
    print()

    for chat_id, chat_type in chat_ids:
        print(f"   Chat ID: {chat_id}")
        print(f"   Type: {chat_type}")
        print()

    if len(chat_ids) == 1:
        chat_id, chat_type = list(chat_ids)[0]
        print("=" * 70)
        print("SETUP INSTRUCTIONS")
        print("=" * 70)
        print()
        print(f"Your Chat ID is: {chat_id}")
        print()
        print("To complete setup:")
        print(f"1. Edit .env file")
        print(f"2. Replace 'PLACEHOLDER_GET_YOUR_CHAT_ID' with: {chat_id}")
        print()
        print("Or run this command:")
        print(f"   sed -i 's/TELEGRAM_CHAT_ID=.*/TELEGRAM_CHAT_ID={chat_id}/' .env")
        print()
    else:
        print("=" * 70)
        print("Multiple chats found. Choose the one where you want alerts:")
        print()
        for i, (chat_id, chat_type) in enumerate(chat_ids, 1):
            print(f"{i}. Chat ID {chat_id} ({chat_type})")
        print()
        print("Edit .env and set TELEGRAM_CHAT_ID to your chosen chat ID")
        print()

except requests.exceptions.RequestException as e:
    print(f"❌ Network error: {e}")
    exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
