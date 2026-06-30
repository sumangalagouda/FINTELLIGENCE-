import pandas as pd
from app.models.transaction import Transaction


# ============================================================================
# CONFIGURATION
# ============================================================================

CASH_KEYWORDS = [
    "cash",
    "cash dep",
    "cash deposit",
    "cash wdl",
    "atm withdrawal",
    "atm wdl",
    "atm deposit",
    "cdm",
    "self withdrawal",
    "by cash",
    "cash remittance"
]

MAX_TIME_WINDOW_HOURS = 24
MAX_AMOUNT_DIFFERENCE = 0.10   # 10%


# ============================================================================
# CASH CYCLING DETECTOR
# ============================================================================

def detect_cash_cycling(case_id: str):

    transactions = (
        Transaction.query
        .filter_by(case_id=case_id, is_failed=False)
        .all()
    )

    if len(transactions) < 2:
        return [{
            "detector": "CashCycling",
            "triggered": False,
            "score": 0,
            "reason": "Not enough transactions for cash cycling analysis.",
            "transactions_involved": [],
            "severity": "none",
            "metadata": {}
        }]

    df = pd.DataFrame([
        {
            "txn_id": t.id,
            "amount": float(t.amount),
            "type": str(t.type).lower(),
            "date": pd.to_datetime(t.date),
            "description": (
                str(t.description).lower()
                if t.description else ""
            )
        }
        for t in transactions
    ])

    if df.empty:
        return [{
            "detector": "CashCycling",
            "triggered": False,
            "score": 0,
            "reason": "No transactions available.",
            "transactions_involved": [],
            "severity": "none",
            "metadata": {}
        }]

    df = df.sort_values("date").reset_index(drop=True)

    # ------------------------------------------------------------------------
    # Detect cash-related transactions
    # ------------------------------------------------------------------------
    def is_cash_transaction(desc):
        return any(
            keyword in desc
            for keyword in CASH_KEYWORDS
        )

    df["is_cash"] = df["description"].apply(
        is_cash_transaction
    )

    cash_deposits = df[
        (df["type"] == "credit") &
        (df["is_cash"])
    ]

    cash_withdrawals = df[
        (df["type"] == "debit") &
        (df["is_cash"])
    ]

    detected_cycles = []

    # ------------------------------------------------------------------------
    # Match deposits with nearby withdrawals
    # ------------------------------------------------------------------------
    for _, deposit in cash_deposits.iterrows():

        deposit_time = deposit["date"]

        candidate_withdrawals = cash_withdrawals[
            (cash_withdrawals["date"] >= deposit_time)
            &
            (
                (cash_withdrawals["date"] - deposit_time)
                .dt.total_seconds()
                <= MAX_TIME_WINDOW_HOURS * 3600
            )
        ]

        for _, withdrawal in candidate_withdrawals.iterrows():

            amount_in = deposit["amount"]
            amount_out = withdrawal["amount"]

            if amount_in <= 0:
                continue

            difference_pct = abs(
                amount_in - amount_out
            ) / amount_in

            # Must retain at least 90% similarity
            if difference_pct > MAX_AMOUNT_DIFFERENCE:
                continue

            detected_cycles.append({
                "deposit_id": deposit["txn_id"],
                "withdrawal_id": withdrawal["txn_id"],
                "amount_in": amount_in,
                "amount_out": amount_out,
                "difference_pct": difference_pct
            })

    # ------------------------------------------------------------------------
    # No cycles found
    # ------------------------------------------------------------------------
    if not detected_cycles:

        return [{
            "detector": "CashCycling",
            "triggered": False,
            "score": 0,
            "reason": "No cash cycling patterns detected.",
            "transactions_involved": [],
            "severity": "none",
            "metadata": {}
        }]

    # ------------------------------------------------------------------------
    # Aggregate results
    # ------------------------------------------------------------------------
    total_cycles = len(detected_cycles)

    largest_cycle = max(
        detected_cycles,
        key=lambda x: x["amount_in"]
    )

    if total_cycles == 1:
        score = 55
        severity = "medium"

    elif total_cycles == 2:
        score = 75
        severity = "high"

    else:
        score = 90
        severity = "critical"

    involved_txns = []

    for cycle in detected_cycles:

        involved_txns.extend([
            cycle["deposit_id"],
            cycle["withdrawal_id"]
        ])

    involved_txns = list(set(involved_txns))

    return [{
        "detector": "CashCycling",
        "triggered": True,
        "score": score,
        "reason": (
            f"{total_cycles} cash deposit-withdrawal cycle(s) "
            f"were detected within {MAX_TIME_WINDOW_HOURS} hours. "
            f"The largest cycle involved "
            f"₹{largest_cycle['amount_in']:,.2f}."
        ),
        "transactions_involved": involved_txns,
        "severity": severity,
        "metadata": {
            "total_cycles": total_cycles,
            "largest_cycle_amount":
                largest_cycle["amount_in"],
            "largest_difference_pct":
                round(
                    largest_cycle["difference_pct"] * 100,
                    2
                )
        }
    }]