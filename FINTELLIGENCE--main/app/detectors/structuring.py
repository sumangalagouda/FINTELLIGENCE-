import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer, util
from app.models.transaction import Transaction

# Load model globally (lazy loading inside the function is also fine, but global avoids reload per request)
# Alternatively, load it inside the function to save memory if not frequently used.
_model = None

def get_similarity_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def detect_structuring(case_id: str):
    transactions = Transaction.query.filter_by(case_id=case_id).order_by(Transaction.date).all()
    if not transactions:
        return []

    df = pd.DataFrame([{
        'txn_id': t.id,
        'sender_account': t.sender_account,
        'receiver_account': t.receiver_account,
        'amount': t.amount,
        'date': pd.to_datetime(t.date),
        'description': t.description or ''
    } for t in transactions if t.sender_account])

    if df.empty:
        return []

    # Filter transactions between 40k and 49,999
    # Usually structuring is deposits/credits, but depending on context, it could be debits.
    # We will look at absolute amount for structuring, assuming sending/receiving context is unified here.
    sub_threshold = df[(df['amount'] >= 40000) & (df['amount'] < 50000)].copy()
    
    if sub_threshold.empty:
        return []

    sub_threshold = sub_threshold.sort_values(by=['sender_account', 'date'])
    sub_threshold = sub_threshold.set_index('date')

    results = []

    # Rolling 7-day window
    for sender, group in sub_threshold.groupby('sender_account'):
        # For each transaction, count how many within 7 days
        for i, row in group.iterrows():
            # i is date index
            window_start = i
            window_end = i + pd.Timedelta(days=7)
            
            window_txns = group[(group.index >= window_start) & (group.index <= window_end)]
            
            if len(window_txns) >= 2:
                # Calculate scores
                count = len(window_txns)
                avg_amount = window_txns['amount'].mean()
                threshold_proximity_pct = (avg_amount / 50000.0) * 100
                
                # Proximity score (higher is closer to 50k)
                score = 50 + (threshold_proximity_pct - 80) * 2 # If 98%, gives 50 + 36 = 86
                
                # Frequency
                score += (count - 2) * 10
                
                # Same beneficiary
                unique_beneficiaries = window_txns['receiver_account'].nunique()
                if unique_beneficiaries == 1 and window_txns['receiver_account'].iloc[0] is not None:
                    score += 15
                
                # Description similarity
                descriptions = window_txns['description'].tolist()
                sim_score = 0.0
                if len(descriptions) > 1 and any(descriptions):
                    model = get_similarity_model()
                    embeddings = model.encode(descriptions)
                    # compute pairwise similarity
                    cosine_scores = util.cos_sim(embeddings, embeddings)
                    # Average similarity excluding self
                    mask = ~np.eye(cosine_scores.shape[0], dtype=bool)
                    sim_score = cosine_scores[mask].mean().item()
                    
                    if sim_score > 0.8:
                        score += (sim_score * 20)
                
                score = min(100, score)

                # Avoid adding the same window repeatedly
                # We can just add the first one and break, or aggregate
                results.append({
                    "detector": "Structuring",
                    "triggered": True,
                    "score": int(score),
                    "reason": f"{count} transactions between ₹40,000-₹49,999 within 7 days. Avg proximity to threshold: {threshold_proximity_pct:.1f}%. Description similarity: {sim_score*100:.0f}%",
                    "severity": "high" if score >= 75 else "medium",
                    "transactions_involved": window_txns['txn_id'].tolist(),
                    "metadata": {
                        "transactions_in_window": count,
                        "avg_amount": float(avg_amount),
                        "threshold_proximity_pct": float(threshold_proximity_pct),
                        "description_similarity": float(sim_score)
                    }
                })
                
                break # Just emit one alert per sender for the cluster to avoid duplicates, or could be refined.

    return results
