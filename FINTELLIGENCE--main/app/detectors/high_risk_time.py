import pandas as pd
from scipy.stats import gaussian_kde
from app.models.transaction import Transaction


INDIAN_HOLIDAYS = [
    "01-26",  # Republic Day
    "08-15",  # Independence Day
    "10-02",  # Gandhi Jayanti
    "12-25",  # Christmas
    "11-12",  # Diwali (placeholder)
    "03-25",  # Holi (placeholder)
    "04-11",  # Eid (placeholder)
]


def detect_high_risk_time(case_id: str):
    transactions = (
        Transaction.query
        .filter_by(case_id=case_id)
        .order_by(Transaction.date)
        .all()
    )

    if not transactions:
        return [{
            "detector": "HighRiskTime",
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
            "date": pd.to_datetime(t.date),
            "amount": float(t.amount)
        }
        for t in transactions
    ])

    if df.empty:
        return [{
            "detector": "HighRiskTime",
            "triggered": False,
            "score": 0,
            "reason": "No transaction data available.",
            "transactions_involved": [],
            "severity": "none",
            "metadata": {}
        }]

    # --------------------------------------------------
    # Check whether statement contains actual time data
    # --------------------------------------------------
    has_time_data = (
        (df["date"].dt.hour != 0) |
        (df["date"].dt.minute != 0) |
        (df["date"].dt.second != 0)
    ).any()

    if not has_time_data:
        return [{
            "detector": "HighRiskTime",
            "triggered": False,
            "score": 0,
            "reason": "No time component available in transaction data.",
            "transactions_involved": [],
            "severity": "none",
            "metadata": {}
        }]

    # --------------------------------------------------
    # Extract time features
    # --------------------------------------------------
    df["hour"] = df["date"].dt.hour

    # High-risk window: 1 AM - 4:59 AM
    df["is_midnight"] = df["hour"].between(1, 4)

    # Holiday detection
    df["month_day"] = df["date"].dt.strftime("%m-%d")
    df["is_holiday"] = df["month_day"].isin(INDIAN_HOLIDAYS)

    flagged = df[
        df["is_midnight"] |
        df["is_holiday"]
    ].copy()

    if flagged.empty:
        return [{
            "detector": "HighRiskTime",
            "triggered": False,
            "score": 0,
            "reason": "No high-risk timing patterns detected.",
            "transactions_involved": [],
            "severity": "none",
            "metadata": {}
        }]

    # --------------------------------------------------
    # Midnight clustering analysis
    # --------------------------------------------------
    cluster_bonus = 0

    midnight_txns = flagged[
        flagged["is_midnight"]
    ].copy()

    if len(midnight_txns) >= 3:

        midnight_txns["minutes"] = (
            midnight_txns["date"].dt.hour * 60
            + midnight_txns["date"].dt.minute
        )

        kde = gaussian_kde(midnight_txns["minutes"])
        midnight_txns["density"] = kde(midnight_txns["minutes"])

        density_map = dict(
            zip(
                midnight_txns["txn_id"],
                midnight_txns["density"]
            )
        )

        cluster_bonus = 20

    else:
        density_map = {}

    # --------------------------------------------------
    # Generate results
    # --------------------------------------------------
    results = []

    for _, row in flagged.iterrows():

        score = 0
        reasons = []

        txn_density = density_map.get(
            row["txn_id"],
            0
        )

        if row["is_midnight"]:
            score += 40

            reasons.append(
                f"Transaction occurred at "
                f"{row['date'].strftime('%I:%M %p')} "
                f"(high-risk midnight window)."
            )

            if txn_density > 0.01:
                score += cluster_bonus

                reasons.append(
                    "Part of a cluster of late-night transactions."
                )

        if row["is_holiday"]:
            score += 30

            reasons.append(
                f"Transaction occurred on a public holiday "
                f"({row['month_day']})."
            )

        score = min(score, 100)

        if score >= 80:
            severity = "critical"
        elif score >= 60:
            severity = "high"
        else:
            severity = "medium"

        results.append({
            "detector": "HighRiskTime",
            "triggered": True,
            "score": score,
            "reason": " ".join(reasons),
            "transactions_involved": [row["txn_id"]],
            "severity": severity,
            "metadata": {
                "hour": int(row["hour"]),
                "is_midnight": bool(row["is_midnight"]),
                "is_holiday": bool(row["is_holiday"])
            }
        })

    return sorted(
        results,
        key=lambda x: x["score"],
        reverse=True
    )