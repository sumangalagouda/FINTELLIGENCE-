import pandas as pd
from app.models.transaction import Transaction

DORMANCY_THRESHOLD_DAYS = 180
HIGH_DORMANCY_THRESHOLD_DAYS = 365


def detect_dormant_revival(case_id: str):
    transactions = (
        Transaction.query
        .filter_by(case_id=case_id, is_failed=False)
        .order_by(Transaction.date)
        .all()
    )

    if not transactions:
        return [{
            "detector": "DormantRevival",
            "triggered": False,
            "score": 0,
            "reason": "No transactions available for analysis.",
            "transactions_involved": [],
            "severity": "none",
            "metadata": {}
        }]

    df = pd.DataFrame([
        {
            "txn_id": t.id,
            "sender_account": t.sender_account,
            "amount": float(t.amount),
            "date": pd.to_datetime(t.date)
        }
        for t in transactions
        if t.sender_account
    ])

    if df.empty:
        return [{
            "detector": "DormantRevival",
            "triggered": False,
            "score": 0,
            "reason": "No sender accounts available for dormancy analysis.",
            "transactions_involved": [],
            "severity": "none",
            "metadata": {}
        }]

    df = df.sort_values(["sender_account", "date"])

    # Previous transaction date
    df["prev_date"] = (
        df.groupby("sender_account")["date"]
        .shift(1)
    )

    # Gap between transactions
    df["days_since_last"] = (
        df["date"] - df["prev_date"]
    ).dt.days

    # Historical average before current transaction
    df["historical_avg"] = (
        df.groupby("sender_account")["amount"]
        .transform(
            lambda x: x.expanding().mean().shift(1)
        )
    )

    results = []

    for account, group in df.groupby("sender_account"):

        group = group.reset_index(drop=True)

        for idx, row in group.iterrows():

            if pd.isna(row["days_since_last"]):
                continue

            days_gap = int(row["days_since_last"])

            if days_gap < DORMANCY_THRESHOLD_DAYS:
                continue

            score = 40
            reasons = [
                f"Account inactive for {days_gap} days."
            ]

            # Very long dormancy
            if days_gap >= HIGH_DORMANCY_THRESHOLD_DAYS:
                score += 20
                reasons.append(
                    "Dormancy exceeded 1 year."
                )

            multiplier = 0.0

            hist_avg = row["historical_avg"]

            if pd.notna(hist_avg) and hist_avg > 0:

                multiplier = row["amount"] / hist_avg

                if multiplier >= 3:
                    score += 15
                    reasons.append(
                        f"Revival transaction is {multiplier:.1f}x historical average."
                    )

                if multiplier >= 5:
                    score += 15

            # Activity immediately after revival
            subsequent = group.iloc[idx + 1:]

            if not subsequent.empty:

                rapid_txns = subsequent[
                    (subsequent["date"] - row["date"]).dt.days <= 7
                ]

                if len(rapid_txns) >= 3:
                    score += 20
                    reasons.append(
                        f"{len(rapid_txns)} additional transactions occurred within 7 days."
                    )

            score = min(score, 100)

            if score >= 80:
                severity = "high"
            elif score >= 60:
                severity = "medium"
            else:
                severity = "low"

            results.append({
                "detector": "DormantRevival",
                "triggered": True,
                "score": score,
                "reason": " ".join(reasons),
                "transactions_involved": [row["txn_id"]],
                "severity": severity,
                "metadata": {
                    "account": account,
                    "days_dormant": days_gap,
                    "amount": float(row["amount"]),
                    "historical_avg": (
                        round(float(hist_avg), 2)
                        if pd.notna(hist_avg)
                        else 0
                    ),
                    "multiplier": round(multiplier, 2)
                }
            })

    # No dormant revival found
    if not results:
        return [{
            "detector": "DormantRevival",
            "triggered": False,
            "score": 0,
            "reason": "No dormancy patterns detected within available transaction history.",
            "transactions_involved": [],
            "severity": "none",
            "metadata": {}
        }]

    return results