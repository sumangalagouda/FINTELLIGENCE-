# # import pandas as pd
# # from scipy.stats import gaussian_kde
# # from app.models.transaction import Transaction


# # INDIAN_HOLIDAYS = [
# #     "01-26",  # Republic Day
# #     "08-15",  # Independence Day
# #     "10-02",  # Gandhi Jayanti
# #     "12-25",  # Christmas
# #     "11-12",  # Diwali 
# #     "03-25",  # Holi 
# #     "04-11",  # Eid 
# # ]


# # def detect_high_risk_time(case_id: str):
# #     transactions = (
# #         Transaction.query
# #         .filter_by(case_id=case_id, is_failed=False)
# #         .order_by(Transaction.date)
# #         .all()
# #     )

# #     if not transactions:
# #         return [{
# #             "detector": "HighRiskTime",
# #             "triggered": False,
# #             "score": 0,
# #             "reason": "No transactions available for analysis.",
# #             "transactions_involved": [],
# #             "severity": "none",
# #             "metadata": {}
# #         }]

# #     df = pd.DataFrame([
# #         {
# #             "txn_id": t.id,
# #             "date": pd.to_datetime(t.date),
# #             "amount": float(t.amount)
# #         }
# #         for t in transactions
# #     ])

# #     if df.empty:
# #         return [{
# #             "detector": "HighRiskTime",
# #             "triggered": False,
# #             "score": 0,
# #             "reason": "No transaction data available.",
# #             "transactions_involved": [],
# #             "severity": "none",
# #             "metadata": {}
# #         }]

# #     # --------------------------------------------------
# #     # Check whether statement contains actual time data
# #     # --------------------------------------------------
# #     has_time_data = (
# #         (df["date"].dt.hour != 0) |
# #         (df["date"].dt.minute != 0) |
# #         (df["date"].dt.second != 0)
# #     ).any()

# #     if not has_time_data:
# #         return [{
# #             "detector": "HighRiskTime",
# #             "triggered": False,
# #             "score": 0,
# #             "reason": "No time component available in transaction data.",
# #             "transactions_involved": [],
# #             "severity": "none",
# #             "metadata": {}
# #         }]

# #     # --------------------------------------------------
# #     # Extract time features
# #     # --------------------------------------------------
# #     df["hour"] = df["date"].dt.hour

# #     # High-risk window: 1 AM - 4:59 AM
# #     df["is_midnight"] = df["hour"].between(1, 4)

# #     # Holiday detection
# #     df["month_day"] = df["date"].dt.strftime("%m-%d")
# #     df["is_holiday"] = df["month_day"].isin(INDIAN_HOLIDAYS)

# #     flagged = df[
# #         df["is_midnight"] |
# #         df["is_holiday"]
# #     ].copy()

# #     if flagged.empty:
# #         return [{
# #             "detector": "HighRiskTime",
# #             "triggered": False,
# #             "score": 0,
# #             "reason": "No high-risk timing patterns detected.",
# #             "transactions_involved": [],
# #             "severity": "none",
# #             "metadata": {}
# #         }]

# #     # --------------------------------------------------
# #     # Midnight clustering analysis
# #     # --------------------------------------------------
# #     cluster_bonus = 0

# #     midnight_txns = flagged[
# #         flagged["is_midnight"]
# #     ].copy()

# #     if len(midnight_txns) >= 3:

# #         midnight_txns["minutes"] = (
# #             midnight_txns["date"].dt.hour * 60
# #             + midnight_txns["date"].dt.minute
# #         )

# #         kde = gaussian_kde(midnight_txns["minutes"])
# #         midnight_txns["density"] = kde(midnight_txns["minutes"])

# #         density_map = dict(
# #             zip(
# #                 midnight_txns["txn_id"],
# #                 midnight_txns["density"]
# #             )
# #         )

# #         cluster_bonus = 20

# #     else:
# #         density_map = {}

# #     # --------------------------------------------------
# #     # Generate results
# #     # --------------------------------------------------
# #     results = []

# #     for _, row in flagged.iterrows():

# #         score = 0
# #         reasons = []

# #         txn_density = density_map.get(
# #             row["txn_id"],
# #             0
# #         )

# #         if row["is_midnight"]:
# #             score += 40

# #             reasons.append(
# #                 f"Transaction occurred at "
# #                 f"{row['date'].strftime('%I:%M %p')} "
# #                 f"(high-risk midnight window)."
# #             )

# #             if txn_density > 0.01:
# #                 score += cluster_bonus

# #                 reasons.append(
# #                     "Part of a cluster of late-night transactions."
# #                 )

# #         if row["is_holiday"]:
# #             score += 30

# #             reasons.append(
# #                 f"Transaction occurred on a public holiday "
# #                 f"({row['month_day']})."
# #             )

# #         score = min(score, 100)

# #         if score >= 80:
# #             severity = "critical"
# #         elif score >= 60:
# #             severity = "high"
# #         else:
# #             severity = "medium"

# #         results.append({
# #             "detector": "HighRiskTime",
# #             "triggered": True,
# #             "score": score,
# #             "reason": " ".join(reasons),
# #             "transactions_involved": [row["txn_id"]],
# #             "severity": severity,
# #             "metadata": {
# #                 "hour": int(row["hour"]),
# #                 "is_midnight": bool(row["is_midnight"]),
# #                 "is_holiday": bool(row["is_holiday"])
# #             }
# #         })

# #     return sorted(
# #         results,
# #         key=lambda x: x["score"],
# #         reverse=True
# #     )

# import pandas as pd
# import holidays
# from app.models.transaction import Transaction


# # Indian public holidays (dynamic, year-aware)
# INDIA_HOLIDAYS = holidays.India()


# MIDNIGHT_START = 0      # 12:00 AM
# MIDNIGHT_END = 5        # 05:59 AM
# MIN_CLUSTER_SIZE = 3


# def detect_high_risk_time(case_id: str):

#     transactions = (
#         Transaction.query
#         .filter_by(case_id=case_id, is_failed=False)
#         .order_by(Transaction.date)
#         .all()
#     )

#     if not transactions:
#         return [{
#             "detector": "HighRiskTime",
#             "triggered": False,
#             "score": 0,
#             "reason": "No transactions available for analysis.",
#             "transactions_involved": [],
#             "severity": "none",
#             "metadata": {}
#         }]

#     df = pd.DataFrame([
#         {
#             "txn_id": t.id,
#             "date": pd.to_datetime(t.date),
#             "amount": float(t.amount)
#         }
#         for t in transactions
#     ])

#     if df.empty:
#         return [{
#             "detector": "HighRiskTime",
#             "triggered": False,
#             "score": 0,
#             "reason": "No transaction data available.",
#             "transactions_involved": [],
#             "severity": "none",
#             "metadata": {}
#         }]

#     # ==========================================================
#     # CHECK WHETHER ACTUAL TIME DATA EXISTS
#     # ==========================================================
#     has_time_data = (
#         (df["date"].dt.hour != 0) |
#         (df["date"].dt.minute != 0) |
#         (df["date"].dt.second != 0)
#     ).any()

#     results = []

#     # ==========================================================
#     # MODE 1: TIMESTAMP AVAILABLE
#     # ==========================================================
#     if has_time_data:

#         df["hour"] = df["date"].dt.hour

#         df["is_midnight"] = (
#             df["hour"]
#             .between(MIDNIGHT_START, MIDNIGHT_END)
#         )

#         df["is_holiday"] = df["date"].dt.date.isin(
#             INDIA_HOLIDAYS
#         )

#         midnight_txns = df[df["is_midnight"]]

#         cluster_detected = (
#             len(midnight_txns) >= MIN_CLUSTER_SIZE
#         )

#         flagged = df[
#             df["is_midnight"] |
#             df["is_holiday"]
#         ]

#         if flagged.empty:
#             return [{
#                 "detector": "HighRiskTime",
#                 "triggered": False,
#                 "score": 0,
#                 "reason": "No high-risk timing patterns detected.",
#                 "transactions_involved": [],
#                 "severity": "none",
#                 "metadata": {
#                     "analysis_mode": "timestamp"
#                 }
#             }]

#         score = 0
#         reasons = []

#         if len(midnight_txns) > 0:

#             score += 40

#             reasons.append(
#                 f"{len(midnight_txns)} transactions occurred "
#                 f"between 12 AM and 6 AM."
#             )

#         if cluster_detected:

#             score += 20

#             reasons.append(
#                 "Multiple late-night transactions formed "
#                 "a suspicious activity cluster."
#             )

#         holiday_txns = flagged[
#             flagged["is_holiday"]
#         ]

#         if len(holiday_txns) > 0:

#             score += 30

#             reasons.append(
#                 f"{len(holiday_txns)} transactions occurred "
#                 f"on public holidays."
#             )

#         score = min(score, 100)

#         severity = (
#             "critical" if score >= 80
#             else "high" if score >= 60
#             else "medium"
#         )

#         results.append({
#             "detector": "HighRiskTime",
#             "triggered": True,
#             "score": score,
#             "reason": " ".join(reasons),
#             "transactions_involved":
#                 flagged["txn_id"].tolist(),
#             "severity": severity,
#             "metadata": {
#                 "analysis_mode": "timestamp",
#                 "midnight_transactions":
#                     len(midnight_txns),
#                 "holiday_transactions":
#                     len(holiday_txns),
#                 "cluster_detected":
#                     cluster_detected
#             }
#         })

#     # ==========================================================
#     # MODE 2: DATE-ONLY STATEMENTS
#     # ==========================================================
#     else:

#         df["is_holiday"] = df["date"].dt.date.isin(
#             INDIA_HOLIDAYS
#         )

#         df["is_weekend"] = (
#             df["date"].dt.weekday >= 5
#         )

#         holiday_txns = df[df["is_holiday"]]
#         weekend_txns = df[df["is_weekend"]]

#         if holiday_txns.empty and weekend_txns.empty:

#             return [{
#                 "detector": "HighRiskTime",
#                 "triggered": False,
#                 "score": 0,
#                 "reason":
#                     "No suspicious calendar-based patterns detected.",
#                 "transactions_involved": [],
#                 "severity": "none",
#                 "metadata": {
#                     "analysis_mode": "date_only"
#                 }
#             }]

#         score = 0
#         reasons = []

#         if len(holiday_txns) > 0:

#             score += 30

#             reasons.append(
#                 f"{len(holiday_txns)} transactions occurred "
#                 f"on Indian public holidays."
#             )

#         if len(weekend_txns) >= 5:

#             score += 20

#             reasons.append(
#                 "High concentration of transactions "
#                 "during weekends."
#             )

#         if holiday_txns["amount"].sum() >= 100000:

#             score += 20

#             reasons.append(
#                 "Large monetary movement occurred "
#                 "on public holidays."
#             )

#         score = min(score, 100)

#         severity = (
#             "high" if score >= 60
#             else "medium"
#         )

#         results.append({
#             "detector": "HighRiskTime",
#             "triggered": True,
#             "score": score,
#             "reason": " ".join(reasons),
#             "transactions_involved": list(
#                 set(
#                     holiday_txns["txn_id"].tolist()
#                     + weekend_txns["txn_id"].tolist()
#                 )
#             ),
#             "severity": severity,
#             "metadata": {
#                 "analysis_mode": "date_only",
#                 "holiday_transactions":
#                     len(holiday_txns),
#                 "weekend_transactions":
#                     len(weekend_txns)
#             }
#         })

#     return results

import pandas as pd
import holidays
from app.models.transaction import Transaction


# ============================================================================
# CONFIGURATION
# ============================================================================

INDIA_HOLIDAYS = holidays.India()

MIDNIGHT_START = 0      # 12:00 AM
MIDNIGHT_END = 5        # 05:59 AM
MIN_CLUSTER_SIZE = 3
WEEKEND_RATIO_THRESHOLD = 0.40   # 40%


# ============================================================================
# DETECTOR
# ============================================================================

def detect_high_risk_time(case_id: str):

    transactions = (
        Transaction.query
        .filter_by(case_id=case_id, is_failed=False)
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
            "amount": abs(float(t.amount))
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

    # ========================================================================
    # CHECK IF ACTUAL TIME DATA EXISTS
    # ========================================================================

    has_time_data = (
        (df["date"].dt.hour != 0) |
        (df["date"].dt.minute != 0) |
        (df["date"].dt.second != 0)
    ).any()

    # ========================================================================
    # MODE 1: FULL TIMESTAMP AVAILABLE
    # ========================================================================

    if has_time_data:

        df["hour"] = df["date"].dt.hour

        df["is_midnight"] = (
            df["hour"]
            .between(MIDNIGHT_START, MIDNIGHT_END)
        )

        df["is_holiday"] = (
            df["date"]
            .dt.date
            .isin(INDIA_HOLIDAYS)
        )

        midnight_txns = df[df["is_midnight"]]
        holiday_txns = df[df["is_holiday"]]

        cluster_detected = (
            len(midnight_txns)
            >= MIN_CLUSTER_SIZE
        )

        flagged = df[
            df["is_midnight"] |
            df["is_holiday"]
        ]

        if flagged.empty:
            return [{
                "detector": "HighRiskTime",
                "triggered": False,
                "score": 0,
                "reason": "No high-risk timing patterns detected.",
                "transactions_involved": [],
                "severity": "none",
                "metadata": {
                    "analysis_mode": "timestamp"
                }
            }]

        score = 0
        reasons = []

        if len(midnight_txns) > 0:

            score += 40

            reasons.append(
                f"{len(midnight_txns)} transactions occurred "
                f"between 12 AM and 6 AM."
            )

        if cluster_detected:

            score += 20

            reasons.append(
                "Multiple late-night transactions formed "
                "a suspicious activity cluster."
            )

        if len(holiday_txns) > 0:

            score += 30

            reasons.append(
                f"{len(holiday_txns)} transactions occurred "
                f"on Indian public holidays."
            )

        score = min(score, 100)

        severity = (
            "critical" if score >= 80
            else "high" if score >= 60
            else "medium"
        )

        return [{
            "detector": "HighRiskTime",
            "triggered": True,
            "score": score,
            "reason": " ".join(reasons),
            "transactions_involved":
                flagged["txn_id"].tolist(),
            "severity": severity,
            "metadata": {
                "analysis_mode": "timestamp",
                "midnight_transactions":
                    len(midnight_txns),
                "holiday_transactions":
                    len(holiday_txns),
                "cluster_detected":
                    cluster_detected
            }
        }]

    # ========================================================================
    # MODE 2: DATE-ONLY STATEMENTS
    # ========================================================================

    df["is_holiday"] = (
        df["date"]
        .dt.date
        .isin(INDIA_HOLIDAYS)
    )

    df["is_weekend"] = (
        df["date"].dt.weekday >= 5
    )

    holiday_txns = df[df["is_holiday"]]
    weekend_txns = df[df["is_weekend"]]

    weekend_ratio = (
        len(weekend_txns) / len(df)
    )

    # Avoid triggering on accounts with only a few weekend transactions
    if (
        holiday_txns.empty
        and weekend_ratio < WEEKEND_RATIO_THRESHOLD
    ):
        return [{
            "detector": "HighRiskTime",
            "triggered": False,
            "score": 0,
            "reason":
                "No suspicious calendar-based patterns detected.",
            "transactions_involved": [],
            "severity": "none",
            "metadata": {
                "analysis_mode": "date_only",
                "weekend_ratio":
                    round(weekend_ratio, 3)
            }
        }]

    score = 0
    reasons = []

    if len(holiday_txns) > 0:

        score += 30

        reasons.append(
            f"{len(holiday_txns)} transactions "
            f"occurred on Indian public holidays."
        )

        if holiday_txns["amount"].sum() >= 100000:

            score += 20

            reasons.append(
                "Large monetary movement occurred "
                "on public holidays."
            )

    if weekend_ratio >= WEEKEND_RATIO_THRESHOLD:

        score += 20

        reasons.append(
            f"{weekend_ratio:.0%} of transactions "
            f"occurred during weekends."
        )

    score = min(score, 100)

    severity = (
        "high"
        if score >= 60
        else "medium"
    )

    return [{
        "detector": "HighRiskTime",
        "triggered": True,
        "score": score,
        "reason": " ".join(reasons),
        "transactions_involved": list(
            set(
                holiday_txns["txn_id"].tolist()
                + weekend_txns["txn_id"].tolist()
            )
        ),
        "severity": severity,
        "metadata": {
            "analysis_mode": "date_only",
            "holiday_transactions":
                len(holiday_txns),
            "weekend_transactions":
                len(weekend_txns),
            "weekend_ratio":
                round(weekend_ratio, 3)
        }
    }]