#!/usr/bin/env python3
"""
Quick Twilio WhatsApp sandbox test.

Usage:
    source venv/bin/activate
    python3 scripts/test_twilio.py --to "+919876543210" --message "AstraGuard test 🚀"

Before running:
1. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env
2. Join the Twilio sandbox: send "join <word>" to +14155238886 on WhatsApp
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from integrations.twilio_whatsapp import send_whatsapp_message


async def main():
    parser = argparse.ArgumentParser(description="Test Twilio WhatsApp")
    parser.add_argument("--to", required=True, help="Recipient phone (e.g., +919876543210)")
    parser.add_argument("--message", default="🚀 AstraGuard test message! If you see this, WhatsApp integration works.", help="Message to send")
    args = parser.parse_args()

    # Check env
    if not os.getenv("TWILIO_ACCOUNT_SID"):
        print("❌ TWILIO_ACCOUNT_SID not set in .env")
        sys.exit(1)
    if not os.getenv("TWILIO_AUTH_TOKEN"):
        print("❌ TWILIO_AUTH_TOKEN not set in .env")
        sys.exit(1)

    print(f"📱 Sending WhatsApp to {args.to}...")
    print(f"💬 Message: {args.message}")

    result = await send_whatsapp_message(args.to, args.message)

    if result["success"]:
        print(f"✅ Message sent! SID: {result['sid']}")
    else:
        print(f"❌ Failed: {result['error']}")
        print("\n🔧 Troubleshooting:")
        print("1. Did the recipient join the Twilio sandbox?")
        print("   → Send 'join <word>' to +14155238886 on WhatsApp")
        print("2. Are TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN correct?")
        print("3. Is the phone number in international format (+91...)?")


if __name__ == "__main__":
    asyncio.run(main())
