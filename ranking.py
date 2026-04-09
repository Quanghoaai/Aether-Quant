from typing import Dict, Any, Tuple, Optional, List
from constants import RANKING_WEIGHTS

def rank_stocks(scored_data: Dict[str, Any], primary: str = "HHV", watchlist: Optional[List[str]] = None) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Rank stocks based on multi-factor scores and assign classifications.
    
    Args:
        scored_data: dict of symbol -> score_dict
        primary: string, the primary component
        watchlist: list of symbols to classify
        
    Returns:
        Tuple mapping:
        - Updated scored_data with 'rank_score'
        - Classification dictionary mapping strings to roles (PRIMARY, ALPHA, SECONDARY)
    """
    if watchlist is None:
        watchlist = []
    
    results = {}
    
    for symbol, s_data in scored_data.items():
        if symbol == "VNINDEX":
            continue
            
        score = s_data['score']
        rs_rank = s_data['RS_score']
        liquidity_score = s_data['Volume_Profile_score']
        
        rank_score = (score * RANKING_WEIGHTS['score'] + 
                      rs_rank * RANKING_WEIGHTS['rs_rank'] + 
                      liquidity_score * RANKING_WEIGHTS['liquidity'])
        s_data['rank_score'] = round(rank_score, 2)
        results[symbol] = s_data
    
    # Classify
    classification = {}
    primary_rank = results.get(primary, {}).get('rank_score', 0)
    
    if primary in results:
        classification[primary] = "PRIMARY"
        
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
            if w_sym == alpha_candidate and max_alpha_rank > primary_rank:
                classification[w_sym] = "ALPHA"
            else:
                classification[w_sym] = "SECONDARY"
                
    return results, classification
