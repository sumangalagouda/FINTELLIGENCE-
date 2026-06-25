import pandas as pd
from app.models.transaction import Transaction

def detect_pass_through(case_id: str):
    transactions = (
        Transaction.query
        .filter_by(case_id=case_id, is_failed=False)
        .all()
    )

    if not transactions:
        return {
            "detector": "PassThrough",
            "triggered": False,
            "score": 0,
            "reason": "No transactions available for analysis.",
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

    total_received = df[df["type"] == "credit"]["amount"].sum()
    total_sent = df[df["type"] == "debit"]["amount"].sum()

    if total_received == 0:
        return {
            "detector": "PassThrough",
            "triggered": False,
            "score": 0,
            "reason": "No funds received in this account.",
            "transactions_involved": [],
            "severity": "none",
            "metadata": {}
        }

    ratio = total_sent / total_received
    
    if ratio > 0.90:
        df = df.sort_values("date")
        duration_seconds = (df["date"].max() - df["date"].min()).total_seconds()
        avg_holding_hours = round((duration_seconds / 3600) / max(len(df), 1), 1) if len(df) > 0 else 0.0

        pass_through_pct = ratio * 100
        score = 85 if ratio >= 0.98 else 60 if ratio >= 0.95 else 45
        severity = "critical" if score >= 80 else "high" if score >= 60 else "medium"
        
        return {
            "detector": "PassThrough",
            "triggered": True,
            "score": score,
            "reason": f"Account forwarded {pass_through_pct:.1f}% of received funds with avg holding time of {avg_holding_hours} hours.",
            "transactions_involved": df["txn_id"].tolist(),
            "severity": severity,
            "metadata": {
                "pass_through_pct": round(pass_through_pct, 1),
                "amount_received": round(total_received, 2),
                "amount_forwarded": round(total_sent, 2),
                "amount_retained": round(total_received - total_sent, 2),
                "avg_holding_hours": avg_holding_hours
            }
        }
        
    return {
        "detector": "PassThrough",
        "triggered": False,
        "score": 0,
        "reason": f"Pass-through ratio is {ratio*100:.1f}%, below 90% threshold.",
        "transactions_involved": [],
        "severity": "none",
        "metadata": {}
    }
