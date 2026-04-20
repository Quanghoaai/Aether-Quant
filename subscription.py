"""
Subscription & Coupon Management for Aether Quant Telegram Bot
"""
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

SUBSCRIPTIONS_FILE = "subscriptions.json"
PAYMENTS_FILE = "payments.json"
FREE_TRIAL_DAYS = 7  # Free trial for new users


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def build_vietqr_image_url(amount: int, add_info: str) -> str:
    """Build VietQR image URL (no API key).

    Requires env:
    - BANK_BIN (e.g. 970423 for TPBank, 970415 for VietinBank, etc.)
    - BANK_ACCOUNT
    - BANK_OWNER
    """
    bank_bin = os.environ.get("BANK_BIN", "")
    bank_account = os.environ.get("BANK_ACCOUNT", "")
    bank_owner = os.environ.get("BANK_OWNER", "")
    if not bank_bin or not bank_account:
        return ""
    # compact2 has nicer layout for Telegram
    # VietQR endpoint supports: amount, addInfo, accountName
    from urllib.parse import quote

    qs_amount = str(int(amount))
    qs_add_info = quote(add_info)
    qs_owner = quote(bank_owner) if bank_owner else ""
    return (
        f"https://img.vietqr.io/image/{bank_bin}-{bank_account}-compact2.png"
        f"?amount={qs_amount}&addInfo={qs_add_info}&accountName={qs_owner}"
    )

# Subscription Plans
PLANS = {
    "daily": {
        "id": "daily",
        "name": "Goi Ngay",
        "price": 10000,  # VND
        "duration_days": 1,
        "features": ["Phan tich hang ngay", "Tin realtime"]
    },
    "weekly": {
        "id": "weekly",
        "name": "Goi Tuan",
        "price": 50000,  # VND
        "duration_days": 7,
        "features": ["Phan tich hang ngay", "Tin realtime", "Bao cao tuan"]
    },
    "monthly": {
        "id": "monthly",
        "name": "Goi Thang",
        "price": 150000,  # VND
        "duration_days": 30,
        "features": ["Phan tich hang ngay", "Tin realtime", "Bao cao tuan", "Hotline support"]
    },
    "quarterly": {
        "id": "quarterly",
        "name": "Goi Quy",
        "price": 400000,  # VND
        "duration_days": 90,
        "features": ["Tat ca tinh nang Monthly", "Priority support", "Custom watchlist"]
    },
    "yearly": {
        "id": "yearly",
        "name": "Goi Nam",
        "price": 1200000,  # VND
        "duration_days": 365,
        "features": ["Tat ca tinh nang", "VIP support", "Alpha signals", "Unlimited watchlist"]
    }
}

# Default Coupons (fallback when env not set)
DEFAULT_COUPONS = {
    "NEWUSER": {"code": "NEWUSER", "discount": 20000, "active": True, "max_uses": 100, "current_uses": 0},
    "LAUNCH": {"code": "LAUNCH", "discount": 20000, "active": True, "max_uses": 50, "current_uses": 0},
    "DOUUSER": {"code": "DOUUSER", "discount": 50000, "active": True, "max_uses": 10, "current_uses": 0},
    "SUMMER": {"code": "SUMMER", "discount": 15000, "active": True, "expires_at": "2025-08-31", "max_uses": 200, "current_uses": 0},
    "FLASH": {"code": "FLASH", "discount": 10000, "active": True, "expires_at": "2025-04-30", "max_uses": 500, "current_uses": 0},
    "VIP50": {"code": "VIP50", "discount": 50000, "active": True, "max_uses": 20, "current_uses": 0},
}


def load_subscriptions() -> Dict[str, Any]:
    """Load subscriptions data from file."""
    if os.path.exists(SUBSCRIPTIONS_FILE):
        with open(SUBSCRIPTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Ensure users key exists
        if "users" not in data:
            data["users"] = {}
        if "coupons" not in data:
            data["coupons"] = DEFAULT_COUPONS.copy()
        if "transactions" not in data:
            data["transactions"] = []
        return data
    return {
        "users": {},  # chat_id -> user data
        "coupons": DEFAULT_COUPONS.copy(),
        "transactions": []
    }


def load_payments() -> Dict[str, Any]:
    """Load pending payments data."""
    if os.path.exists(PAYMENTS_FILE):
        with open(PAYMENTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "pending" not in data:
            data["pending"] = {}
        if "approved" not in data:
            data["approved"] = []
        return data
    return {"pending": {}, "approved": []}


def save_payments(data: Dict[str, Any]) -> None:
    """Save payments data to file."""
    with open(PAYMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_subscriptions(data: Dict[str, Any]) -> None:
    """Save subscriptions data to file."""
    with open(SUBSCRIPTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_coupons() -> Dict[str, Any]:
    """Get coupons from env or defaults."""
    coupons_env = os.environ.get("COUPONS", "")
    if coupons_env:
        coupons = {}
        for item in coupons_env.split(","):
            parts = item.strip().split(":")
            if len(parts) >= 2:
                code = parts[0].upper()
                discount = int(parts[1])
                expires_at = parts[2] if len(parts) > 2 else None
                max_uses = int(parts[3]) if len(parts) > 3 else None
                coupons[code] = {
                    "code": code,
                    "discount": discount,
                    "active": True,
                    "expires_at": expires_at,
                    "max_uses": max_uses,
                    "current_uses": 0
                }
        return coupons if coupons else DEFAULT_COUPONS
    return DEFAULT_COUPONS


def verify_coupon(code: str) -> Dict[str, Any]:
    """
    Verify a coupon code.
    Returns: {"success": bool, "data": {...} or "error": str}
    """
    code = code.upper().strip()
    data = load_subscriptions()
    coupons = data.get("coupons", get_coupons())
    
    if code not in coupons:
        return {"success": False, "error": "Ma khong ton tai"}
    
    coupon = coupons[code]
    
    # Check active
    if not coupon.get("active", True):
        return {"success": False, "error": "Ma da vo hieu hoa"}
    
    # Check expiration
    if coupon.get("expires_at"):
        try:
            expires = datetime.strptime(coupon["expires_at"], "%Y-%m-%d")
            if datetime.now() > expires:
                return {"success": False, "error": "Ma da het han"}
        except ValueError:
            pass
    
    # Check max uses
    if coupon.get("max_uses"):
        if coupon.get("current_uses", 0) >= coupon["max_uses"]:
            return {"success": False, "error": "Ma da het luot su dung"}
    
    return {"success": True, "data": {"code": code, "discount": coupon["discount"]}}


def use_coupon(code: str) -> bool:
    """Increment coupon usage count."""
    code = code.upper().strip()
    data = load_subscriptions()
    coupons = data.get("coupons", get_coupons())
    
    if code in coupons:
        coupons[code]["current_uses"] = coupons[code].get("current_uses", 0) + 1
        data["coupons"] = coupons
        save_subscriptions(data)
        return True
    return False


def get_user_subscription(chat_id: int) -> Optional[Dict[str, Any]]:
    """Get user's active subscription."""
    data = load_subscriptions()
    user = data["users"].get(str(chat_id))
    
    if not user:
        return None
    
    sub = user.get("subscription")
    if not sub:
        return None
    
    # Check if expired
    expires_at = sub.get("expires_at")
    if expires_at:
        try:
            exp_date = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
            if datetime.now() > exp_date:
                sub["active"] = False
                save_subscriptions(data)
                return None
        except ValueError:
            pass
    
    return sub


def is_trial_expired_and_not_notified(chat_id: int) -> bool:
    """Return True if user had a free trial that is expired and we haven't notified yet."""
    data = load_subscriptions()
    user = data.get("users", {}).get(str(chat_id), {})
    if not user:
        return False

    sub = user.get("subscription") or {}
    if not sub.get("is_free_trial"):
        return False
    if user.get("trial_expired_notified"):
        return False

    expires_at = sub.get("expires_at")
    if not expires_at:
        return False
    try:
        exp_date = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return False
    return datetime.now() > exp_date


def mark_trial_expired_notified(chat_id: int) -> None:
    data = load_subscriptions()
    chat_str = str(chat_id)
    if chat_str not in data.get("users", {}):
        data.setdefault("users", {})[chat_str] = {}
    data["users"][chat_str]["trial_expired_notified"] = True
    save_subscriptions(data)


def grant_free_trial(chat_id: int) -> Dict[str, Any]:
    """Grant free trial to new user."""
    data = load_subscriptions()
    chat_str = str(chat_id)
    
    # Check if user already exists
    if chat_str in data["users"]:
        user = data["users"][chat_str]
        # Check if they've used free trial
        if user.get("free_trial_used", False):
            return {"success": False, "message": "Ban da su dung qua thoi gian dung thu."}
    
    # Create new user with free trial
    now = datetime.now()
    expires_at = now + timedelta(days=FREE_TRIAL_DAYS)
    
    if chat_str not in data["users"]:
        data["users"][chat_str] = {}
    
    data["users"][chat_str]["free_trial_used"] = True
    data["users"][chat_str]["subscription"] = {
        "active": True,
        "plan_id": "free_trial",
        "plan_name": "Dung Thu Mien Phi",
        "price": 0,
        "starts_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),
        "days": FREE_TRIAL_DAYS,
        "is_free_trial": True
    }
    
    # Add transaction record
    data["transactions"].append({
        "chat_id": chat_str,
        "type": "free_trial",
        "plan_id": "free_trial",
        "price": 0,
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S")
    })
    
    save_subscriptions(data)
    return {
        "success": True,
        "message": f"Cap {FREE_TRIAL_DAYS} ngay dung thu mien phi thanh cong!",
        "data": {
            "plan": "Dung Thu Mien Phi",
            "days": FREE_TRIAL_DAYS,
            "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S")
        }
    }


def has_used_free_trial(chat_id: int) -> bool:
    """Check if user has used their free trial."""
    data = load_subscriptions()
    chat_str = str(chat_id)
    if chat_str not in data["users"]:
        return False
    return data["users"][chat_str].get("free_trial_used", False)


def create_pending_payment(chat_id: int, plan_id: str, coupon_code: str = None) -> Dict[str, Any]:
    """Create a pending payment request."""
    if plan_id not in PLANS:
        return {"success": False, "message": "Goi khong hop le."}
    
    plan = PLANS[plan_id]
    price = plan["price"]
    discount = 0
    
    # Apply coupon if provided
    if coupon_code:
        coupon_result = verify_coupon(coupon_code)
        if coupon_result["success"]:
            discount = coupon_result["data"]["discount"]
    
    final_price = max(0, price - discount)
    
    # Create pending payment
    payments = load_payments()
    now = datetime.now()
    payment_id = f"{chat_id}_{now.strftime('%Y%m%d%H%M%S')}"
    
    payments["pending"][payment_id] = {
        "chat_id": chat_id,
        "plan_id": plan_id,
        "plan_name": plan["name"],
        "original_price": price,
        "discount": discount,
        "final_price": final_price,
        "coupon_code": coupon_code,
        "status": "pending",
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "photo_received": False
    }
    
    save_payments(payments)
    
    return {
        "success": True,
        "payment_id": payment_id,
        "data": {
            "plan": plan["name"],
            "original_price": price,
            "discount": discount,
            "final_price": final_price,
            "bank_info": f"Ngan hang: {os.environ.get('BANK_NAME', 'TPBank')}\nSo TK: {os.environ.get('BANK_ACCOUNT', '88998886666')}\nChu TK: {os.environ.get('BANK_OWNER', 'NGUYEN QUANG HOA')}\nNoi dung: AQ_{payment_id}"
        }
    }


def approve_payment(payment_id: str) -> Dict[str, Any]:
    """Approve a pending payment and activate subscription."""
    payments = load_payments()
    
    if payment_id not in payments["pending"]:
        return {"success": False, "message": "Khong tim thay yeu cau thanh toan."}
    
    
    payment = payments["pending"][payment_id]
    
    if payment["status"] != "pending":
        return {"success": False, "message": "Yeu cau thanh toan da duoc xu ly."}
    
    
    # Activate subscription
    chat_id = payment["chat_id"]
    plan_id = payment["plan_id"]
    plan = PLANS[plan_id]
    
    data = load_subscriptions()
    chat_str = str(chat_id)
    now = datetime.now()
    expires_at = now + timedelta(days=plan["duration_days"])
    
    if chat_str not in data["users"]:
        data["users"][chat_str] = {}
    
    data["users"][chat_str]["subscription"] = {
        "active": True,
        "plan_id": plan_id,
        "plan_name": plan["name"],
        "price": payment["final_price"],
        "starts_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),
        "days": plan["duration_days"],
        "is_free_trial": False,
        "payment_id": payment_id
    }
    
    # Add transaction
    data["transactions"].append({
        "chat_id": chat_str,
        "type": "paid_subscription",
        "plan_id": plan_id,
        "price": payment["final_price"],
        "payment_id": payment_id,
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S")
    })
    
    save_subscriptions(data)
    
    # Move payment to approved
    payment["status"] = "approved"
    payment["approved_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
    payments["approved"].append(payment)
    del payments["pending"][payment_id]
    save_payments(payments)
    
    return {
        "success": True,
        "message": "Duyet thanh toan thanh cong!",
        "data": {
            "chat_id": chat_id,
            "plan": plan["name"],
            "price": payment["final_price"],
            "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S")
        }
    }


def get_pending_payments() -> Dict[str, Any]:
    """Get all pending payments for admin."""
    payments = load_payments()
    return {"success": True, "data": payments["pending"]}


def has_active_subscription(chat_id: int) -> bool:
    """Check if user has active subscription."""
    sub = get_user_subscription(chat_id)
    return sub is not None and sub.get("active", False)


def grant_subscription(chat_id: int, plan_id: str, days: Optional[int] = None) -> Dict[str, Any]:
    """
    Admin grant subscription to a user (free, no coupon needed).
    Args:
        chat_id: User's Telegram chat_id
        plan_id: Plan ID (daily, weekly, monthly, quarterly, yearly)
        days: Optional custom days (overrides plan duration)
    Returns: {"success": bool, "message": str, "data": {...}}
    """
    if plan_id not in PLANS:
        return {"success": False, "message": "Goi khong hop le"}
    
    plan = PLANS[plan_id]
    duration = days if days else plan["duration_days"]
    
    data = load_subscriptions()
    chat_str = str(chat_id)
    
    # Initialize user if not exists
    if chat_str not in data["users"]:
        data["users"][chat_str] = {
            "chat_id": chat_id,
            "subscriptions_history": [],
            "applied_coupons": []
        }
    
    user = data["users"][chat_str]
    
    # Calculate expiration
    start_date = datetime.now()
    expires_at = start_date + timedelta(days=duration)
    
    # Create subscription
    subscription = {
        "plan_id": plan_id,
        "plan_name": plan["name"],
        "active": True,
        "start_date": start_date.strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),
        "price_paid": 0,
        "discount_applied": 0,
        "coupon_used": None,
        "granted_by_admin": True
    }
    
    # Update user
    user["subscription"] = subscription
    user.setdefault("subscriptions_history", []).append(subscription)
    
    # Record transaction
    data["transactions"].append({
        "chat_id": chat_id,
        "type": "admin_grant",
        "plan_id": plan_id,
        "price": 0,
        "discount": 0,
        "final_price": 0,
        "coupon": None,
        "timestamp": start_date.strftime("%Y-%m-%d %H:%M:%S")
    })
    
    save_subscriptions(data)
    
    return {
        "success": True,
        "message": f"Cap goi {plan['name']} thanh cong!",
        "data": {
            "plan": plan["name"],
            "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),
            "days": duration
        }
    }


def subscribe_user(chat_id: int, plan_id: str, coupon_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Subscribe a user to a plan.
    Returns: {"success": bool, "message": str, "data": {...}}
    """
    if plan_id not in PLANS:
        return {"success": False, "message": "Goi khong hop le"}
    
    plan = PLANS[plan_id]
    price = plan["price"]
    discount = 0
    
    # Apply coupon if provided
    if coupon_code:
        result = verify_coupon(coupon_code)
        if result["success"]:
            discount = result["data"]["discount"]
            # Coupon not applicable for daily/weekly
            if plan_id in ["daily", "weekly"]:
                discount = 0
    
    final_price = max(0, price - discount)
    
    data = load_subscriptions()
    chat_str = str(chat_id)
    
    # Initialize user if not exists
    if chat_str not in data["users"]:
        data["users"][chat_str] = {
            "chat_id": chat_id,
            "subscriptions_history": [],
            "applied_coupons": []
        }
    
    user = data["users"][chat_str]
    
    # Calculate expiration
    start_date = datetime.now()
    expires_at = start_date + timedelta(days=plan["duration_days"])
    
    # Create subscription
    subscription = {
        "plan_id": plan_id,
        "plan_name": plan["name"],
        "active": True,
        "start_date": start_date.strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),
        "price_paid": final_price,
        "discount_applied": discount,
        "coupon_used": coupon_code
    }
    
    # Update user
    user["subscription"] = subscription
    user.setdefault("subscriptions_history", []).append(subscription)
    if coupon_code and discount > 0:
        user.setdefault("applied_coupons", []).append(coupon_code)
    
    # Record transaction
    data["transactions"].append({
        "chat_id": chat_id,
        "type": "subscription",
        "plan_id": plan_id,
        "price": price,
        "discount": discount,
        "final_price": final_price,
        "coupon": coupon_code,
        "timestamp": start_date.strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # Increment coupon usage
    if coupon_code and discount > 0:
        use_coupon(coupon_code)
    
    save_subscriptions(data)
    
    return {
        "success": True,
        "message": f"Dang ky thanh cong goi {plan['name']}!",
        "data": {
            "plan": plan["name"],
            "price": price,
            "discount": discount,
            "final_price": final_price,
            "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S")
        }
    }


def get_subscription_status(chat_id: int) -> Dict[str, Any]:
    """Get detailed subscription status for user."""
    data = load_subscriptions()
    user = data["users"].get(str(chat_id))
    
    if not user:
        return {
            "has_subscription": False,
            "message": "Ban chua dang ky goi nao."
        }
    
    sub = user.get("subscription")
    if not sub:
        return {
            "has_subscription": False,
            "message": "Ban chua co goi active."
        }
    
    # Check expiration
    expires_at = sub.get("expires_at")
    days_left = 0
    if expires_at:
        try:
            exp_date = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
            days_left = max(0, (exp_date - datetime.now()).days)
        except ValueError:
            pass
    
    return {
        "has_subscription": True,
        "plan_name": sub.get("plan_name", "Unknown"),
        "active": sub.get("active", False),
        "expires_at": expires_at,
        "days_left": days_left,
        "features": PLANS.get(sub.get("plan_id", ""), {}).get("features", [])
    }


def format_plans_message() -> str:
    """Format plans list for Telegram message."""
    msg = "*CAC GOI SUBSCRIPTION*\n"
    msg += "-------------------\n\n"
    
    for plan_id, plan in PLANS.items():
        msg += f"*{plan['name']}* (`{plan_id}`)\n"
        msg += f"  - Gia: *{plan['price']:,}* VND\n"
        msg += f"  - Thoi han: {plan['duration_days']} ngay\n"
        msg += f"  - Tinh nang:\n"
        for feat in plan["features"]:
            msg += f"    + {feat}\n"
        msg += "\n"
    
    msg += "*Luu y:* Coupon khong ap dung cho goi Ngay va Tuan.\n"
    msg += "Dung `/subscribe <plan_id> [ma_coupon]` de dang ky.\n"
    msg += "VD: `/subscribe monthly NEWUSER`"
    
    return msg


def format_subscription_status(chat_id: int) -> str:
    """Format subscription status for Telegram message."""
    status = get_subscription_status(chat_id)
    
    if not status["has_subscription"]:
        return "*TRANG THAI SUBSCRIPTION*\n\n" + status["message"] + "\n\nDung `/plans` de xem cac goi."
    
    msg = "*TRANG THAI SUBSCRIPTION*\n"
    msg += "-------------------\n\n"
    msg += f"Goi: *{status['plan_name']}*\n"
    msg += f"Trang thai: {'Active' if status['active'] else 'Expired'}\n"
    msg += f"Het han: {status['expires_at']}\n"
    msg += f"Con {status['days_left']} ngay\n\n"
    
    if status.get("features"):
        msg += "Tinh nang:\n"
        for feat in status["features"]:
            msg += f"  + {feat}\n"
    
    return msg
