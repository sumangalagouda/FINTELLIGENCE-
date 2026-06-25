import pandas as pd
from app.models.transaction import Transaction

def detect_velocity(case_id: str):
    transactions = (
        Transaction.query
        .filter_by(case_id=case_id, is_failed=False)
        .order_by(Transaction.date)
        .all()
    )

    if len(transactions) < 2:
        return {
            "detector": "TransactionVelocity",
            "triggered": False,
            "score": 0,
            "reason": "Not enough transactions for velocity analysis.",
            "transactions_involved": [],
            "severity": "none",
            "metadata": {}
        }

    df = pd.DataFrame([
        {
            "txn_id": t.id,
            "amount": float(t.amount),
            "type": t.type,
            "date": pd.to_datetime(t.date)
        }
        for t in transactions
    ])

    results = []
    
    df = df.sort_values("date").reset_index(drop=True)
    
    credits = df[df["type"] == "credit"]
    
    for idx, credit in credits.iterrows():
        mask = (df["type"] == "debit") & (df["date"] >= credit["date"]) & ((df["date"] - credit["date"]).dt.total_seconds() <= 3600)
        subsequent_debits = df[mask]
        
        for d_idx, debit in subsequent_debits.iterrows():
            amt_in = credit["amount"]
            amt_out = debit["amount"]
            
            diff_pct = abs(amt_in - amt_out) / amt_in if amt_in > 0 else 0
            
            if diff_pct <= 0.05:
                time_diff_minutes = int((debit["date"] - credit["date"]).total_seconds() / 60)
                forwarded_pct = (amt_out / amt_in) * 100 if amt_in > 0 else 0
                
                score = 40
                if time_diff_minutes <= 10:
                    score += 40
                elif time_diff_minutes <= 30:
                    score += 20
                
                if diff_pct <= 0.01:
                    score += 20
                    
                score = min(score, 100)
                
                severity = "critical" if score >= 80 else "high" if score >= 60 else "medium"
                
                results.append({
                    "detector": "TransactionVelocity",
                    "triggered": True,
                    "score": score,
                    "reason": f"₹{amt_in:,.2f} received and ₹{amt_out:,.2f} forwarded within {time_diff_minutes} minutes. {forwarded_pct:.1f}% of funds forwarded.",
                    "transactions_involved": [credit["txn_id"], debit["txn_id"]],
                    "severity": severity,
                    "metadata": {
                        "time_diff_minutes": time_diff_minutes,
                        "amount_in": amt_in,
                        "amount_out": amt_out,
                        "forwarded_pct": round(forwarded_pct, 1)
                    }
                })

    if not results:
        return {
            "detector": "TransactionVelocity",
            "triggered": False,
            "score": 0,
            "reason": "No high-velocity transaction pairs detected.",
            "transactions_involved": [],
            "severity": "none",
            "metadata": {}
        }
        
    # Return highest score if multiple pairs
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[0]
