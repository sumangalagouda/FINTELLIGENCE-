import pandas as pd
from scipy.stats import zscore
from app.models.transaction import Transaction


MIN_AMOUNT_THRESHOLD = 50000
MULTIPLIER_THRESHOLD = 3.0


def detect_large_transaction(case_id: str):
    transactions = (
        Transaction.query
        .filter_by(case_id=case_id, is_failed=False)
        .order_by(Transaction.date)
        .all()
    )

    if not transactions:
        return []

    df = pd.DataFrame([
        {
            "txn_id": t.id,
            "sender_account": t.sender_account,
            "receiver_account": t.receiver_account,
            "amount": float(t.amount),
            "date": pd.to_datetime(t.date)
        }
        for t in transactions
    ])

    df = df.dropna(subset=["sender_account"])

    if df.empty:
        return []

    df = df.sort_values(["sender_account", "date"])

    # --------------------------------------------------
    # Historical rolling average (EXCLUDES current txn)
    # --------------------------------------------------
    df["rolling_avg"] = (
        df.groupby("sender_account")["amount"]
        .transform(
            lambda x: (
                x.shift(1)
                 .rolling(window=20, min_periods=1)
                 .mean()
            )
        )
    )

    # --------------------------------------------------
    # Account-wise z-score
    # --------------------------------------------------
    df["zscore"] = (
        df.groupby("sender_account")["amount"]
        .transform(
            lambda x: pd.Series(
                zscore(x, nan_policy="omit"),
                index=x.index
            )
        )
    )

    df["zscore"] = df["zscore"].fillna(0)

    # --------------------------------------------------
    # Multiplier calculation
    # --------------------------------------------------
    df["multiplier"] = df["amount"] / df["rolling_avg"]

    # Remove rows without historical baseline
    df = df[df["rolling_avg"].notna()]

    # --------------------------------------------------
    # Detection criteria
    # --------------------------------------------------
    flagged = df[
        (df["amount"] >= MIN_AMOUNT_THRESHOLD)
        &
        (df["multiplier"] >= MULTIPLIER_THRESHOLD)
    ].copy()

    if flagged.empty:
        return []

    # --------------------------------------------------
    # Fraud score
    # --------------------------------------------------
    flagged["risk_score"] = flagged.apply(
        lambda row: min(
            100,
            int(
                (row["multiplier"] * 15)
                +
                (max(row["zscore"], 0) * 10)
            )
        ),
        axis=1
    )

    # Highest risk first
    flagged = flagged.sort_values(
        by=["risk_score", "multiplier", "zscore"],
        ascending=False
    )

    results = []

    for _, row in flagged.iterrows():

        multiplier = float(row["multiplier"])
        z_score_val = float(row["zscore"])

        if multiplier >= 8:
            severity = "critical"
        elif multiplier >= 5:
            severity = "high"
        else:
            severity = "medium"

        results.append({
            "detector": "LargeTransaction",
            "triggered": True,
            "score": int(row["risk_score"]),
            "reason": (
                f"₹{row['amount']:,.2f} is "
                f"{multiplier:.2f}x the historical average "
                f"of ₹{row['rolling_avg']:,.2f}. "
                f"Z-score: {z_score_val:.2f}"
            ),
            "severity": severity,
            "transactions_involved": [row["txn_id"]],
            "metadata": {
                "amount": float(row["amount"]),
                "rolling_avg": float(row["rolling_avg"]),
                "multiplier": round(multiplier, 2),
                "zscore": round(z_score_val, 2)
            }
        })

    return results