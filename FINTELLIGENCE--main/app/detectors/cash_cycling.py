import pandas as pd
from app.models.transaction import Transaction

def detect_cash_cycling(case_id: str):
    transactions = (
        Transaction.query
        .filter_by(case_id=case_id, is_failed=False)
        .all()
    )

    if len(transactions) < 2:
        return {
            "detector": "CashCycling",
            "triggered": False,
            "score": 0,
            "reason": "Not enough transactions for cash cycling analysis.",
            "transactions_involved": [],
            "severity": "none",
            "metadata": {}
        }

    df = pd.DataFrame([
        {
            "txn_id": t.id,
            "amount": float(t.amount),
            "type": t.type,
            "date": pd.to_datetime(t.date),
            "description": str(t.description).lower() if t.description else ""
        }
        for t in transactions
    ])

    results = []
    
    df = df.sort_values("date").reset_index(drop=True)
    
    cash_keywords = ["cash", "atm deposit", "cdm", "atm withdrawal"]
    
    def is_cash(desc):
        return any(k in desc for k in cash_keywords)

    df["is_cash"] = df["description"].apply(is_cash)
    
    cash_deposits = df[(df["type"] == "credit") & (df["is_cash"])]
    cash_withdrawals = df[(df["type"] == "debit") & (df["is_cash"])]
    
    for idx, deposit in cash_deposits.iterrows():
        mask = (cash_withdrawals["date"] >= deposit["date"]) & ((cash_withdrawals["date"] - deposit["date"]).dt.total_seconds() <= 86400)
        subsequent_withdrawals = cash_withdrawals[mask]
        
        for w_idx, withdrawal in subsequent_withdrawals.iterrows():
            amt_in = deposit["amount"]
            amt_out = withdrawal["amount"]
            
            diff_pct = abs(amt_in - amt_out) / amt_in if amt_in > 0 else 0
            
            if diff_pct <= 0.10:
                score = 70 if diff_pct <= 0.05 else 50
                severity = "high" if score >= 60 else "medium"
                
                results.append({
                    "detector": "CashCycling",
                    "triggered": True,
                    "score": score,
                    "reason": f"Cash deposit of ₹{amt_in:,.2f} followed by cash withdrawal of ₹{amt_out:,.2f} within 24 hours.",
                    "transactions_involved": [deposit["txn_id"], withdrawal["txn_id"]],
                    "severity": severity,
                    "metadata": {
                        "amount_deposited": amt_in,
                        "amount_withdrawn": amt_out,
                        "difference_pct": round(diff_pct * 100, 1)
                    }
                })

    if not results:
        return {
            "detector": "CashCycling",
            "triggered": False,
            "score": 0,
            "reason": "No cash cycling patterns detected.",
            "transactions_involved": [],
            "severity": "none",
            "metadata": {}
        }
        
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[0]
