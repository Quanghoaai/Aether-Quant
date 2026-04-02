import argparse
from dotenv import load_dotenv

load_dotenv()

from data_pipeline import fetch_data
from scoring import calculate_multi_factor_score
from ranking import rank_stocks
from execution import execute_logic
from reporting import save_signals_to_json, log_scores_to_csv, send_daily_summary, send_telegram_summary

def main():
    parser = argparse.ArgumentParser(description="HCA System Main")
    parser.add_argument("--mode", type=str, default="hybrid")
    parser.add_argument("--primary", type=str, default="HHV")
    parser.add_argument("--watchlist", type=str, default="TOS,NKG,AAS")
    parser.add_argument("--cap", type=int, default=50000000)
    parser.add_argument("--min_score", type=float, default=3.8)
    
    args = parser.parse_args()
    
    watchlist = [t.strip() for t in args.watchlist.split(",")]
    primary = args.primary
    tickers = [primary, "VNINDEX"] + watchlist
    
    print(f"Starting HCA System in {args.mode} mode...")
    
    # AGENT 1: Data Pipeline
    print("Fetching data...")
    # Fetch data (Using 6mo period to ensure enough data for 50MA)
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
            
    # AGENT 3: Ranking & Alpha Detection
    print("Ranking stocks...")
    scored_data, classification = rank_stocks(scored_data)
    
    # Filter by min_score rule where applicable
    for sym, score_info in list(scored_data.items()):
        pass # The rule keep if score >= 3.8 is handled in execution logic
        
    print(f"Classification: {classification}")
    
    # AGENT 4: Execution Logic
    print("Evaluating execution logic...")
    actions, portfolio = execute_logic(scored_data, classification, current_prices)
    
    # AGENT 5: Output & Reporting
    print("Saving reporting outputs...")
    save_signals_to_json(actions)
    log_scores_to_csv(scored_data, classification)
    send_daily_summary(actions, portfolio)
    send_telegram_summary(actions, portfolio, scored_data, classification, current_prices)
    
    print("Done!")

if __name__ == "__main__":
    main()
