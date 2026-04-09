import json
import csv
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime

def save_signals_to_json(actions, filename="execution_log.json"):
    with open(filename, "w") as f:
        json.dump(actions, f, indent=4)

def log_scores_to_csv(scored_data, classification, filename="history.csv"):
    file_exists = os.path.isfile(filename)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    with open(filename, "a", newline='') as csvfile:
        fieldnames = ["Date", "Symbol", "Score", "RankScore", "Classification"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
            
        for sym, data in scored_data.items():
            writer.writerow({
                "Date": today,
                "Symbol": sym,
                "Score": data.get("score"),
                "RankScore": data.get("rank_score"),
                "Classification": classification.get(sym, "N/A")
            })

def send_daily_summary(actions, portfolio):
    sender_email = os.environ.get("EMAIL_USER", "")
    receiver_email = os.environ.get("EMAIL_RECEIVER", "")
    password = os.environ.get("EMAIL_PASS", "")
    
    if not sender_email or not receiver_email:
        print("Email credentials not set. Skipping email.")
        return
        
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Daily HCA System Actions - {datetime.datetime.now().strftime('%Y-%m-%d')}"
    msg["From"] = sender_email
    msg["To"] = receiver_email
    
    text = "HCA System Update\n\n"
    text += f"Portfolio Cash: {portfolio['cash']} VND\n"
    text += f"Positions: {json.dumps(portfolio['positions'], indent=2)}\n\n"
    text += "Actions for Today:\n"
    if not actions:
        text += "No recommended actions today.\n"
    else:
        for a in actions:
            text += str(a) + "\n"
        
    part1 = MIMEText(text, "plain")
    msg.attach(part1)
    
    try:
        if password:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
            server.quit()
            print("Email sent successfully.")
        else:
            print("No email password provided, skipping email sending.")
    except Exception as e:
        print(f"Error sending email: {e}")

def _detect_market_regime(benchmark_df):
    """Detect VNINDEX regime: Uptrend / Sideway / Downtrend."""
    if benchmark_df is None or benchmark_df.empty or len(benchmark_df) < 50:
        return "⚠️ Thiếu dữ liệu VNINDEX"
    
    close = benchmark_df['Close'].iloc[-1]
    ma20 = benchmark_df['MA20'].iloc[-1]
    ma50 = benchmark_df['MA50'].iloc[-1]
    ret_5d = benchmark_df['Close'].pct_change(5).iloc[-1]
    ret_20d = benchmark_df['Close'].pct_change(20).iloc[-1]
    
    if close > ma20 and close > ma50 and ma20 > ma50:
        regime = "🟢 UPTREND"
        detail = "Giá > MA20 > MA50. Xu hướng tăng rõ ràng."
    elif close < ma20 and close < ma50 and ma20 < ma50:
        regime = "🔴 DOWNTREND"
        detail = "Giá < MA20 < MA50. Xu hướng giảm, ưu tiên phòng thủ."
    else:
        regime = "🟡 SIDEWAY"
        detail = "Giá dao động quanh MA20/MA50. Thị trường chưa rõ xu hướng."
        
    vnindex_price = f"{close:,.0f}"
    return f"{regime}\nVNINDEX: {vnindex_price} | 5D: {ret_5d:+.1%} | 20D: {ret_20d:+.1%}\n{detail}"

def _format_score_bar(score, max_score=5):
    """Create a visual score bar."""
    filled = int(round(score))
    empty = max_score - filled
    return "█" * filled + "░" * empty + f" {score:.1f}/5"

def _get_action_label(sym, actions, classification):
    """Determine BUY/HOLD/SELL/ROTATE for a symbol."""
    action_map = {}
    for a in actions:
        action_map[a['symbol']] = a['action']
    
    if sym in action_map:
        act = action_map[sym]
        if act in ["SELL", "SELL_HALF"]:
            return "🔴 SELL"
        elif act == "BUY":
            return "🟢 BUY"
        elif "ROTATE" in act:
            return "🔄 ROTATE"
        elif act == "REDUCE":
            return "🟠 REDUCE"
        return f"⚡ {act}"
    
    cls = classification.get(sym, "")
    if cls == "PRIMARY":
        return "🔵 HOLD (Core)"
    return "⚪ HOLD"

def _calc_entry_sl_tp(current_price):
    """Calculate entry/stoploss/take-profit levels."""
    if not current_price or current_price <= 0:
        return "N/A", "N/A", "N/A", "N/A"
    sl = current_price * 0.93  # -7%
    tp1 = current_price * 1.10  # +10%
    tp2 = current_price * 1.17  # +17%
    return f"{current_price:,.0f}", f"{sl:,.0f}", f"{tp1:,.0f}", f"{tp2:,.0f}"

def build_full_report(scored_data, classification, actions, portfolio, benchmark_df, current_prices, capital=50000000):
    """Build professional fund-style analysis report."""
    today = datetime.datetime.now().strftime("%d/%m/%Y")
    
    # === HEADER ===
    report = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    report += f" *HCA SYSTEM — BÁO CÁO NGÀY {today}*\n"
    report += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # === DISCLAIMER ===
    report += "??  y l  ph n t ch t  d  n AI Trading c  nh n. "
    report += "S  d ng Python + VNStock API. Kh ng ph i l i khuy n  u t .\n\n"
    
    # === SUMMARY RECOMMENDATIONS ===
    # Sort by rank_score to get top picks
    sorted_symbols = sorted(scored_data.items(), key=lambda x: x[1].get('rank_score', 0), reverse=True)
    
    # Get actions summary
    buy_signals = [a for a in actions if a['action'] == 'BUY']
    sell_signals = [a for a in actions if a['action'] in ['SELL', 'SELL_HALF']]
    hold_count = len([s for s, d in sorted_symbols if d.get('score', 0) >= 3.0]) - len(buy_signals) - len(sell_signals)
    
    report += "?? *T M T T KHUY N NGH *\n"
    report += "?????????????????????\n\n"
    
    # Top 3 recommendations
    top_3 = sorted_symbols[:3]
    for i, (sym, data) in enumerate(top_3, 1):
        score = data.get('score', 0)
        cp = current_prices.get(sym, 0)
        entry, sl, tp1, tp2 = _calc_entry_sl_tp(cp)
        cls = classification.get(sym, "")
        
        # Determine action
        if score >= 3.8:
            action = "?? MUA"
        elif score >= 3.5:
            action = "?? GI "
        else:
            action = "?? B N"
        
        role = "?? CORE" if cls == "PRIMARY" else "?? ALPHA" if cls == "ALPHA" else ""
        report += f"*{i}. {sym}* {role}\n"
        report += f"   {action} | Score: {score:.1f}/5\n"
        report += f"   ?? Entry: {entry}\n"
        report += f"   ?? TP1: {tp1} | TP2: {tp2} | TP3: {int(tp2 * 1.1)}\n"
        report += f"   ?? SL: {sl}\n\n"
    
    # Quick stats
    report += f"?? T ng: {len(buy_signals)} MUA | {hold_count} GI  | {len(sell_signals)} B N\n\n"
    
    # === 1. MARKET REGIME ===
    report += " *1. MARKET REGIME*\n"
    report += _detect_market_regime(benchmark_df) + "\n\n"
    
    # === 2. PORTFOLIO STATUS ===
    cash_pct = (portfolio['cash'] / capital) * 100
    report += "💰 *2. TRẠNG THÁI DANH MỤC*\n"
    report += f"Vốn: {capital:,.0f} VND\n"
    report += f"Tiền mặt: {portfolio['cash']:,.0f} VND ({cash_pct:.0f}%)\n"
    if portfolio['positions']:
        for sym, pos in portfolio['positions'].items():
            cp = current_prices.get(sym, pos['avg_price'])
            pnl = ((cp - pos['avg_price']) / pos['avg_price']) * 100 if pos['avg_price'] > 0 else 0
            report += f"📌 {sym}: {pos['qty']} cp @ {pos['avg_price']:,.0f} → {cp:,.0f} ({pnl:+.1f}%)\n"
    else:
        report += "📌 Chưa có vị thế nào.\n"
    report += "\n"
    
    # === 3. MULTI-FACTOR SCORING ===
    report += "📈 *3. CHẤM ĐIỂM ĐA NHÂN TỐ (0-5)*\n"
    report += "─────────────────────────────\n"
    
    # Sort by rank_score descending
    sorted_symbols = sorted(scored_data.items(), key=lambda x: x[1].get('rank_score', 0), reverse=True)
    
    primary_sym = None
    secondary_syms = []
    
    for sym, data in sorted_symbols:
        score = data.get('score', 0)
        rank = data.get('rank_score', 0)
        rs = data.get('RS_score', 0)
        pa = data.get('Price_Action_score', 0)
        vol = data.get('Volume_Profile_score', 0)
        vty = data.get('Volatility_score', 0)
        sf = data.get('Sector_Flow_score', 0)
        cls = classification.get(sym, "")
        action_label = _get_action_label(sym, actions, classification)
        
        role_tag = ""
        if cls == "PRIMARY":
            role_tag = " 👑 CORE"
            primary_sym = sym
        elif cls == "ALPHA":
            role_tag = " ⚡ ALPHA"
            if not primary_sym:
                primary_sym = sym
            else:
                secondary_syms.append(sym)
        elif cls == "SECONDARY":
            secondary_syms.append(sym)
        
        report += f"\n*{sym}*{role_tag} → {action_label}\n"
        report += f"  Tổng: {_format_score_bar(score)} (Rank: {rank:.2f})\n"
        report += f"  RS:      {_format_score_bar(rs)}\n"
        report += f"  PA:      {_format_score_bar(pa)}\n"
        report += f"  Vol:     {_format_score_bar(vol)}\n"
        report += f"  ATR:     {_format_score_bar(vty)}\n"
        report += f"  Sector:  {_format_score_bar(sf)}\n"
        
        # Entry/SL/TP
        cp = current_prices.get(sym, 0)
        entry, sl, tp1, tp2 = _calc_entry_sl_tp(cp)
        report += f"  💲 Entry: {entry} | SL(-7%): {sl}\n"
        report += f"  🎯 TP1(+10%): {tp1} | TP2(+17%): {tp2}\n"
    
    report += "\n"
    
    # === 4. EXECUTION DECISIONS ===
    report += "🎯 *4. QUYẾT ĐỊNH HÔM NAY*\n"
    report += "─────────────────────────────\n"
    if primary_sym:
        report += f"PRIMARY: *{primary_sym}*\n"
    if secondary_syms:
        report += f"SECONDARY: {', '.join(secondary_syms)}\n"
    report += "\n"
    
    if not actions:
        report += "✅ Không có tín hiệu giao dịch. HOLD toàn bộ.\n"
    else:
        for a in actions:
            sym = a['symbol']
            act = a['action']
            reason = a.get('reason', '')
            qty = a.get('qty', '')
            amt = a.get('amount', '')
            
            if act == "BUY":
                cp = current_prices.get(sym, 0)
                entry, sl, tp1, tp2 = _calc_entry_sl_tp(cp)
                report += f"🟢 *BUY {sym}*\n"
                report += f"  Entry: {entry} | SL: {sl}\n"
                report += f"  TP1: {tp1} (bán 50%) | TP2: {tp2} (bán hết)\n"
                if qty:
                    report += f"  KL: {qty:,} cp\n" if isinstance(qty, int) else f"  KL: {qty} cp\n"
                report += f"  Lý do: {reason}\n"
            elif act in ["SELL", "SELL_HALF"]:
                report += f"🔴 *{act} {sym}*\n"
                if qty:
                    report += f"  KL: {qty:,} cp\n" if isinstance(qty, int) else f"  KL: {qty} cp\n"
                report += f"  Lý do: {reason}\n"
            elif "ROTATE" in act:
                target = a.get('target', '?')
                report += f"🔄 *ROTATE {sym} → {target}*\n"
                report += f"  Lý do: {reason}\n"
            else:
                report += f"⚡ *{act} {sym}* — {reason}\n"
    
    report += "\n"
    
    # === 5. RISK MANAGEMENT ===
    report += "⚠️ *5. QUẢN TRỊ RỦI RO*\n"
    report += "─────────────────────────────\n"
    report += "• Risk/lệnh: 1% vốn (500K VND)\n"
    report += "• Stoploss cứng: -7%\n"
    report += "• TP1 +10%: bán 50% | TP2 +17%: bán hết\n"
    report += "• Giữ 20-30% tiền mặt\n"
    report += "• Max 3 vị thế đồng thời\n\n"
    
    # HHV specific check
    hhv_data = scored_data.get("HHV", {})
    hhv_score = hhv_data.get('score', 0)
    if hhv_score < 3.5:
        report += "⛔ *HHV đang YẾU* (Score < 3.5). Xem xét ROTATE sang ALPHA nếu có.\n"
    elif hhv_score < 3.8:
        report += "⚠️ *HHV chưa đủ mạnh* (Score < 3.8). Theo dõi thêm, chưa nên BUY mới.\n"
    else:
        report += "✅ *HHV khỏe mạnh.* Giữ vị thế hoặc BUY nếu chưa có.\n"
    
    report += "\n"
    
    # === 6. BIGGEST RISK ===
    report += "🔥 *6. RỦI RO LỚN NHẤT HÔM NAY*\n"
    report += "─────────────────────────────\n"
    
    # Detect market regime risk
    if benchmark_df is not None and not benchmark_df.empty:
        close = benchmark_df['Close'].iloc[-1]
        ma50 = benchmark_df['MA50'].iloc[-1] if 'MA50' in benchmark_df.columns else close
        if close < ma50:
            report += "VNINDEX dưới MA50. Rủi ro hệ thống cao. Hạn chế mở vị thế mới.\n"
        else:
            report += "Thị trường chung ổn định. Rủi ro chính là tin vi mô từng mã.\n"
    
    report += "\n"
    
    # === FOOTER ===
    report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    report += f"_Hệ thống HCA v1.0 — Trích xuất từ VNStock API_\n"
    report += f"_Cập nhật: {datetime.datetime.now().strftime('%H:%M %d/%m/%Y')}_"
    
    return report

def send_telegram_summary(scored_data, classification, actions, portfolio, benchmark_df, current_prices, capital=50000000, chat_id=None):
    import requests
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")

    # Use provided chat_id or fallback to env variable
    target_chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")

    if not bot_token or not target_chat_id:
        print("Telegram credentials not set. Skipping Telegram notification.")
        return

    report = build_full_report(scored_data, classification, actions, portfolio, benchmark_df, current_prices, capital)

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": target_chat_id,
        "text": report,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"Telegram message sent successfully to chat_id={target_chat_id}.")
        else:
            print(f"Error sending Telegram message: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
