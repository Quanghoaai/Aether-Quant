import json
import os
import logging

from constants import (
    DEFAULT_CAPITAL, MIN_CASH_RESERVE_PCT, MAX_POSITIONS, MIN_SCORE_BUY,
    HARD_STOP_PCT, TRAILING_STOP_TRIGGER_PCT, TRAILING_STOP_PCT,
    TP1_PCT, TP2_PCT, LOT_SIZE
)

logger = logging.getLogger(__name__)

PORTFOLIO_FILE = "portfolio.json"

def load_all_portfolios():
    """Load all portfolios from file."""
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            data = json.load(f)
        # Handle old format (single portfolio) vs new format (per-user)
        if "users" not in data:
            # Old format - convert to new format
            if "cash" in data or "positions" in data:
                return {"users": {"default": data}}
            return {"users": {}}
        return data
    return {"users": {}}

def save_all_portfolios(data):
    """Save all portfolios to file."""
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_portfolio(capital=DEFAULT_CAPITAL, chat_id=None):
    """Load portfolio for a specific user or legacy format."""
    data = load_all_portfolios()
    
    if chat_id:
        chat_str = str(chat_id)
        if chat_str in data["users"]:
            return data["users"][chat_str]
        else:
            # Create new portfolio for user
            return {
                "cash": capital,
                "positions": {},
                "capital": capital
            }
    else:
        # Legacy mode: use first user or default
        if data["users"]:
            first_user = list(data["users"].keys())[0]
            return data["users"][first_user]
        return {
            "cash": capital,
            "positions": {},
            "capital": capital
        }

def save_portfolio(portfolio, chat_id=None):
    """Save portfolio for a specific user."""
    data = load_all_portfolios()
    
    if chat_id:
        data["users"][str(chat_id)] = portfolio
    else:
        # Legacy mode: update first user or default
        if data["users"]:
            first_user = list(data["users"].keys())[0]
            data["users"][first_user] = portfolio
        else:
            data["users"]["default"] = portfolio
    
    save_all_portfolios(data)

def execute_logic(scored_data, classification, current_prices, primary="HHV", capital=DEFAULT_CAPITAL, chat_id=None):
    portfolio = load_portfolio(capital, chat_id)
    
    # Ensure portfolio has required fields
    if "positions" not in portfolio:
        portfolio["positions"] = {}
    if "cash" not in portfolio:
        portfolio["cash"] = capital
    if "capital" not in portfolio:
        portfolio["capital"] = capital
    
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
        
        # Hard Stop
        if profit_pct <= HARD_STOP_PCT:
            actions.append({"symbol": sym, "action": "SELL", "reason": f"Hard Stop ({HARD_STOP_PCT*100:.0f}%)", "qty": pos["qty"]})
            portfolio["cash"] += pos["qty"] * current_p
            del portfolio["positions"][sym]
            
        # Trailing Stop
        elif profit_pct >= TRAILING_STOP_TRIGGER_PCT and drawdown_from_high >= TRAILING_STOP_PCT:
            actions.append({"symbol": sym, "action": "SELL", "reason": "Trailing Stop", "qty": pos["qty"]})
            portfolio["cash"] += pos["qty"] * current_p
            del portfolio["positions"][sym]
            
        # Take Profit Level 2
        elif profit_pct >= TP2_PCT:
            actions.append({"symbol": sym, "action": "SELL", "reason": f"Take Profit Level 2 (+{TP2_PCT*100:.0f}%)", "qty": pos["qty"]})
            portfolio["cash"] += pos["qty"] * current_p
            del portfolio["positions"][sym]
            
        # Take Profit Level 1
        elif profit_pct >= TP1_PCT and not pos.get("tp_level_1_hit"):
            sell_qty = pos["qty"] // 2
            if sell_qty > 0:
                actions.append({"symbol": sym, "action": "SELL_HALF", "reason": f"Take Profit Level 1 (+{TP1_PCT*100:.0f}%)", "qty": sell_qty})
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
    min_cash_reserve = capital * MIN_CASH_RESERVE_PCT
    
    buy_candidates = []
    if primary not in portfolio["positions"] and not primary_weak and primary_score >= MIN_SCORE_BUY:
        buy_candidates.append(primary)
    if alpha_sym and alpha_sym not in portfolio["positions"]:
        alpha_s = scored_data.get(alpha_sym, {}).get("score", 0)
        if alpha_s >= MIN_SCORE_BUY:
            buy_candidates.append(alpha_sym)
        
    for sym, cls in classification.items():
        if cls == "SECONDARY" and scored_data.get(sym, {}).get("score", 0) >= MIN_SCORE_BUY:
            if sym not in portfolio["positions"] and sym not in buy_candidates:
                buy_candidates.append(sym)
                
    available_slots = MAX_POSITIONS - len(portfolio["positions"])
    for sym in buy_candidates:
        if available_slots <= 0: break
        
        usable_cash = portfolio["cash"] - min_cash_reserve
        if usable_cash < 5000000:  # Not enough after reserve
            break
            
        invest_amount = min(usable_cash, usable_cash / max(available_slots, 1))
        price = current_prices.get(sym)
        if price and price > 0:
            qty = int(invest_amount // (price * 1000)) * 1000 // int(price) if price < 100 else int(invest_amount // price)
            # Round to lot size
            qty = (qty // LOT_SIZE) * LOT_SIZE
            if qty >= LOT_SIZE:
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
    save_portfolio(portfolio, chat_id)
    
    return actions, portfolio
