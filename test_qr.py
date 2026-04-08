#!/usr/bin/env python3
"""
Test script for VietQR generation.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from subscription import build_vietqr_image_url, PLANS


def test_qr():
    print("\n" + "="*60)
    print("TESTING VIETQR GENERATION")
    print("="*60 + "\n")
    
    # Check env config
    print("[1] Checking environment configuration...")
    bank_bin = os.environ.get("BANK_BIN", "")
    bank_account = os.environ.get("BANK_ACCOUNT", "")
    bank_owner = os.environ.get("BANK_OWNER", "")
    bank_name = os.environ.get("BANK_NAME", "")
    
    print(f"    - BANK_NAME: {bank_name}")
    print(f"    - BANK_BIN: {bank_bin}")
    print(f"    - BANK_ACCOUNT: {bank_account}")
    print(f"    - BANK_OWNER: {bank_owner}")
    
    if not bank_bin or not bank_account:
        print("\n    [!] WARNING: BANK_BIN or BANK_ACCOUNT not configured!")
        print("    Please set these in .env file")
        return
    
    # Test QR for each plan
    print("\n[2] Testing QR URLs for each plan...")
    print("-" * 60)
    
    test_chat_id = 5529264160
    
    for plan_id, plan in PLANS.items():
        add_info = f"AQ_{test_chat_id}_{plan_id}"
        qr_url = build_vietqr_image_url(plan["price"], add_info)
        
        print(f"\nPlan: {plan['name']} ({plan_id})")
        print(f"  Price: {plan['price']:,} VND")
        print(f"  Add Info: {add_info}")
        print(f"  QR URL: {qr_url}")
        
        if qr_url:
            print(f"  [OK] QR URL generated successfully")
        else:
            print(f"  [ERROR] Failed to generate QR URL")
    
    print("\n" + "-" * 60)
    print("\n[3] Sample QR URLs (copy to browser to view):")
    print("-" * 60)
    
    # Show monthly plan QR
    monthly_qr = build_vietqr_image_url(PLANS["monthly"]["price"], f"AQ_{test_chat_id}_monthly")
    print(f"\nMonthly plan QR:")
    print(f"  {monthly_qr}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_qr()
