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

def send_telegram_summary(actions, portfolio):
    import requests
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    
    if not bot_token or not chat_id:
        print("Telegram credentials not set. Skipping Telegram notification.")
        return
        
    text = "🚀 *HCA System Update*\n\n"
    text += f"*Portfolio Cash:* {portfolio['cash']:,.0f} VND\n"
    text += "*Positions:*\n"
    for sym, pos in portfolio['positions'].items():
        text += f"⁃ {sym}: {pos['qty']} @ {pos['avg_price']:,.0f}\n"
        
    text += "\n*Actions for Today:*\n"
    if not actions:
        text += "No recommended actions today.\n"
    else:
        for a in actions:
            text += f"⚡ *{a['action']}* {a['symbol']} - {a.get('reason','')}\n"
            
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Telegram message sent successfully.")
        else:
            print(f"Error sending Telegram message: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

