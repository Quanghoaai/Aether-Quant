import os
import json
import subprocess
import sys
import time
import socket
import requests.packages.urllib3.util.connection as urllib3_cn
from dotenv import load_dotenv

# Force IPv4 to prevent ConnectionResetError on some Linux environments
def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family

load_dotenv()

CONFIG_FILE = "config.json"
PORTFOLIO_FILE = "portfolio.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"primary": "HHV", "watchlist": ["TOS", "NKG", "AAS"], "capital": 50000000, "min_score": 3.8}

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    return {"cash": 50000000, "positions": {}}

def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=4)

def run_analysis(cfg):
    """Run main.py with current config and return output."""
    wl = ",".join(cfg["watchlist"])
    cmd = [
        sys.executable, "main.py",
        "--mode", "hybrid",
        "--primary", cfg["primary"],
        "--watchlist", wl,
        "--cap", str(cfg["capital"]),
        "--min_score", str(cfg["min_score"])
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
    offset = 0
    cfg = load_config()
    
    # Register command menu on Telegram
    commands = [
        {"command": "status", "description": "📊 Xem cấu hình hiện tại"},
        {"command": "run", "description": "🔥 Chạy phân tích ngay lập tức"},
        {"command": "portfolio", "description": "💼 Xem danh mục đầu tư"},
        {"command": "set_primary", "description": "👑 Đổi mã chính (VD: /set_primary HHV)"},
        {"command": "set_watchlist", "description": "📋 Đổi watchlist (VD: /set_watchlist TOS,NKG,AAS)"},
        {"command": "add", "description": "➕ Thêm mã vào watchlist (VD: /add FPT)"},
        {"command": "remove", "description": "➖ Xóa mã khỏi watchlist (VD: /remove NKG)"},
        {"command": "confirm_buy", "description": "✅ Xác nhận mua (VD: /confirm_buy TCB 1000 25500)"},
        {"command": "confirm_sell", "description": "🔴 Xác nhận bán (VD: /confirm_sell TCB 500)"},
        {"command": "set_capital", "description": "💰 Đổi vốn (VD: /set_capital 100000000)"},
        {"command": "set_minscore", "description": "🎯 Đổi điểm (VD: /set_minscore 3.5)"},
        {"command": "help", "description": "❓ Xem hướng dẫn sử dụng"}
    ]
    resp = requests.post(f"{base_url}/setMyCommands", json={"commands": commands})
    if resp.status_code == 200:
        print("Commands menu registered on Telegram!")
    
    print(f"Bot started! Config: primary={cfg['primary']}, watchlist={cfg['watchlist']}")
    print("Waiting for Telegram commands...")
    
    while True:
        try:
            resp = requests.get(f"{base_url}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
            updates = resp.json().get("result", [])
            
            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "").strip()
                
                if not chat_id or not text:
                    continue
                
                reply = handle_command(text, cfg, chat_id, bot_token)
                if reply:
                    send_msg(bot_token, chat_id, reply)
                    
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

def handle_command(text, cfg, chat_id, bot_token):
    """Process a command and return reply text."""
    
    parts = text.split()
    cmd = parts[0].lower() if parts else ""
    
    # /start or /help
    if cmd in ["/start", "/help"]:
        return (
            "🚀 *Aether-Quant HCA Bot*\n\n"
            "📌 */status* — Xem cấu hình\n"
            "📌 */portfolio* — Xem danh mục & PnL\n"
            "📌 */run* — Chạy phân tích ngay\n"
            "📌 */set\\_primary MÃ* — Đổi mã chính\n"
            "📌 */set\\_watchlist MÃ1,MÃ2* — Đổi watchlist\n"
            "📌 */add MÃ* / */remove MÃ* — Thêm/Xóa mã\n"
            "📌 */confirm\\_buy MÃ SỐ\\_CP GIÁ* — Xác nhận mua\n"
            "📌 */confirm\\_sell MÃ SỐ\\_CP* — Xác nhận bán\n"
            "📌 */set\\_capital SỐ* — Đổi vốn\n"
            "📌 */set\\_minscore SỐ* — Đổi điểm\n"
        )
    
    # /status
    elif cmd == "/status":
        wl = ", ".join(cfg["watchlist"])
        return (
            "📊 *Cấu hình hiện tại*\n\n"
            f"👑 Mã chính: *{cfg['primary']}*\n"
            f"📋 Watchlist: *{wl}*\n"
            f"💰 Vốn: *{cfg['capital']:,.0f}* VND\n"
            f"🎯 Min Score: *{cfg['min_score']}*\n"
        )
    
    # /portfolio
    elif cmd == "/portfolio":
        pf = load_portfolio()
        capital = cfg.get("capital", 50000000)
        cash_pct = (pf['cash'] / capital) * 100 if capital > 0 else 0
        
        text = "💼 *DANH MỤC ĐẦU TƯ*\n"
        text += "─────────────────\n"
        text += f"💰 Tiền mặt: *{pf['cash']:,.0f}* VND ({cash_pct:.0f}%)\n\n"
        
        if not pf['positions']:
            text += "📌 Chưa có vị thế nào.\n"
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
            return "⚠️ Cú pháp: `/confirm_buy MÃ SỐ_CP GIÁ`\nVD: `/confirm_buy TCB 1000 25500`"
        sym = parts[1].upper()
        try:
            qty = int(parts[2])
            price = float(parts[3])
        except ValueError:
            return "⚠️ Số lượng hoặc giá không hợp lệ."
        
        pf = load_portfolio()
        cost = qty * price
        
        if cost > pf['cash']:
            return f"⚠️ Không đủ tiền mặt! Cần {cost:,.0f} nhưng chỉ có {pf['cash']:,.0f}"
        
        # Check cash reserve
        min_reserve = cfg.get("capital", 50000000) * 0.20
        if pf['cash'] - cost < min_reserve:
            return f"⚠️ Vi phạm quy tắc giữ 20% tiền mặt! Sau khi mua chỉ còn {pf['cash']-cost:,.0f} < {min_reserve:,.0f}"
        
        if sym in pf['positions']:
            old = pf['positions'][sym]
            total_qty = old['qty'] + qty
            avg_price = (old['avg_price'] * old['qty'] + price * qty) / total_qty
            pf['positions'][sym] = {"qty": total_qty, "avg_price": round(avg_price, 0), "highest_price": max(old.get("highest_price", price), price)}
        else:
            pf['positions'][sym] = {"qty": qty, "avg_price": price, "highest_price": price}
        
        pf['cash'] -= cost
        save_portfolio(pf)
        
        return (
            f"✅ *ĐÃ MUA {sym}*\n"
            f"KL: {qty:,} cp @ {price:,.0f}\n"
            f"Chi phí: {cost:,.0f} VND\n"
            f"Tiền mặt còn: {pf['cash']:,.0f} VND"
        )
    
    # /confirm_sell SYMBOL QTY
    elif cmd == "/confirm_sell":
        if len(parts) < 3:
            return "⚠️ Cú pháp: `/confirm_sell MÃ SỐ_CP`\nVD: `/confirm_sell TCB 500`"
        sym = parts[1].upper()
        try:
            qty = int(parts[2])
        except ValueError:
            return "⚠️ Số lượng không hợp lệ."
        
        pf = load_portfolio()
        
        if sym not in pf['positions']:
            return f"⚠️ Không có vị thế *{sym}* trong danh mục."
        
        pos = pf['positions'][sym]
        if qty > pos['qty']:
            return f"⚠️ Chỉ có {pos['qty']:,} cp {sym}, không thể bán {qty:,} cp."
        
        # Use avg_price as estimated sell price (user can input 4th param for actual price)
        sell_price = float(parts[3]) if len(parts) >= 4 else pos['avg_price']
        revenue = qty * sell_price
        pnl = (sell_price - pos['avg_price']) * qty
        
        pos['qty'] -= qty
        if pos['qty'] <= 0:
            del pf['positions'][sym]
        else:
            pf['positions'][sym] = pos
        
        pf['cash'] += revenue
        save_portfolio(pf)
        
        return (
            f"🔴 *ĐÃ BÁN {sym}*\n"
            f"KL: {qty:,} cp @ {sell_price:,.0f}\n"
            f"Thu về: {revenue:,.0f} VND\n"
            f"PnL: {pnl:+,.0f} VND\n"
            f"Tiền mặt: {pf['cash']:,.0f} VND"
        )
    
    # /set_primary
    elif cmd == "/set_primary":
        if len(parts) < 2:
            return "⚠️ Thiếu mã. VD: `/set_primary HHV`"
        new_primary = parts[1].upper()
        cfg["primary"] = new_primary
        save_config(cfg)
        return f"✅ Đã đổi mã chính → *{new_primary}*"
    
    # /set_watchlist
    elif cmd == "/set_watchlist":
        if len(parts) < 2:
            return "⚠️ Thiếu danh sách. VD: `/set_watchlist TOS,NKG,AAS`"
        wl = [s.strip().upper() for s in parts[1].split(",") if s.strip()]
        cfg["watchlist"] = wl
        save_config(cfg)
        return f"✅ Đã đổi Watchlist → *{', '.join(wl)}*"
    
    # /add
    elif cmd == "/add":
        if len(parts) < 2:
            return "⚠️ Thiếu mã. VD: `/add VNM`"
        sym = parts[1].upper()
        if sym not in cfg["watchlist"]:
            cfg["watchlist"].append(sym)
            save_config(cfg)
            return f"✅ Đã thêm *{sym}* → Watchlist: *{', '.join(cfg['watchlist'])}*"
        return f"⚠️ *{sym}* đã có trong Watchlist rồi."
    
    # /remove
    elif cmd == "/remove":
        if len(parts) < 2:
            return "⚠️ Thiếu mã. VD: `/remove NKG`"
        sym = parts[1].upper()
        if sym in cfg["watchlist"]:
            cfg["watchlist"].remove(sym)
            save_config(cfg)
            return f"✅ Đã xóa *{sym}* → Watchlist: *{', '.join(cfg['watchlist'])}*"
        return f"⚠️ *{sym}* không có trong Watchlist."
    
    # /set_capital
    elif cmd == "/set_capital":
        if len(parts) < 2:
            return "⚠️ Thiếu số vốn. VD: `/set_capital 100000000`"
        try:
            cap = int(parts[1])
            cfg["capital"] = cap
            save_config(cfg)
            return f"✅ Đã đổi vốn → *{cap:,.0f}* VND"
        except ValueError:
            return "⚠️ Số vốn không hợp lệ."
    
    # /set_minscore
    elif cmd == "/set_minscore":
        if len(parts) < 2:
            return "⚠️ Thiếu điểm. VD: `/set_minscore 3.5`"
        try:
            ms = float(parts[1])
            cfg["min_score"] = ms
            save_config(cfg)
            return f"✅ Đã đổi Min Score → *{ms}*"
        except ValueError:
            return "⚠️ Số điểm không hợp lệ."
    
    # /run
    elif cmd == "/run":
        send_msg(bot_token, chat_id, "⏳ Đang chạy phân tích... Chờ 30-60 giây.")
        output = run_analysis(cfg)
        # The analysis itself sends the full report via Telegram
        lines = output.strip().split('\n')
        summary = '\n'.join(lines[-5:]) if len(lines) > 5 else output
        return f"✅ Phân tích hoàn tất!\n\n```\n{summary}\n```"
    
    else:
        return "❓ Lệnh không nhận dạng. Gõ */help* để xem menu."

def send_msg(bot_token, chat_id, text):
    import requests
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except:
        pass

if __name__ == "__main__":
    main()
