import argparse
import json
import os
from dotenv import load_dotenv

load_dotenv()

from data_pipeline import fetch_data
from scoring import calculate_multi_factor_score
from ranking import rank_stocks
from execution import execute_logic
from reporting import save_signals_to_json, log_scores_to_csv, send_daily_summary, send_telegram_summary

def main():
    # Load defaults from config.json if exists
    cfg_defaults = {}
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            cfg_defaults = json.load(f)
    
    parser = argparse.ArgumentParser(description="HCA System Main")
    parser.add_argument("--mode", type=str, default="hybrid")
    parser.add_argument("--primary", type=str, default=cfg_defaults.get("primary", "HHV"))
    parser.add_argument("--watchlist", type=str, default=",".join(cfg_defaults.get("watchlist", ["TOS","NKG","AAS"])))
    parser.add_argument("--cap", type=int, default=cfg_defaults.get("capital", 50000000))
    parser.add_argument("--min_score", type=float, default=cfg_defaults.get("min_score", 3.8))
    
    args = parser.parse_args()
    
    watchlist = [t.strip() for t in args.watchlist.split(",")]
    primary = args.primary
    tickers = list(set([primary, "VNINDEX"] + watchlist))
    
    print(f"Starting HCA System in {args.mode} mode...")
    print(f"Primary: {primary} | Watchlist: {watchlist} | Capital: {args.cap:,}")
    
    # AGENT 1: Data Pipeline
    print("Fetching data...")
    data_dict = fetch_data(tickers, period="6mo")
    
    benchmark_df = data_dict.get("VNINDEX")
    if benchmark_df is None or benchmark_df.empty:
        print("Warning: VNINDEX data not found. Some indicators might be inaccurate.")
            
    # AGENT 2: Multi-Factor Scoring
    print("Running Multi-Factor Scoring...")
    scored_data = {}
    current_prices = {}
    for sym, df in data_dict.items():
        if sym == "VNINDEX":
            continue
        if len(df) > 0:
            scored_data[sym] = calculate_multi_factor_score(df, benchmark_df)
            current_prices[sym] = df['Close'].iloc[-1]
            
    # AGENT 3: Ranking & Alpha Detection (Dynamic)
    print("Ranking stocks...")
    scored_data, classification = rank_stocks(scored_data, primary=primary, watchlist=watchlist)
    
    print(f"Classification: {classification}")
    
    # AGENT 4: Execution Logic (Dynamic primary + capital)
    print("Evaluating execution logic...")
    actions, portfolio = execute_logic(scored_data, classification, current_prices, primary=primary, capital=args.cap)
    
    # AGENT 5: Output & Reporting
    print("Saving reporting outputs...")
    save_signals_to_json(actions)
    log_scores_to_csv(scored_data, classification)
    send_daily_summary(actions, portfolio)
    send_telegram_summary(scored_data, classification, actions, portfolio, benchmark_df, current_prices, args.cap)
    
    print("Done!")

if __name__ == "__main__":
    main()
