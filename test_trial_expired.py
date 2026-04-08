#!/usr/bin/env python3
"""
Test script for trial expiration notification.
Usage: python test_trial_expired.py <chat_id>
"""
import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from subscription import (
    load_subscriptions,
    save_subscriptions,
    is_trial_expired_and_not_notified,
    mark_trial_expired_notified,
    PLANS,
    FREE_TRIAL_DAYS
)


def simulate_expired_trial(chat_id: int):
    """Simulate an expired trial for testing."""
    data = load_subscriptions()
    chat_str = str(chat_id)
    
    # Create or update user with expired trial
    now = datetime.now()
    expired_at = now - timedelta(days=1)  # Expired 1 day ago
    
    if chat_str not in data["users"]:
        data["users"][chat_str] = {}
    
    data["users"][chat_str]["free_trial_used"] = True
    data["users"][chat_str]["trial_expired_notified"] = False  # Reset notification flag
    data["users"][chat_str]["subscription"] = {
        "active": False,
        "plan_id": "free_trial",
        "plan_name": "Dung Thu Mien Phi",
        "price": 0,
        "starts_at": (now - timedelta(days=FREE_TRIAL_DAYS + 1)).strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": expired_at.strftime("%Y-%m-%d %H:%M:%S"),
        "days": FREE_TRIAL_DAYS,
        "is_free_trial": True
    }
    
    save_subscriptions(data)
    print(f"[*] Created expired trial for chat_id={chat_id}")
    print(f"[*] Trial expired at: {expired_at.strftime('%Y-%m-%d %H:%M:%S')}")
    return data


def test_notification(chat_id: int):
    """Test the notification logic."""
    print(f"\n{'='*50}")
    print(f"TESTING TRIAL EXPIRATION NOTIFICATION")
    print(f"{'='*50}\n")
    
    # Step 1: Check current status
    print("[1] Checking current subscription status...")
    data = load_subscriptions()
    chat_str = str(chat_id)
    
    if chat_str in data["users"]:
        user = data["users"][chat_str]
        sub = user.get("subscription", {})
        print(f"    - Has subscription: {bool(sub)}")
        print(f"    - Is free trial: {sub.get('is_free_trial', False)}")
        print(f"    - Expires at: {sub.get('expires_at', 'N/A')}")
        print(f"    - Notified: {user.get('trial_expired_notified', False)}")
    else:
        print(f"    - User not found in subscriptions")
    
    # Step 2: Check if trial expired
    print("\n[2] Checking if trial expired and not notified...")
    is_expired = is_trial_expired_and_not_notified(chat_id)
    print(f"    - Is expired and not notified: {is_expired}")
    
    # Step 3: Show notification message
    if is_expired:
        print("\n[3] Notification message that would be sent:")
        print("-" * 40)
        msg = "*DUNG THU DA HET HAN!*\n\n"
        msg += "Ban vui long chon goi va thanh toan de tiep tuc su dung bot.\n\n"
        msg += "*CAC GOI HIEN CO:*\n"
        for plan_id, plan in PLANS.items():
            msg += f"- `{plan_id}`: {plan['name']} - *{plan['price']:,.0f}* VND ({plan['duration_days']} ngay)\n"
        msg += "\nDung: `/subscribe <plan_id>` de tao yeu cau thanh toan.\n"
        msg += "Hoac dung: `/qr <plan_id>` de nhan QR thanh toan nhanh."
        print(msg)
        print("-" * 40)
        
        # Step 4: Mark as notified
        print("\n[4] Marking as notified...")
        mark_trial_expired_notified(chat_id)
        print("    - Done! User won't receive this notification again.")
    else:
        print("\n[3] No notification needed.")
        if not data["users"].get(chat_str, {}).get("subscription", {}).get("is_free_trial"):
            print("    - Reason: User doesn't have a free trial")
        elif data["users"].get(chat_str, {}).get("trial_expired_notified"):
            print("    - Reason: User already notified")
        else:
            print("    - Reason: Trial not expired yet")
    
    print(f"\n{'='*50}")
    print("TEST COMPLETE")
    print(f"{'='*50}\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_trial_expired.py <chat_id> [--create]")
        print("\nOptions:")
        print("  --create    Create a simulated expired trial for testing")
        print("\nExample:")
        print("  python test_trial_expired.py 5529264160 --create")
        print("  python test_trial_expired.py 5529264160")
        return
    
    try:
        chat_id = int(sys.argv[1])
    except ValueError:
        print(f"Error: Invalid chat_id '{sys.argv[1]}'")
        return
    
    # Check if --create flag
    if len(sys.argv) > 2 and sys.argv[2] == "--create":
        simulate_expired_trial(chat_id)
    
    test_notification(chat_id)


if __name__ == "__main__":
    main()
