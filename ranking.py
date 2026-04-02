def rank_stocks(scored_data):
    """
    scored_data: dict of symbol -> score_dict
    Formula: rank_score = (score * 0.45) + (rs_rank * 0.35) + (liquidity_score * 0.20)
    """
    results = {}
    watchlist = ["TOS", "NKG", "AAS"]
    
    for symbol, s_data in scored_data.items():
        if symbol == "VNINDEX":
            continue
            
        score = s_data['score']
        rs_rank = s_data['RS_score']
        liquidity_score = s_data['Volume_Profile_score']
        
        rank_score = (score * 0.45) + (rs_rank * 0.35) + (liquidity_score * 0.20)
        s_data['rank_score'] = round(rank_score, 2)
        results[symbol] = s_data
    
    # Classify
    classification = {}
    hhv_sym = "HHV"
    hhv_rank = results.get(hhv_sym, {}).get('rank_score', 0)
    
    if hhv_sym in results:
        classification[hhv_sym] = "PRIMARY"
        
    alpha_candidate = None
    max_alpha_rank = 0
    
    for w_sym in watchlist:
        if w_sym in results:
            w_rank = results[w_sym]['rank_score']
            if w_rank > max_alpha_rank:
                max_alpha_rank = w_rank
                alpha_candidate = w_sym
                
    for w_sym in watchlist:
        if w_sym in results:
            if w_sym == alpha_candidate and max_alpha_rank > hhv_rank:
                classification[w_sym] = "ALPHA"
            else:
                classification[w_sym] = "SECONDARY"
                
    return results, classification
