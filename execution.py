import json
import os

PORTFOLIO_FILE = "portfolio.json"

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    return {
        "cash": 50000000,
        "positions": {}
    }

def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=4)

def execute_logic(scored_data, classification, current_prices):
    portfolio = load_portfolio()
    actions = []
    
    # Check current positions for Risk Controls
    for sym, pos in list(portfolio["positions"].items()):
        current_p = current_prices.get(sym)
        if not current_p: continue
        
        avg_p = pos["avg_price"]
        highest_p = max(pos.get("highest_price", avg_p), current_p)
        portfolio["positions"][sym]["highest_price"] = highest_p
        
        profit_pct = (current_p - avg_p) / avg_p
        drawdown_from_high = (highest_p - current_p) / highest_p if highest_p > 0 else 0
        
        # Risk Control Rules
        if profit_pct <= -0.07:
            actions.append({"symbol": sym, "action": "SELL", "reason": "Hard Stop -7%", "qty": pos["qty"]})
        elif profit_pct >= 0.08 and drawdown_from_high >= 0.03:
            actions.append({"symbol": sym, "action": "SELL", "reason": "Trailing Stop", "qty": pos["qty"]})
        elif profit_pct >= 0.15:
            actions.append({"symbol": sym, "action": "SELL", "reason": "Take Profit Level 2", "qty": pos["qty"]})
        elif profit_pct >= 0.10 and not pos.get("tp_level_1_hit"):
            actions.append({"symbol": sym, "action": "SELL_HALF", "reason": "Take Profit Level 1", "qty": pos["qty"] // 2})
            portfolio["positions"][sym]["tp_level_1_hit"] = True
            
    # Priority handling: HHV Health Check
    hhv_sym = "HHV"
    hhv_data = scored_data.get(hhv_sym, {})
    hhv_score = hhv_data.get("score", 0)
    hhv_rs_score = hhv_data.get("RS_score", 0)
    hhv_pa = hhv_data.get("Price_Action_score", 0)
    
    hhv_weak = hhv_score < 3.5 or hhv_pa < 2.5 or hhv_rs_score < 2.5
    
    if hhv_sym in portfolio["positions"] and hhv_weak:
        actions.append({"symbol": hhv_sym, "action": "REDUCE", "reason": "HHV Health Check Failed. Weak Trend."})
        
    alpha_sym = None
    for sym, cls in classification.items():
        if cls == "ALPHA":
            alpha_sym = sym
            
    # Rotation Rule (Alpha Swap)
    if alpha_sym and hhv_weak:
        alpha_score = scored_data.get(alpha_sym, {}).get("score", 0)
        if alpha_score > hhv_score + 0.5:
            actions.append({"symbol": hhv_sym, "action": "ROTATE_TO_ALPHA", "target": alpha_sym, "reason": "Alpha Swap Rule"})

    # Diversification (Buy Rules)
    buy_candidates = []
    if hhv_sym not in portfolio["positions"] and not hhv_weak and hhv_score >= 3.8:
        buy_candidates.append(hhv_sym)
    if alpha_sym and alpha_sym not in portfolio["positions"]:
        buy_candidates.append(alpha_sym)
        
    for sym, cls in classification.items():
        if cls == "SECONDARY" and scored_data.get(sym, {}).get("score", 0) >= 3.8:
            if sym not in portfolio["positions"] and sym not in buy_candidates:
                buy_candidates.append(sym)
                
    available_slots = 3 - len(portfolio["positions"])
    for sym in buy_candidates:
        if available_slots <= 0: break
        if portfolio["cash"] > 10000000:
            invest_amount = min(portfolio["cash"], portfolio["cash"] / available_slots)
            # Find price to get qty
            price = current_prices.get(sym)
            if price and price > 0:
                qty = int(invest_amount // price)
                if qty > 0:
                    actions.append({"symbol": sym, "action": "BUY", "amount": invest_amount, "reason": "New Position", "qty": qty})
                    available_slots -= 1
                    
    # We could simulate updating the portfolio based on actions here, but in a semi-automated system
    # the user might execute them manually and update the portfolio file.
    # For now, we will just return the generated actions.
    
    return actions, portfolio
