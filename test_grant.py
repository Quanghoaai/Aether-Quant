#!/usr/bin/env python3
"""Quick test to grant subscription for user."""
import sys
sys.path.insert(0, '.')

from subscription import grant_subscription, has_active_subscription

chat_id = 5529264160
plan_id = "monthly"
days = 30

print(f"Granting {plan_id} subscription for {days} days to chat_id={chat_id}...")
result = grant_subscription(chat_id, plan_id, days)

if result["success"]:
    print(f"\n SUCCESS!")
    print(f"  Plan: {result['data']['plan']}")
    print(f"  Days: {result['data']['days']}")
    print(f"  Expires: {result['data']['expires_at']}")
    print(f"\n  has_active_subscription({chat_id}): {has_active_subscription(chat_id)}")
else:
    print(f"\n FAILED: {result['message']}")
