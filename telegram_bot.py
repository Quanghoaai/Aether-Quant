import os
import json
import subprocess
import sys
from dotenv import load_dotenv

load_dotenv()

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"primary": "HHV", "watchlist": ["TOS", "NKG", "AAS"], "capital": 50000000, "min_score": 3.8}

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)

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
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.stdout + result.stderr
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
            import time
            time.sleep(5)

def handle_command(text, cfg, chat_id, bot_token):
    """Process a command and return reply text."""
    
    parts = text.split()
    cmd = parts[0].lower() if parts else ""
    
    # /start or /help
    if cmd in ["/start", "/help"]:
        return (
            "🚀 *Aether-Quant HCA Bot*\n\n"
            "Lệnh có sẵn:\n\n"
            "📌 */status* — Xem cấu hình hiện tại\n"
            "📌 */set\\_primary MÃ* — Đổi mã chính\n"
            "   VD: `/set_primary HHV`\n"
            "📌 */set\\_watchlist MÃ1,MÃ2,...* — Đổi watchlist\n"
            "   VD: `/set_watchlist TOS,NKG,AAS`\n"
            "📌 */set\\_capital SỐ* — Đổi vốn\n"
            "   VD: `/set_capital 100000000`\n"
            "📌 */set\\_minscore SỐ* — Đổi điểm tối thiểu\n"
            "   VD: `/set_minscore 3.5`\n"
            "📌 */run* — Chạy phân tích ngay\n"
            "📌 */add MÃ* — Thêm mã vào watchlist\n"
            "📌 */remove MÃ* — Xóa mã khỏi watchlist\n"
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
            return f"✅ Đã thêm *{sym}* vào Watchlist → *{', '.join(cfg['watchlist'])}*"
        return f"⚠️ *{sym}* đã có trong Watchlist rồi."
    
    # /remove
    elif cmd == "/remove":
        if len(parts) < 2:
            return "⚠️ Thiếu mã. VD: `/remove NKG`"
        sym = parts[1].upper()
        if sym in cfg["watchlist"]:
            cfg["watchlist"].remove(sym)
            save_config(cfg)
            return f"✅ Đã xóa *{sym}* khỏi Watchlist → *{', '.join(cfg['watchlist'])}*"
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
        send_msg(os.environ.get("TELEGRAM_BOT_TOKEN", ""), 
                 os.environ.get("TELEGRAM_CHAT_ID", ""), 
                 "⏳ Đang chạy phân tích... Vui lòng chờ 30-60 giây.")
        output = run_analysis(cfg)
        # The analysis itself will send the full Telegram report
        return f"✅ Phân tích hoàn tất!\n\n```\n{output[-500:]}\n```"
    
    else:
        return "❓ Lệnh không nhận dạng được. Gõ */help* để xem danh sách lệnh."

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
