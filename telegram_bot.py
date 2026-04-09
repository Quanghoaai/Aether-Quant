import os
import json
import subprocess
import sys
import time
import socket
import logging
import re
from datetime import datetime
import requests.packages.urllib3.util.connection as urllib3_cn
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Company info helper
from company_info import get_company_info, format_company_info, get_company_name

# Subscription system
from subscription import (
    has_active_subscription,
    subscribe_user,
    verify_coupon,
    format_plans_message,
    format_subscription_status,
    grant_subscription,
    load_subscriptions,
    grant_free_trial,
    has_used_free_trial,
    create_pending_payment,
    approve_payment,
    get_pending_payments,
    FREE_TRIAL_DAYS,
    build_vietqr_image_url,
    is_trial_expired_and_not_notified,
    mark_trial_expired_notified,
    PLANS
)

# Force IPv4 to prevent ConnectionResetError on some Linux environments
def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family

load_dotenv()

CONFIG_FILE = "config.json"
PORTFOLIO_FILE = "portfolio.json"
USER_CONFIG_FILE = "user_configs.json"
TRANSACTIONS_FILE = "transactions.json"
DEFAULT_CAPITAL = 50000000  # 50 million VND default for new users
DEFAULT_CONFIG = {
    "primary": "HHV",
    "watchlist": ["TOS", "NKG", "AAS"],
    "min_score": 3.8
}

def load_all_transactions():
    """Load all transactions from file."""
    if os.path.exists(TRANSACTIONS_FILE):
        with open(TRANSACTIONS_FILE, "r") as f:
            data = json.load(f)
        if "users" not in data:
            return {"users": {}}
        return data
    return {"users": {}}

def save_all_transactions(data):
    """Save all transactions to file."""
    with open(TRANSACTIONS_FILE, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def log_transaction(chat_id: int, trans_type: str, symbol: str, qty: int, price: float, note: str = ""):
    """Log a transaction for a user."""
    data = load_all_transactions()
    chat_str = str(chat_id)

    if chat_str not in data["users"]:
        data["users"][chat_str] = []

    trans = {
        "type": trans_type,  # "BUY" or "SELL"
        "symbol": symbol,
        "qty": qty,
        "price": price,
        "total": qty * price,
        "note": note,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    data["users"][chat_str].append(trans)
    save_all_transactions(data)

def get_user_transactions(chat_id: int, limit: int = 20):
    """Get transactions for a user."""
    data = load_all_transactions()
    chat_str = str(chat_id)
    transactions = data["users"].get(chat_str, [])
    return transactions[-limit:] if transactions else []

def load_global_config():
    """Load global config (for backward compatibility)."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return DEFAULT_CONFIG

def load_all_user_configs():
    """Load all user configs from file."""
    if os.path.exists(USER_CONFIG_FILE):
        with open(USER_CONFIG_FILE, "r") as f:
            data = json.load(f)
        if "users" not in data:
            return {"users": {}}
        return data
    return {"users": {}}

def save_all_user_configs(data):
    """Save all user configs to file."""
    with open(USER_CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user_config(chat_id: int) -> dict:
    """Get config for a specific user, create if not exists."""
    data = load_all_user_configs()
    chat_str = str(chat_id)

    if chat_str not in data["users"]:
        # Create new config for user
        data["users"][chat_str] = DEFAULT_CONFIG.copy()
        save_all_user_configs(data)

    return data["users"][chat_str]

def save_user_config(chat_id: int, cfg: dict):
    """Save config for a specific user."""
    data = load_all_user_configs()
    data["users"][str(chat_id)] = cfg
    save_all_user_configs(data)

def load_all_portfolios():
    """Load all portfolios from file."""
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            data = json.load(f)
        # Handle old format (single portfolio) vs new format (per-user)
        if "users" not in data:
            # Old format - convert to new format
            # Check if it has old portfolio keys
            if "cash" in data or "positions" in data:
                # Migrate old portfolio to admin's portfolio
                admin_chat_id = os.environ.get("ADMIN_CHAT_ID", "default")
                return {"users": {admin_chat_id: data}}
            return {"users": {}}
        return data
    return {"users": {}}

def save_all_portfolios(data):
    """Save all portfolios to file."""
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user_portfolio(chat_id: int) -> dict:
    """Get portfolio for a specific user, create if not exists."""
    data = load_all_portfolios()
    chat_str = str(chat_id)

    if chat_str not in data["users"]:
        # Create new portfolio for user
        data["users"][chat_str] = {
            "cash": DEFAULT_CAPITAL,
            "positions": {},
            "capital": DEFAULT_CAPITAL
        }
        save_all_portfolios(data)

    return data["users"][chat_str]

def save_user_portfolio(chat_id: int, portfolio: dict):
    """Save portfolio for a specific user."""
    data = load_all_portfolios()
    data["users"][str(chat_id)] = portfolio
    save_all_portfolios(data)

def run_analysis(cfg, capital, chat_id):
    """Run main.py with current config and return output."""
    wl = ",".join(cfg["watchlist"])
    cmd = [
        sys.executable, "main.py",
        "--mode", "hybrid",
        "--primary", cfg["primary"],
        "--watchlist", wl,
        "--cap", str(capital),
        "--min_score", str(cfg["min_score"]),
        "--chat_id", str(chat_id)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "Error: Phân tích quá lâu (Timeout > 300s). Vui lòng thử lại sau hoặc kiểm tra kết nối mạng trên Host."
    except Exception as e:
        return f"Error: {e}"

def main():
    import requests

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        print("TELEGRAM_BOT_TOKEN not set in .env")
        return

    base_url = f"https://api.telegram.org/bot{bot_token}"

    # Load last offset to avoid re-processing messages after restart
    offset_file = "bot_offset.txt"
    offset = 0
    if os.path.exists(offset_file):
        try:
            with open(offset_file, "r") as f:
                offset = int(f.read().strip())
            logger.info(f"Resuming from offset: {offset}")
        except:
            offset = 0
    
    # Register command menu on Telegram
    commands = [
        {"command": "start", "description": "Khởi động bot"},
        {"command": "plans", "description": "Xem các gói subscription"},
        {"command": "subscribe", "description": "Đăng ký (VD: /subscribe monthly NEWUSER)"},
        {"command": "coupon", "description": "Kiểm tra mã giảm giá (VD: /coupon NEWUSER)"},
        {"command": "subscription", "description": "Xem trạng thái đăng ký"},
        {"command": "status", "description": "Xem cấu hình hiện tại"},
        {"command": "run", "description": "Chạy phân tích ngay lập tức"},
        {"command": "portfolio", "description": "Xem danh mục đầu tư"},
        {"command": "history", "description": "Xem lịch sử giao dịch"},
        {"command": "watchlist", "description": "Xem watchlist hiện tại"},
        {"command": "add", "description": "Thêm mã vào watchlist (VD: /add FPT)"},
        {"command": "remove", "description": "Xóa mã khỏi watchlist (VD: /remove NKG)"},
        {"command": "confirm_buy", "description": "Xác nhận mua (VD: /confirm_buy TCB 1000 25500)"},
        {"command": "confirm_sell", "description": "Xác nhận bán (VD: /confirm_sell TCB 500)"},
        {"command": "set_capital", "description": "Đổi vốn (VD: /set_capital 100000000)"},
        {"command": "reset_capital", "description": "Reset vốn và xóa vị thế"},
        {"command": "set_minscore", "description": "Đổi điểm (VD: /set_minscore 3.5)"},
        {"command": "update", "description": "Admin: Cập nhật bot từ GitHub"},
        {"command": "help", "description": "Xem hướng dẫn sử dụng"}
    ]
    resp = requests.post(f"{base_url}/setMyCommands", json={"commands": commands})
    if resp.status_code == 200:
        logger.info("Commands menu registered on Telegram!")

    # Send startup notification to admin
    admin_chat_id = os.environ.get("ADMIN_CHAT_ID", "")
    if admin_chat_id:
        startup_msg = " *BOT DA KHOI DONG THANH CONG!*\n\n"
        startup_msg += f"Thoi gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        startup_msg += "Bot san sang nhan lenh."
        send_msg(bot_token, int(admin_chat_id), startup_msg)

    logger.info("Bot started! Waiting for Telegram commands...")

    while True:
        try:
            resp = requests.get(f"{base_url}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
            updates = resp.json().get("result", [])
            
            for update in updates:
                offset = update["update_id"] + 1

                # Save offset to file
                try:
                    with open(offset_file, "w") as f:
                        f.write(str(offset))
                except:
                    pass

                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "").strip()
                
                if not chat_id:
                    continue
                
                # Check if message has photo (payment receipt)
                if msg.get("photo"):
                    # Get the largest photo
                    photos = msg["photo"]
                    photo = photos[-1]  # Largest size
                    file_id = photo["file_id"]
                    
                    # Check if it's a reply to payment request
                    reply_to = msg.get("reply_to_message", {})
                    reply_text = reply_to.get("text", "")
                    
                    # Extract payment_id from reply
                    payment_id = None
                    if "Ma GD:" in reply_text:
                        import re
                        match = re.search(r"Ma GD: `([^`]+)`", reply_text)
                        if match:
                            payment_id = match.group(1)
                    
                    if payment_id:
                        # Mark payment as having photo
                        from subscription import load_payments, save_payments
                        payments = load_payments()
                        if payment_id in payments["pending"]:
                            payments["pending"][payment_id]["photo_received"] = True
                            payments["pending"][payment_id]["photo_file_id"] = file_id
                            save_payments(payments)
                            
                            # Notify user
                            send_msg(bot_token, chat_id, " *Da nhan anh bien nhan!*\n\nAdmin se duyet trong thoi gian ngan. Cam on ban!")
                            
                            # Notify admin
                            admin_chat_id = os.environ.get("ADMIN_CHAT_ID", "")
                            if admin_chat_id:
                                admin_msg = f" *ANH BIEN NHAN MOI*\n\n"
                                admin_msg += f"Chat ID: `{chat_id}`\n"
                                admin_msg += f"Ma GD: `{payment_id}`\n"
                                admin_msg += f"Thoi gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                                admin_msg += "Dung `/payments` de xem chi tiet.\n"
                                admin_msg += f"Dung `/approve {payment_id}` de duyet."
                                send_msg(bot_token, int(admin_chat_id), admin_msg)
                                # Forward photo to admin
                                forward_photo(bot_token, int(admin_chat_id), file_id)
                        else:
                            send_msg(bot_token, chat_id, "Khong tim thay ma giao dich. Vui long reply vao tin nhan yeu cau thanh toan.")
                    else:
                        send_msg(bot_token, chat_id, "Vui long reply vao tin nhan yeu cau thanh toan khi gui anh bien nhan.")
                    continue
                
                if not text:
                    continue
                
                # Log incoming command with chat_id
                logger.info(f"Received from chat_id={chat_id}: {text}")
                
                reply = handle_command(text, chat_id, bot_token)
                if reply:
                    send_msg(bot_token, chat_id, reply)
                    
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)

def handle_command(text, chat_id, bot_token):
    """Process a command and return reply text."""
    
    parts = text.split()
    cmd = parts[0].lower() if parts else ""
    
    # Get user's own config
    cfg = get_user_config(chat_id)

    # Notify user when free trial just expired (send once)
    if is_trial_expired_and_not_notified(chat_id):
        mark_trial_expired_notified(chat_id)
        msg = "*DUNG THU DA HET HAN!*\n\n"
        msg += "Ban vui long chon goi va thanh toan de tiep tuc su dung bot.\n\n"
        msg += "*CAC GOI HIEN CO:*\n"
        for plan_id, plan in PLANS.items():
            msg += f"- `{plan_id}`: {plan['name']} - *{plan['price']:,.0f}* VND ({plan['duration_days']} ngay)\n"
        msg += "\nDung: `/subscribe <plan_id>` de tao yeu cau thanh toan.\n"
        msg += "Hoac dung: `/qr <plan_id>` de nhan QR thanh toan nhanh."
        send_msg(bot_token, chat_id, msg)
    
    # /start or /help
    if cmd in ["/start", "/help"]:
        # Auto-grant free trial for new users
        trial_msg = ""
        if cmd == "/start" and not has_used_free_trial(chat_id):
            result = grant_free_trial(chat_id)
            if result["success"]:
                trial_msg = f"\n\n *QUA TANG: {FREE_TRIAL_DAYS} NGAY DUNG THU MIEN PHI!*\n"
                trial_msg += f"Het han: {result['data']['expires_at']}\n"

        return (
            " *Aether-Quant HCA Bot*\n\n"
            f" *Chat ID cua ban:* `{chat_id}`\n"
            f"{trial_msg}\n"
            "*SUBSCRIPTION:*\n"
            " */plans* - Xem cac goi\n"
            " */subscribe <goi> [coupon]* - Dang ky\n"
            " */coupon <ma>* - Kiem tra coupon\n"
            " */subscription* - Trang thai goi\n\n"
            "*TRADING:*\n"
            " */status* - Xem cau hinh\n"
            " */portfolio* - Xem danh muc & PnL\n"
            " */history* - Xem lich su giao dich\n"
            " */run* - Chay phan tich ngay\n"
            " */watchlist* - Xem watchlist\n"
            " */info MA* - Xem thong tin cong ty\n"
            " */add MA1,MA2* - Them ma\n"
            " */remove MA1,MA2* - Xoa ma\n"
            " */confirm\\_buy MA SL GIA* - Xac nhan mua\n"
            " */confirm\\_sell MA SL [GIA]* - Xac nhan ban\n"
            " */set\\_capital SO* - Doi von\n"
            " */reset\\_capital SO* - Reset von & xoa vi the\n"
            " */set\\_minscore SO* - Doi diem\n\n"
            " *TUYEN BO TRACH NHIEM:*\n"
            " Phan tich tu du an AI Trading ca nhan. Su dung Python + VNStock API. *Khong phai loi khuyen dau tu.*\n"
        )
    
    # /myid - Show user's chat ID
    elif cmd == "/myid":
        return f" *Chat ID cua ban:* `{chat_id}`"

    # /qr - Send VietQR for a plan (quick pay)
    elif cmd == "/qr":
        if len(parts) < 2:
            return "Cu phap: `/qr <plan_id>`\n\nVD: `/qr monthly`"
        plan_id = parts[1].lower()
        if plan_id not in PLANS:
            return "Plan ID khong hop le. Dung `/plans` de xem danh sach."

        plan = PLANS[plan_id]
        add_info = f"AQ_{chat_id}_{plan_id}"
        qr_url = build_vietqr_image_url(plan["price"], add_info)
        if not qr_url:
            return "Chua cau hinh VietQR (BANK_BIN/BANK_ACCOUNT)."

        send_photo_url(bot_token, chat_id, qr_url, caption=(
            f"*QR THANH TOAN*\n\nGoi: {plan['name']}\nSo tien: *{plan['price']:,.0f}* VND\nNoi dung: `{add_info}`"
        ))
        return None
    
    # /status
    elif cmd == "/status":
        wl = ", ".join(cfg["watchlist"])
        pf = get_user_portfolio(chat_id)
        capital = pf.get("capital", DEFAULT_CAPITAL)
        return (
            " *Cau hinh hien tai*\n\n"
            f" Ma chinh: *{cfg['primary']}*\n"
            f" Watchlist: *{wl}*\n"
            f" Von: *{capital:,.0f}* VND\n"
            f" Min Score: *{cfg['min_score']}*\n"
        )
    
    # /portfolio
    elif cmd == "/portfolio":
        pf = get_user_portfolio(chat_id)
        capital = pf.get("capital", DEFAULT_CAPITAL)
        cash_pct = (pf['cash'] / capital) * 100 if capital > 0 else 0
        
        text = "💼 *DANH MỤC ĐẦU TƯ*\n"
        text += "──────────────────────\n\n"
        text += f"� Vốn ban đầu: *{capital:,.0f}* VND\n"
        text += f"�💰 Tiền mặt: *{pf['cash']:,.0f}* VND ({cash_pct:.0f}%)\n\n"
        
        if not pf['positions']:
            pnl = pf['cash'] - capital
            pnl_pct = (pnl / capital) * 100 if capital > 0 else 0
            text += "📌 *Chưa có vị thế nào.*\n\n"
            text += f"📈 PnL hiện tại: *{pnl:+,.0f}* VND ({pnl_pct:+.1f}%)\n\n"
            text += "💡 *HƯỚNG DẪN:*\n"
            text += "- Chạy `/run` để phân tích\n"
            text += "- Dùng `/confirm_buy MA SL GIA` để mua\n"
            text += "- VD: `/confirm_buy TCB 100 25000`\n"
        else:
            total_invested = 0
            for sym, pos in pf['positions'].items():
                qty = pos['qty']
                avg = pos['avg_price']
                val = qty * avg
                total_invested += val
                tp1_hit = "✅" if pos.get("tp_level_1_hit") else "❌"
                text += f"*{sym}*\n"
                text += f"  KL: {qty:,} cp | Giá TB: {avg:,.0f}\n"
                text += f"  Giá trị: {val:,.0f} VND\n"
                text += f"  TP1 hit: {tp1_hit}\n\n"
            
            total_assets = pf['cash'] + total_invested
            text += f"📊 Tổng tài sản: *{total_assets:,.0f}* VND\n"
            pnl = total_assets - capital
            text += f"📈 PnL: *{pnl:+,.0f}* VND ({pnl/capital*100:+.1f}%)\n"
        
        return text
    
    # /confirm_buy SYMBOL QTY PRICE
    elif cmd == "/confirm_buy":
        if len(parts) < 4:
            return " Cu phap: `/confirm_buy MA SO_CP GIA`\nVD: `/confirm_buy TCB 1000 25500`"
        sym = parts[1].upper()
        try:
            qty = int(parts[2])
            price = float(parts[3])
        except ValueError:
            return " So luong hoac gia khong hop le."
        
        pf = get_user_portfolio(chat_id)
        capital = pf.get("capital", DEFAULT_CAPITAL)
        
        # Calculate cost with fee (0.15% broker fee)
        gross = qty * price
        fee = gross * 0.0015  # 0.15% fee
        cost = gross + fee
        
        if cost > pf['cash']:
            return f" Khong du tien mat! Can {cost:,.0f} (da tinh phi) nhung chi co {pf['cash']:,.0f}"
        
        # Check cash reserve (20% of capital)
        min_reserve = capital * 0.20
        if pf['cash'] - cost < min_reserve:
            return f" Vi pham quy tac giu 20% tien mat! Sau khi mua chi con {pf['cash']-cost:,.0f} < {min_reserve:,.0f}"
        
        if sym in pf['positions']:
            old = pf['positions'][sym]
            total_qty = old['qty'] + qty
            avg_price = (old['avg_price'] * old['qty'] + price * qty) / total_qty
            pf['positions'][sym] = {"qty": total_qty, "avg_price": round(avg_price, 0), "highest_price": max(old.get("highest_price", price), price)}
        else:
            pf['positions'][sym] = {"qty": qty, "avg_price": price, "highest_price": price}
        
        pf['cash'] -= cost
        save_user_portfolio(chat_id, pf)

        # Log transaction
        log_transaction(chat_id, "BUY", sym, qty, price, f"Mua {qty} cp @ {price:,.0f}, phi: {fee:,.0f}")

        return (
            f"✅ ĐÃ MUA {sym}\n"
            f"KL: {qty:,} cp @ {price:,.0f}\n"
            f"Thành tiền: {gross:,.0f} VND\n"
            f"Phí GD (0.15%): {fee:,.0f} VND\n"
            f"Tổng chi phí: {cost:,.0f} VND\n"
            f"Tiền mặt còn: {pf['cash']:,.0f} VND"
        )
    
    # /confirm_sell SYMBOL QTY
    elif cmd == "/confirm_sell":
        if len(parts) < 3:
            return " Cu phap: `/confirm_sell MA SO_CP`\nVD: `/confirm_sell TCB 500`"
        sym = parts[1].upper()
        try:
            qty = int(parts[2])
        except ValueError:
            return " So luong khong hop le."
        
        pf = get_user_portfolio(chat_id)
        
        if sym not in pf['positions']:
            return f" Khong co vi the *{sym}* trong danh muc."
        
        pos = pf['positions'][sym]
        if qty > pos['qty']:
            return f" Chi co {pos['qty']:,} cp {sym}, khong the ban {qty:,} cp."
        
        # Use avg_price as estimated sell price (user can input 4th param for actual price)
        sell_price = float(parts[3]) if len(parts) >= 4 else pos['avg_price']
        
        # Calculate revenue with fee (0.15% broker + 0.1% tax = 0.25%)
        gross = qty * sell_price
        fee = gross * 0.0025  # 0.25% fee
        revenue = gross - fee
        pnl = (sell_price - pos['avg_price']) * qty - fee
        
        pos['qty'] -= qty
        if pos['qty'] <= 0:
            del pf['positions'][sym]
        else:
            pf['positions'][sym] = pos
        
        pf['cash'] += revenue
        save_user_portfolio(chat_id, pf)

        # Log transaction
        log_transaction(chat_id, "SELL", sym, qty, sell_price, f"Bán {qty} cp @ {sell_price:,.0f}, phi: {fee:,.0f}, PnL: {pnl:+,.0f}")

        return (
            f"✅ ĐÃ BÁN {sym}\n"
            f"KL: {qty:,} cp @ {sell_price:,.0f}\n"
            f"Thành tiền: {gross:,.0f} VND\n"
            f"Phí GD (0.25%): {fee:,.0f} VND\n"
            f"Thu về: {revenue:,.0f} VND\n"
            f"PnL: {pnl:+,.0f} VND\n"
            f"Tiền mặt: {pf['cash']:,.0f} VND"
        )

    # /set_primary
    elif cmd == "/set_primary":
        if len(parts) < 2:
            return "Thieu ma. VD: `/set_primary HHV`"
        new_primary = parts[1].upper()
        cfg["primary"] = new_primary
        save_user_config(chat_id, cfg)
        return f"Da doi ma chinh -> *{new_primary}*"

    # /set_watchlist
    elif cmd == "/set_watchlist":
        if len(parts) < 2:
            return "Thieu danh sach. VD: `/set_watchlist TOS,NKG,AAS`"
        wl = [s.strip().upper() for s in parts[1].split(",") if s.strip()]
        cfg["watchlist"] = wl
        save_user_config(chat_id, cfg)
        return f"Da doi Watchlist -> *{', '.join(wl)}*"

    # /watchlist - View current watchlist
    elif cmd == "/watchlist":
        if not cfg["watchlist"]:
            return "Watchlist dang trong.\n\nDung `/add MA1,MA2,MA3` de them ma."

        msg = "*WATCHLIST HIEN TAI*\n"
        msg += "-------------------\n\n"
        msg += f"Ma chinh: *{cfg['primary']}*\n"
        msg += f"Watchlist: *{', '.join(cfg['watchlist'])}*\n\n"
        msg += "Lenh:\n"
        msg += "- `/add MA1,MA2` - Them nhieu ma\n"
        msg += "- `/remove MA1,MA2` - Xoa nhieu ma\n"
        msg += "- `/set_watchlist MA1,MA2,MA3` - Thay the toan bo"
        return msg

    # /info - Get company information
    elif cmd == "/info":
        if len(parts) < 2:
            return "Cu phap: `/info MA`\n\nVD: `/info TCB`"

        sym = parts[1].upper()
        info = get_company_info(sym)

        msg = f"?? *THONG TIN {sym}*\n"
        msg += "-------------------\n\n"

        if info.get('name'):
            msg += f"?? Ten: {info['name']}\n"
        else:
            msg += f"?? Ten: (Chua co du lieu)\n"

        if info.get('industry'):
            msg += f"?? Nganh: {info['industry']}\n"

        if info.get('exchange'):
            msg += f"?? San: {info['exchange']}\n"

        if info.get('price', 0) > 0:
            msg += f"?? Gia: {info['price']:,.0f} VND\n"

        if info.get('market_cap', 0) > 0:
            cap_b = info['market_cap'] / 1e9
            msg += f"?? Von hoa: {cap_b:.1f}B VND\n"

        if info.get('description'):
            msg += f"\n?? *Mo ta:*\n_{info['description']}\n"
        else:
            msg += f"\n?? *Mo ta:* (Chua co du lieu)\n"

        msg += f"\n?? Dung `/add {sym}` de them vao Watchlist"
        return msg

    # /add - Add one or multiple symbols
    elif cmd == "/add":
        if len(parts) < 2:
            return "Cu phap: `/add MA1,MA2,MA3`\n\nVD: `/add VNM,TCB,FPT`"

        # Parse multiple symbols (comma or space separated)
        symbols_input = " ".join(parts[1:])
        new_symbols = [s.strip().upper() for s in symbols_input.replace(",", " ").split() if s.strip()]

        if not new_symbols:
            return "Khong tim thay ma nao hop le."

        added = []
        existed = []

        for sym in new_symbols:
            # Validate: must be 2-5 letters, alphanumeric
            if not sym.isalnum() or len(sym) < 2 or len(sym) > 5:
                continue

            if sym not in cfg["watchlist"]:
                cfg["watchlist"].append(sym)
                added.append(sym)
            else:
                existed.append(sym)

        if added:
            save_user_config(chat_id, cfg)
            msg = f"?? Da them *{len(added)}* ma vao Watchlist:\n\n"
            
            # Show company info for each added symbol
            for sym in added:
                try:
                    info = get_company_info(sym)
                    name = info.get('name', '')[:30] if info.get('name') else ''
                    industry = info.get('industry', '')[:20] if info.get('industry') else ''
                    description = info.get('description', '')[:150] if info.get('description') else ''
                    
                    msg += f"?? *{sym}*"
                    if name:
                        msg += f" - {name}"
                    if industry:
                        msg += f" [{industry}]"
                    msg += "\n"
                    if description:
                        msg += f"  _{description}_\n"
                except:
                    msg += f"?? *{sym}*\n"
            
            msg += f"\nWatchlist hien tai: *{', '.join(cfg['watchlist'])}*\n"
            if existed:
                msg += f"\nDa co san: *{', '.join(existed)}*"
            return msg
        elif existed:
            return f"Tat ca da co trong Watchlist: *{', '.join(existed)}*"
        else:
            return "Khong co ma hop le de them."

    # /remove - Remove one or multiple symbols
    elif cmd == "/remove":
        if len(parts) < 2:
            return "Cu phap: `/remove MA1,MA2,MA3`\n\nVD: `/remove NKG,VNM`"

        # Parse multiple symbols (comma or space separated)
        symbols_input = " ".join(parts[1:])
        remove_symbols = [s.strip().upper() for s in symbols_input.replace(",", " ").split() if s.strip()]

        if not remove_symbols:
            return "Khong tim thay ma nao hop le."

        removed = []
        not_found = []

        for sym in remove_symbols:
            if sym in cfg["watchlist"]:
                cfg["watchlist"].remove(sym)
                removed.append(sym)
            else:
                not_found.append(sym)

        if removed:
            save_user_config(chat_id, cfg)
            msg = f"?? Da xoa *{len(removed)}* ma khoi Watchlist:\n\n"
            
            # Show company info for each removed symbol
            for sym in removed:
                try:
                    info = get_company_info(sym)
                    name = info.get('name', '')[:25] if info.get('name') else ''
                    msg += f"?? *{sym}*"
                    if name:
                        msg += f" - {name}"
                    msg += "\n"
                except:
                    msg += f"?? *{sym}*\n"
            
            msg += f"\nWatchlist con lai: *{', '.join(cfg['watchlist']) if cfg['watchlist'] else '(trong)'}*\n"
            if not_found:
                msg += f"\nKhong co trong list: *{', '.join(not_found)}*"
            return msg
        else:
            return f"Khong tim thay ma nao trong Watchlist: *{', '.join(not_found)}*"

    # /set_capital - Set user's own capital
    elif cmd == "/set_capital":
        if len(parts) < 2:
            return "Thieu so von. VD: `/set_capital 100000000`"
        try:
            cap = int(parts[1])
            pf = get_user_portfolio(chat_id)
            pf["capital"] = cap
            save_user_portfolio(chat_id, pf)
            return f"Da doi von cua ban -> *{cap:,.0f}* VND"
        except ValueError:
            return "So von khong hop le."

    # /set_minscore
    elif cmd == "/set_minscore":
        if len(parts) < 2:
            return " Thiếu điểm. VD: `/set_minscore 3.5`"
        try:
            ms = float(parts[1])
            cfg["min_score"] = ms
            save_user_config(chat_id, cfg)
            return f"✅ Đã đổi Min Score → *{ms}*"
        except ValueError:
            return "⚠️ Số điểm không hợp lệ."

    # /history - View transaction history
    elif cmd == "/history":
        transactions = get_user_transactions(chat_id, limit=15)

        if not transactions:
            return "Chua co giao dich nao.\n\nDung `/confirm_buy MA SL GIA` de ghi nhan mua."

        msg = "*LICH SU GIAO DICH*\n"
        msg += "-------------------\n\n"

        total_buy = 0
        total_sell = 0

        for t in transactions:
            icon = "???" if t['type'] == 'BUY' else "???"
            msg += f"{icon} *{t['symbol']}*\n"
            msg += f"  {t['type']}: {t['qty']:,} cp @ {t['price']:,.0f}\n"
            msg += f"  Thanh tien: {t['total']:,.0f} VND\n"
            msg += f"  Thoi gian: {t['timestamp']}\n\n"

            if t['type'] == 'BUY':
                total_buy += t['total']
            else:
                total_sell += t['total']

        msg += f"??? Tong mua: *{total_buy:,.0f}* VND\n"
        msg += f"??? Tong ban: *{total_sell:,.0f}* VND\n"
        msg += f"??? Chenh lech: *{total_sell - total_buy:+,.0f}* VND"

        return msg

    # /reset_capital - Reset capital (clear all positions)
    elif cmd == "/reset_capital":
        if len(parts) < 2:
            return "Cu phap: `/reset_capital SO_VON_MOI`\n\nVD: `/reset_capital 100000000`\n\n??? *CANH BAO:* Lenh nay se xoa toan bo vi the hien tai!"

        try:
            new_capital = int(parts[1])
        except ValueError:
            return "So von khong hop le."

        pf = get_user_portfolio(chat_id)

        # Check if needs confirm
        if len(parts) < 3 or parts[2].lower() != "confirm":
            if pf['positions']:
                old_pnl = pf['cash'] - pf.get('capital', DEFAULT_CAPITAL)
                msg = "??? *CANH BAO: BAN CO VI THE!*\n\n"
                msg += f"So vi the: {len(pf['positions'])}\n"
                msg += f"Tien mat hien tai: {pf['cash']:,.0f} VND\n"
                msg += f"PnL hien tai: {old_pnl:+,.0f} VND\n\n"
                msg += f"De xac nhan reset, dung:\n`/reset_capital {new_capital} confirm`"
                return msg

        # Reset portfolio
        pf['capital'] = new_capital
        pf['cash'] = new_capital
        pf['positions'] = {}
        save_user_portfolio(chat_id, pf)

        return f"??? Da reset von!\n\nVon moi: *{new_capital:,.0f}* VND\nTien mat: *{new_capital:,.0f}* VND\nChua co vi the."

    # /user_history - Admin: view user's transaction history
    elif cmd == "/user_history":
        admin_chat_id = os.environ.get("ADMIN_CHAT_ID", "")
        if str(chat_id) != str(admin_chat_id):
            return "Ban khong co quyen su dung lenh nay."

        if len(parts) < 2:
            return "Cu phap: `/user_history <chat_id>`\n\nVD: `/user_history 5529264160`"

        try:
            target_chat_id = int(parts[1])
        except ValueError:
            return "Chat ID khong hop le."

        transactions = get_user_transactions(target_chat_id, limit=20)
        pf = get_user_portfolio(target_chat_id)

        if not transactions:
            return f"User `{target_chat_id}` chua co giao dich nao."

        msg = f"??? *LICH SU USER `{target_chat_id}`*\n"
        msg += "-------------------------\n\n"

        for t in transactions[-10:]:
            icon = "???" if t['type'] == 'BUY' else "???"
            msg += f"{icon} {t['symbol']}: {t['qty']:,} @ {t['price']:,.0f}\n"
            msg += f"   {t['timestamp']}\n"

        msg += f"\n??? Tien mat: {pf['cash']:,.0f} VND\n"
        msg += f"??? Vi the: {len(pf['positions'])} ma"

        return msg

    # /plans - View subscription plans
    elif cmd == "/plans":
        return format_plans_message()
    
    # /subscribe - Subscribe to a plan (create pending payment)
    elif cmd == "/subscribe":
        if len(parts) < 2:
            return "Cu phap: `/subscribe <plan_id> [ma_giam_gia]`\n\nPlan ID: `daily`, `weekly`, `monthly`, `quarterly`, `yearly`\nVD: `/subscribe monthly NEWUSER`\n\nDung `/plans` de xem cac goi."
        plan_id = parts[1].lower()
        coupon_code = parts[2].upper() if len(parts) >= 3 else None
        
        # Create pending payment
        result = create_pending_payment(chat_id, plan_id, coupon_code)
        
        if result["success"]:
            data = result["data"]
            payment_id = result["payment_id"]
            msg = f" *YEU CAU THANH TOAN*\n\n"
            msg += f"Goi: {data['plan']}\n"
            msg += f"Gia goc: {data['original_price']:,.0f} VND\n"
            if data['discount'] > 0:
                msg += f"Giam gia: -{data['discount']:,.0f} VND\n"
            msg += f"Can thanh toan: *{data['final_price']:,.0f}* VND\n\n"
            msg += f" *THONG TIN CHUYEN KHOAN:*\n"
            msg += f"```\n{data['bank_info'].replace('{payment_id}', payment_id)}\n```\n\n"
            msg += f" *HUONG DAN:*\n"
            msg += f"1. Chuyen khoan dung so tien\n"
            msg += f"2. Chup anh bien nhan\n"
            msg += f"3. Gui anh cho bot (reply tin nhan nay)\n"
            msg += f"4. Cho admin duyet\n\n"
            msg += f"Ma GD: `{payment_id}`"
            return msg
        else:
            return f"{result['message']}"
    
    # /coupon - Verify a coupon
    elif cmd == "/coupon":
        if len(parts) < 2:
            return "Cú pháp: `/coupon <mã>`\nVD: `/coupon NEWUSER`"
        code = parts[1].upper()
        result = verify_coupon(code)
        
        if result["success"]:
            data = result["data"]
            return f"*Mã hợp lệ!* \n\nMã: `{data['code']}`\nGiảm giá: *{data['discount']:,.0f}* VND\n\nDùng `/subscribe <gói> {code}` để đăng ký."
        else:
            return f"{result['error']}"
    
    # /subscription - View subscription status
    elif cmd == "/subscription":
        return format_subscription_status(chat_id)
    
    # /users - Admin only: list all users
    elif cmd == "/users":
        admin_chat_id = os.environ.get("ADMIN_CHAT_ID", "")
        if str(chat_id) != str(admin_chat_id):
            return "Ban khong co quyen su dung lenh nay."

        # Load all data
        user_configs = load_all_user_configs()
        user_portfolios = load_all_portfolios()
        sub_data = load_subscriptions()

        msg = "*DANH SACH USERS*\n"
        msg += "-----------------\n\n"

        all_chat_ids = set(user_configs.get("users", {}).keys())
        all_chat_ids.update(user_portfolios.get("users", {}).keys())
        all_chat_ids.update(sub_data.get("users", {}).keys())

        if not all_chat_ids:
            msg += "Chua co user nao."
        else:
            for cid in sorted(all_chat_ids):
                # Get subscription status - check if actually active
                sub_status = "Chua dang ky"
                sub = sub_data.get("users", {}).get(cid, {}).get("subscription")
                if sub:
                    # Check if expired
                    expires_at = sub.get("expires_at")
                    is_expired = False
                    if expires_at:
                        try:
                            from datetime import datetime
                            exp_date = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
                            is_expired = datetime.now() > exp_date
                        except:
                            pass

                    if is_expired:
                        sub_status = f"EXPIRED ({sub.get('plan_name', 'N/A')})"
                    elif sub.get("active"):
                        sub_status = f"Active ({sub.get('plan_name', 'N/A')})"
                    else:
                        sub_status = f"Inactive ({sub.get('plan_name', 'N/A')})"

                # Get portfolio info
                pf = user_portfolios.get("users", {}).get(cid, {})
                capital = pf.get("capital", DEFAULT_CAPITAL)

                msg += f"Chat ID: `{cid}`\n"
                msg += f"  Von: {capital:,.0f} VND\n"
                msg += f"  Sub: {sub_status}\n\n"

        return msg
    
    # /grant - Admin only: grant subscription to user
    elif cmd == "/grant":
        admin_chat_id = os.environ.get("ADMIN_CHAT_ID", "")
        if str(chat_id) != str(admin_chat_id):
            return "Ban khong co quyen su dung lenh nay."
        
        if len(parts) < 3:
            return "Cu phap: `/grant <chat_id> <plan_id> [days]`\n\nVD: `/grant 123456789 monthly`\nVD: `/grant 123456789 monthly 60` (60 days)"
        
        try:
            target_chat_id = int(parts[1])
        except ValueError:
            return "Chat ID khong hop le."
        
        plan_id = parts[2].lower()
        days = int(parts[3]) if len(parts) >= 4 else None
        
        result = grant_subscription(target_chat_id, plan_id, days)
        
        if result["success"]:
            data = result["data"]
            msg = f"*{result['message']}*\n\n"
            msg += f"Chat ID: `{target_chat_id}`\n"
            msg += f"Goi: {data['plan']}\n"
            msg += f"So ngay: {data['days']}\n"
            msg += f"Het han: {data['expires_at']}"
            return msg
        else:
            return result["message"]
    
    # /payments - Admin only: view pending payments
    elif cmd == "/payments":
        admin_chat_id = os.environ.get("ADMIN_CHAT_ID", "")
        if str(chat_id) != str(admin_chat_id):
            return "Ban khong co quyen su dung lenh nay."
        
        result = get_pending_payments()
        pending = result["data"]
        
        if not pending:
            return "Khong co yeu cau thanh toan nao dang cho."
        
        msg = " *DANH SACH THANH TOAN CHO*\n"
        msg += "------------------------\n\n"
        
        for payment_id, payment in pending.items():
            msg += f"Ma GD: `{payment_id}`\n"
            msg += f"  Chat ID: `{payment['chat_id']}`\n"
            msg += f"  Goi: {payment['plan_name']}\n"
            msg += f"  So tien: {payment['final_price']:,.0f} VND\n"
            msg += f"  Thoi gian: {payment['created_at']}\n"
            msg += f"  Anh: {'Co' if payment.get('photo_received') else 'Chua'}\n\n"
        
        msg += "Dung `/approve <ma_gd>` de duyet."
        return msg
    
    # /approve - Admin only: approve payment
    elif cmd == "/approve":
        admin_chat_id = os.environ.get("ADMIN_CHAT_ID", "")
        if str(chat_id) != str(admin_chat_id):
            return "Ban khong co quyen su dung lenh nay."
        
        if len(parts) < 2:
            return "Cu phap: `/approve <payment_id>`\n\nDung `/payments` de xem danh sach."
        
        payment_id = parts[1]
        result = approve_payment(payment_id)
        
        if result["success"]:
            data = result["data"]
            msg = f"*{result['message']}*\n\n"
            msg += f"Chat ID: `{data['chat_id']}`\n"
            msg += f"Goi: {data['plan']}\n"
            msg += f"Thanh toan: {data['price']:,.0f} VND\n"
            msg += f"Het han: {data['expires_at']}"
            return msg
        else:
            return result["message"]
    
    # /run
    elif cmd == "/run":
        # Check subscription
        if not has_active_subscription(chat_id):
            logger.info(f"User {chat_id} tried /run but no active subscription")
            return "*Cần subscription để sử dụng tính năng này.*\n\nDùng `/plans` để xem các gói và `/subscribe` để đăng ký."

        try:
            pf = get_user_portfolio(chat_id)
            capital = pf.get("capital", DEFAULT_CAPITAL)

            logger.info(f"User {chat_id} starting analysis with capital {capital}")
            send_msg(bot_token, chat_id, "Đang chạy phân tích... Chờ 30-60 giây.")

            _ = run_analysis(cfg, capital, chat_id)

            # The analysis itself sends the full report via Telegram.
            # Do not echo stdout/stderr back to user to avoid noisy third-party prints.
            logger.info(f"User {chat_id} analysis complete")
            send_msg(bot_token, chat_id, "Phân tích hoàn tất!")
            return None
        except Exception as e:
            logger.error(f"Error in /run for user {chat_id}: {e}")
            return f" *LOI:* Phân tích thất bại. Vui lòng thử lại sau.\n\nError: `{str(e)}`"
    
    # /update - Admin only: auto-update from GitHub
    elif cmd == "/update":
        admin_chat_id = os.environ.get("ADMIN_CHAT_ID", "")
        if str(chat_id) != str(admin_chat_id):
            return "Ban khong co quyen su dung lenh nay."
        
        send_msg(bot_token, chat_id, " *DANG CAP NHAT...*\n\nVui long doi, bot se khoi dong lai sau khi hoan tat.")
        
        try:
            # Git fetch and reset
            fetch_result = subprocess.run(
                ["git", "fetch", "origin"],
                capture_output=True, text=True, timeout=30,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            reset_result = subprocess.run(
                ["git", "reset", "--hard", "origin/main"],
                capture_output=True, text=True, timeout=30,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            # Get current commit info
            log_result = subprocess.run(
                ["git", "log", "-1", "--oneline"],
                capture_output=True, text=True, timeout=10,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            msg = " *CAP NHAT THANH CONG!*\n\n"
            msg += f"Commit: `{log_result.stdout.strip()}`\n\n"
            msg += "Bot dang khoi dong lai...\n"
            msg += "Neu bot khong phan hoi sau 30 giay, vui long kiem tra log."
            
            # Send message before restart
            send_msg(bot_token, chat_id, msg)
            
            # Restart service (will kill current process)
            subprocess.Popen(
                ["sudo", "systemctl", "restart", "hca-bot"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            return None  # Don't send another message
            
        except subprocess.TimeoutExpired:
            return " *LOI:* Git operation timeout."
        except Exception as e:
            return f" *LOI:* `{str(e)}`"
    
    else:
        return "Lenh khong nhan dang. Go */help* de xem menu."

def send_msg(bot_token, chat_id, text):
    import requests
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except:
        pass

def forward_photo(bot_token, chat_id, file_id):
    """Forward a photo to a chat."""
    import requests
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    payload = {"chat_id": chat_id, "photo": file_id}
    try:
        requests.post(url, json=payload)
    except:
        pass


def send_photo_url(bot_token, chat_id, photo_url, caption=None):
    import requests
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    payload = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        payload["caption"] = caption
        payload["parse_mode"] = "Markdown"
    try:
        requests.post(url, json=payload)
    except:
        pass

if __name__ == "__main__":
    main()
