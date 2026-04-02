import json
import os

PORTFOLIO_FILE = "portfolio.json"

def load_portfolio(capital=50000000):
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    return {
        "cash": capital,
        "positions": {}
    }

def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=4)

def execute_logic(scored_data, classification, current_prices, primary="HHV", capital=50000000):
    portfolio = load_portfolio(capital)
    actions = []
    
    # ===== RISK CONTROLS on existing positions =====
    for sym, pos in list(portfolio["positions"].items()):
        current_p = current_prices.get(sym)
        if not current_p: continue
        
        avg_p = pos["avg_price"]
        highest_p = max(pos.get("highest_price", avg_p), current_p)
        portfolio["positions"][sym]["highest_price"] = highest_p
        
        profit_pct = (current_p - avg_p) / avg_p
        drawdown_from_high = (highest_p - current_p) / highest_p if highest_p > 0 else 0
        
        # Hard Stop -7%
        if profit_pct <= -0.07:
            actions.append({"symbol": sym, "action": "SELL", "reason": "Hard Stop -7%", "qty": pos["qty"]})
            portfolio["cash"] += pos["qty"] * current_p
            del portfolio["positions"][sym]
            
        # Trailing Stop (profit ≥8% but dropped 3% from high)
        elif profit_pct >= 0.08 and drawdown_from_high >= 0.03:
            actions.append({"symbol": sym, "action": "SELL", "reason": "Trailing Stop", "qty": pos["qty"]})
            portfolio["cash"] += pos["qty"] * current_p
            del portfolio["positions"][sym]
            
        # Take Profit Level 2: +15-18% → sell all
        elif profit_pct >= 0.15:
            actions.append({"symbol": sym, "action": "SELL", "reason": "Take Profit Level 2 (+15%)", "qty": pos["qty"]})
            portfolio["cash"] += pos["qty"] * current_p
            del portfolio["positions"][sym]
            
        # Take Profit Level 1: +10% → sell half
        elif profit_pct >= 0.10 and not pos.get("tp_level_1_hit"):
            sell_qty = pos["qty"] // 2
            if sell_qty > 0:
                actions.append({"symbol": sym, "action": "SELL_HALF", "reason": "Take Profit Level 1 (+10%)", "qty": sell_qty})
                portfolio["positions"][sym]["qty"] -= sell_qty
                portfolio["positions"][sym]["tp_level_1_hit"] = True
                portfolio["cash"] += sell_qty * current_p
            
    # ===== PRIMARY Health Check (Dynamic) =====
    primary_data = scored_data.get(primary, {})
    primary_score = primary_data.get("score", 0)
    primary_rs = primary_data.get("RS_score", 0)
    primary_pa = primary_data.get("Price_Action_score", 0)
    
    primary_weak = primary_score < 3.5 or primary_pa < 2.5 or primary_rs < 2.5
    
    if primary in portfolio["positions"] and primary_weak:
        actions.append({"symbol": primary, "action": "REDUCE", "reason": f"{primary} Health Check Failed. Weak Trend."})
        
    # Find ALPHA candidate
    alpha_sym = None
    for sym, cls in classification.items():
        if cls == "ALPHA":
            alpha_sym = sym
            
    # ===== Alpha Swap (Rotation Rule) =====
    if alpha_sym and primary_weak:
        alpha_score = scored_data.get(alpha_sym, {}).get("score", 0)
        if alpha_score > primary_score + 0.5:
            actions.append({"symbol": primary, "action": "ROTATE_TO_ALPHA", "target": alpha_sym, "reason": f"Alpha Swap: {alpha_sym} score {alpha_score:.1f} > {primary} score {primary_score:.1f}"})

    # ===== BUY Rules with Cash Reserve Enforcement =====
    min_cash_reserve = capital * 0.20  # Always keep 20% cash
    
    buy_candidates = []
    if primary not in portfolio["positions"] and not primary_weak and primary_score >= 3.8:
        buy_candidates.append(primary)
    if alpha_sym and alpha_sym not in portfolio["positions"]:
        alpha_s = scored_data.get(alpha_sym, {}).get("score", 0)
        if alpha_s >= 3.8:
            buy_candidates.append(alpha_sym)
        
    for sym, cls in classification.items():
        if cls == "SECONDARY" and scored_data.get(sym, {}).get("score", 0) >= 3.8:
            if sym not in portfolio["positions"] and sym not in buy_candidates:
                buy_candidates.append(sym)
                
    available_slots = 3 - len(portfolio["positions"])
    for sym in buy_candidates:
        if available_slots <= 0: break
        
        usable_cash = portfolio["cash"] - min_cash_reserve
        if usable_cash < 5000000:  # Not enough after reserve
            break
            
        invest_amount = min(usable_cash, usable_cash / max(available_slots, 1))
        price = current_prices.get(sym)
        if price and price > 0:
            qty = int(invest_amount // (price * 1000)) * 1000 // int(price) if price < 100 else int(invest_amount // price)
            # Round to lot size (100 shares for VN market)
            qty = (qty // 100) * 100
            if qty >= 100:
                actual_cost = qty * price
                actions.append({
                    "symbol": sym, 
                    "action": "BUY", 
                    "amount": actual_cost, 
                    "reason": "New Position", 
                    "qty": qty,
                    "price": price
                })
                # Update portfolio immediately
                portfolio["positions"][sym] = {
                    "qty": qty,
                    "avg_price": price,
                    "highest_price": price
                }
                portfolio["cash"] -= actual_cost
                available_slots -= 1
    
    # ===== SAVE portfolio after all actions =====
    save_portfolio(portfolio)
    
    return actions, portfolio
