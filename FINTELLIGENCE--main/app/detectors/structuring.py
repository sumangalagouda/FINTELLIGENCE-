import pandas as pd
import numpy as np
from rapidfuzz import fuzz
from app.models.transaction import Transaction


# ============================================================================
# CONFIGURATION
# ============================================================================

STRUCTURING_MIN = 40000
NEAR_THRESHOLD_MIN = 45000
REGULATORY_THRESHOLD = 50000

CLASSICAL_WINDOW_DAYS = 7
MIN_CLASSICAL_TXNS = 2


# ============================================================================
# HELPERS
# ============================================================================

def narration_similarity(desc_a: str, desc_b: str) -> float:
    """
    Fast similarity for banking narrations.

    SentenceTransformers are not ideal for UPI references and account IDs,
    so token-based fuzzy matching is more appropriate.
    """
    if not desc_a or not desc_b:
        return 0.0

    return fuzz.token_sort_ratio(desc_a.upper(), desc_b.upper()) / 100.0


# ============================================================================
# STRUCTURING DETECTOR
# ============================================================================

def detect_structuring(case_id: str):

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
            "amount": abs(t.amount),
            "date": pd.to_datetime(t.date),
            "description": t.description or "",
            "direction": getattr(t, "direction", None)
        }
        for t in transactions
        if t.sender_account and t.amount
    ])

    if df.empty:
        return []

    # ------------------------------------------------------------------------
    # OPTIONAL:
    # Focus primarily on incoming money if direction exists.
    # Remove this block if your schema doesn't support direction.
    # ------------------------------------------------------------------------
    if "direction" in df.columns and df["direction"].notna().any():
        df = df[df["direction"] == "credit"]

    if df.empty:
        return []

    results = []

    # ------------------------------------------------------------------------
    # ONLY consider near-threshold transactions
    # ------------------------------------------------------------------------
    candidate_txns = df[
        (df["amount"] >= STRUCTURING_MIN) &
        (df["amount"] < REGULATORY_THRESHOLD)
    ].copy()

    if candidate_txns.empty:
        return []

    candidate_txns = candidate_txns.sort_values(
        ["sender_account", "date"]
    )

    processed_clusters = set()

    # ========================================================================
    # PER ACCOUNT ANALYSIS
    # ========================================================================
    for sender, group in candidate_txns.groupby("sender_account"):

        group = group.set_index("date")

        for current_date in group.index:

            window_start = current_date
            window_end = current_date + pd.Timedelta(
                days=CLASSICAL_WINDOW_DAYS
            )

            cluster = group[
                (group.index >= window_start) &
                (group.index <= window_end)
            ]

            txn_ids = tuple(sorted(cluster["txn_id"].tolist()))

            # Prevent duplicate alerts
            if txn_ids in processed_clusters:
                continue

            processed_clusters.add(txn_ids)

            count = len(cluster)
            avg_amount = cluster["amount"].mean()

            proximity_pct = (
                avg_amount / REGULATORY_THRESHOLD
            ) * 100

            unique_receivers = (
                cluster["receiver_account"].nunique()
            )

            # ================================================================
            # CASE 1:
            # CLASSICAL STRUCTURING
            # ================================================================
            if count >= MIN_CLASSICAL_TXNS:

                score = 60

                # More transactions = higher suspicion
                score += min((count - 2) * 10, 20)

                # Close to 50K threshold
                score += min((proximity_pct - 80) * 0.8, 15)

                # Same beneficiary repeatedly
                if (
                    unique_receivers == 1
                    and cluster["receiver_account"].iloc[0]
                ):
                    score += 10

                # Narration similarity
                descriptions = cluster["description"].tolist()

                sim_score = 0.0

                if len(descriptions) > 1:

                    similarities = []

                    for i in range(len(descriptions)):
                        for j in range(i + 1, len(descriptions)):

                            similarities.append(
                                narration_similarity(
                                    descriptions[i],
                                    descriptions[j]
                                )
                            )

                    if similarities:

                        sim_score = float(
                            np.mean(similarities)
                        )

                        if sim_score > 0.8:
                            score += 10

                score = min(100, int(score))

                results.append({
                    "detector": "Structuring",
                    "triggered": True,
                    "score": score,
                    "severity": (
                        "critical"
                        if score >= 90
                        else "high"
                    ),
                    "reason": (
                        f"{count} near-threshold transactions "
                        f"(₹40K–₹50K) detected within "
                        f"{CLASSICAL_WINDOW_DAYS} days. "
                        f"Average amount: ₹{avg_amount:,.2f}. "
                        f"Possible smurfing/structuring behaviour."
                    ),
                    "transactions_involved":
                        cluster["txn_id"].tolist(),
                    "metadata": {
                        "pattern_type":
                            "classical_structuring",
                        "transactions_in_window":
                            count,
                        "avg_amount":
                            float(avg_amount),
                        "threshold_proximity_pct":
                            float(proximity_pct),
                        "unique_receivers":
                            int(unique_receivers),
                        "description_similarity":
                            float(sim_score)
                    }
                })

            # ================================================================
            # CASE 2:
            # SINGLE NEAR-THRESHOLD TRANSACTION
            # ================================================================
            elif count == 1:

                txn = cluster.iloc[0]

                if txn["amount"] >= NEAR_THRESHOLD_MIN:

                    score = 55 + (
                        (
                            txn["amount"]
                            - NEAR_THRESHOLD_MIN
                        ) / 5000
                    ) * 20

                    score = min(75, int(score))

                    results.append({
                        "detector": "NearThresholdTransaction",
                        "triggered": True,
                        "score": score,
                        "severity": "medium",
                        "reason": (
                            f"Single transaction of "
                            f"₹{txn['amount']:,.2f} "
                            f"was detected very close to the "
                            f"₹50,000 reporting threshold. "
                            f"This may indicate deliberate "
                            f"threshold avoidance."
                        ),
                        "transactions_involved":
                            [txn["txn_id"]],
                        "metadata": {
                            "pattern_type":
                                "single_near_threshold",
                            "amount":
                                float(txn["amount"]),
                            "threshold_proximity_pct":
                                float(
                                    (
                                        txn["amount"]
                                        / REGULATORY_THRESHOLD
                                    ) * 100
                                )
                        }
                    })

    return results