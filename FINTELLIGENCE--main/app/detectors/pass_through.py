# import pandas as pd
# from app.models.transaction import Transaction

# def detect_pass_through(case_id: str):
#     transactions = (
#         Transaction.query
#         .filter_by(case_id=case_id, is_failed=False)
#         .all()
#     )

#     if not transactions:
#         return {
#             "detector": "PassThrough",
#             "triggered": False,
#             "score": 0,
#             "reason": "No transactions available for analysis.",
#             "transactions_involved": [],
#             "severity": "none",
#             "metadata": {}
#         }

#     df = pd.DataFrame([
#         {
#             "txn_id": t.id,
#             "amount": float(t.amount),
#             "type": t.type,
#             "date": pd.to_datetime(t.date)
#         }
#         for t in transactions
#     ])

#     total_received = df[df["type"] == "credit"]["amount"].sum()
#     total_sent = df[df["type"] == "debit"]["amount"].sum()

#     if total_received == 0:
#         return {
#             "detector": "PassThrough",
#             "triggered": False,
#             "score": 0,
#             "reason": "No funds received in this account.",
#             "transactions_involved": [],
#             "severity": "none",
#             "metadata": {}
#         }

#     ratio = total_sent / total_received
    
#     if ratio > 0.90:
#         df = df.sort_values("date")
#         duration_seconds = (df["date"].max() - df["date"].min()).total_seconds()
#         avg_holding_hours = round((duration_seconds / 3600) / max(len(df), 1), 1) if len(df) > 0 else 0.0

#         pass_through_pct = ratio * 100
#         score = 85 if ratio >= 0.98 else 60 if ratio >= 0.95 else 45
#         severity = "critical" if score >= 80 else "high" if score >= 60 else "medium"
        
#         return {
#             "detector": "PassThrough",
#             "triggered": True,
#             "score": score,
#             "reason": f"Account forwarded {pass_through_pct:.1f}% of received funds with avg holding time of {avg_holding_hours} hours.",
#             "transactions_involved": df["txn_id"].tolist(),
#             "severity": severity,
#             "metadata": {
#                 "pass_through_pct": round(pass_through_pct, 1),
#                 "amount_received": round(total_received, 2),
#                 "amount_forwarded": round(total_sent, 2),
#                 "amount_retained": round(total_received - total_sent, 2),
#                 "avg_holding_hours": avg_holding_hours
#             }
#         }
        
#     return {
#         "detector": "PassThrough",
#         "triggered": False,
#         "score": 0,
#         "reason": f"Pass-through ratio is {ratio*100:.1f}%, below 90% threshold.",
#         "transactions_involved": [],
#         "severity": "none",
#         "metadata": {}
#     }
import pandas as pd
from app.models.transaction import Transaction


# ============================================================================
# CONFIGURATION
# ============================================================================

PASS_THROUGH_THRESHOLD = 0.90
HIGH_RISK_THRESHOLD = 0.95
CRITICAL_THRESHOLD = 0.98

MAX_HOLDING_HOURS = 72
MIN_CREDIT_TRANSACTIONS = 3


# ============================================================================
# PASS THROUGH DETECTOR
# ============================================================================

def detect_pass_through(case_id: str):

    transactions = (
        Transaction.query
        .filter_by(case_id=case_id, is_failed=False)
        .all()
    )

    if not transactions:
        return [{
            "detector": "PassThrough",
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
            "amount": float(t.amount),
            "type": str(t.type).lower(),
            "date": pd.to_datetime(t.date)
        }
        for t in transactions
    ])

    if df.empty:
        return [{
            "detector": "PassThrough",
            "triggered": False,
            "score": 0,
            "reason": "No transaction data available.",
            "transactions_involved": [],
            "severity": "none",
            "metadata": {}
        }]

    df = df.sort_values("date").reset_index(drop=True)

    credits = df[df["type"] == "credit"]
    debits = df[df["type"] == "debit"]

    total_received = credits["amount"].sum()
    total_sent = debits["amount"].sum()

    if total_received <= 0:
        return [{
            "detector": "PassThrough",
            "triggered": False,
            "score": 0,
            "reason": "No incoming funds detected.",
            "transactions_involved": [],
            "severity": "none",
            "metadata": {}
        }]

    # ------------------------------------------------------------------------
    # Require repeated behaviour
    # ------------------------------------------------------------------------
    credit_count = len(credits)

    if credit_count < MIN_CREDIT_TRANSACTIONS:
        return [{
            "detector": "PassThrough",
            "triggered": False,
            "score": 0,
            "reason": (
                f"Only {credit_count} incoming transaction(s) found. "
                f"At least {MIN_CREDIT_TRANSACTIONS} are required "
                f"to establish pass-through behaviour."
            ),
            "transactions_involved": [],
            "severity": "none",
            "metadata": {}
        }]

    pass_through_ratio = total_sent / total_received

    if pass_through_ratio < PASS_THROUGH_THRESHOLD:
        return [{
            "detector": "PassThrough",
            "triggered": False,
            "score": 0,
            "reason": (
                f"Pass-through ratio is "
                f"{pass_through_ratio * 100:.1f}%, "
                f"below the {PASS_THROUGH_THRESHOLD * 100:.0f}% threshold."
            ),
            "transactions_involved": [],
            "severity": "none",
            "metadata": {}
        }]

    # ------------------------------------------------------------------------
    # Estimate holding time
    # ------------------------------------------------------------------------
    holding_times = []

    remaining_debits = debits.copy()

    for _, credit in credits.iterrows():

        candidate_debits = remaining_debits[
            remaining_debits["date"] >= credit["date"]
        ]

        if candidate_debits.empty:
            continue

        first_debit = candidate_debits.iloc[0]

        holding_hours = (
            first_debit["date"] - credit["date"]
        ).total_seconds() / 3600

        holding_times.append(holding_hours)

        # Remove matched debit
        remaining_debits = remaining_debits[
            remaining_debits["txn_id"] != first_debit["txn_id"]
        ]

    avg_holding_hours = round(
        sum(holding_times) / len(holding_times),
        1
    ) if holding_times else 0.0

    # ------------------------------------------------------------------------
    # Holding period safeguard
    # ------------------------------------------------------------------------
    if avg_holding_hours > MAX_HOLDING_HOURS:
        return [{
            "detector": "PassThrough",
            "triggered": False,
            "score": 0,
            "reason": (
                f"Funds remained in the account for "
                f"{avg_holding_hours} hours on average, "
                f"which exceeds the "
                f"{MAX_HOLDING_HOURS}-hour threshold."
            ),
            "transactions_involved": [],
            "severity": "none",
            "metadata": {
                "pass_through_pct":
                    round(pass_through_ratio * 100, 1),
                "avg_holding_hours":
                    avg_holding_hours
            }
        }]

    # ------------------------------------------------------------------------
    # Dynamic scoring
    # ------------------------------------------------------------------------
    if (
        pass_through_ratio >= CRITICAL_THRESHOLD
        and avg_holding_hours <= 24
    ):
        score = 90
        severity = "critical"

    elif (
        pass_through_ratio >= HIGH_RISK_THRESHOLD
        and avg_holding_hours <= 48
    ):
        score = 75
        severity = "high"

    else:
        score = 55
        severity = "medium"

    return [{
        "detector": "PassThrough",
        "triggered": True,
        "score": score,
        "reason": (
            f"Account forwarded "
            f"{pass_through_ratio * 100:.1f}% of received funds "
            f"with an average holding period of "
            f"{avg_holding_hours} hours."
        ),
        "transactions_involved":
            df["txn_id"].tolist(),
        "severity": severity,
        "metadata": {
            "pass_through_pct":
                round(pass_through_ratio * 100, 1),
            "amount_received":
                round(total_received, 2),
            "amount_forwarded":
                round(total_sent, 2),
            "amount_retained":
                round(total_received - total_sent, 2),
            "avg_holding_hours":
                avg_holding_hours,
            "credit_transactions":
                credit_count
        }
    }]