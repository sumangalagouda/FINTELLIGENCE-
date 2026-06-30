# import pandas as pd
# from app.models.transaction import Transaction

# def detect_beneficiary_burst(case_id: str):
#     transactions = Transaction.query.filter_by(case_id=case_id, is_failed=False).order_by(Transaction.date).all()
#     if not transactions:
#         return []

#     # Need timestamp for 24H rolling. If 'date' is just Date, we assume 00:00:00 or parse if it has time.
#     # In Fintelligence, 'date' is usually Date but could be datetime. Let's ensure it's datetime.
#     df = pd.DataFrame([{
#         'txn_id': t.id,
#         'sender_account': t.sender_account,
#         'receiver_account': t.receiver_account,
#         'amount': t.amount,
#         'timestamp': pd.to_datetime(t.date) # If date only, this treats it as midnight
#     } for t in transactions if t.sender_account and t.receiver_account])

#     if df.empty:
#         return []

#     df = df.sort_values(by=['sender_account', 'timestamp'])
    
#     # Identify first time a beneficiary appears for a sender
#     df['is_new_beneficiary'] = ~df.duplicated(subset=['sender_account', 'receiver_account'])
    
#     has_time_data = (
#         (df["timestamp"].dt.hour != 0) |
#         (df["timestamp"].dt.minute != 0) |
#         (df["timestamp"].dt.second != 0)
#     ).any()

#     results = []

#     if has_time_data:
#         # --------------------------------------------------
#         # Rolling 24H Mode
#         # --------------------------------------------------
#         df = df.set_index('timestamp')
#         df['new_beneficiaries_count'] = df.groupby('sender_account')['is_new_beneficiary'].transform(
#             lambda x: x.rolling('24h').sum()
#         )
#         df['amount_dispersed'] = df.groupby('sender_account')['amount'].transform(
#             lambda x: x.rolling('24h').sum()
#         )
#         df = df.reset_index()

#         flagged = df[df['new_beneficiaries_count'] >= 5.0].copy()

#         for sender, group in flagged.groupby('sender_account'):
#             # Get the peak burst row
#             peak_row = group.loc[group['new_beneficiaries_count'].idxmax()]
            
#             count = int(peak_row['new_beneficiaries_count'])
#             amt = peak_row['amount_dispersed']
            
#             if count < 10 and amt < 10000:
#                 continue
            
#             score = min(100, 60 + ((count - 5) * 5))
            
#             end_time = peak_row['timestamp']
#             start_time = end_time - pd.Timedelta(hours=24)
            
#             involved_txns = df[
#                 (df['sender_account'] == sender) &
#                 (df['timestamp'] > start_time) &
#                 (df['timestamp'] <= end_time) &
#                 (df['is_new_beneficiary'])
#             ]['txn_id'].tolist()

#             results.append({
#                 "detector": "BeneficiaryBurst",
#                 "triggered": True,
#                 "score": score,
#                 "reason": f"{count} new beneficiaries paid within 24 hours. Total dispersed: ₹{amt:,.2f}",
#                 "transactions_involved": involved_txns,
#                 "severity": "high" if score >= 80 else "medium",
#                 "metadata": {
#                     "new_beneficiaries_count": count,
#                     "amount_dispersed": amt,
#                     "analysis_mode": "rolling_24h"
#                 }
#             })
#     else:
#         # --------------------------------------------------
#         # Calendar-Day Mode (Fallback)
#         # --------------------------------------------------
#         df['date_only'] = df['timestamp'].dt.date
        
#         # Group by sender and date, counting only new beneficiaries
#         daily_stats = df[df['is_new_beneficiary']].groupby(['sender_account', 'date_only']).agg(
#             new_beneficiaries_count=('is_new_beneficiary', 'sum'),
#             amount_dispersed=('amount', 'sum'),
#             txn_ids=('txn_id', list)
#         ).reset_index()

#         flagged = daily_stats[daily_stats['new_beneficiaries_count'] >= 5].copy()

#         for _, row in flagged.iterrows():
#             sender = row['sender_account']
#             count = int(row['new_beneficiaries_count'])
#             amt = row['amount_dispersed']
            
#             if count < 10 and amt < 10000:
#                 continue

#             score = min(100, 60 + ((count - 5) * 5))
            
#             results.append({
#                 "detector": "BeneficiaryBurst",
#                 "triggered": True,
#                 "score": score,
#                 "reason": f"{count} new beneficiaries paid on {row['date_only']}. Total dispersed: ₹{amt:,.2f}",
#                 "transactions_involved": row['txn_ids'],
#                 "severity": "high" if score >= 80 else "medium",
#                 "metadata": {
#                     "new_beneficiaries_count": count,
#                     "amount_dispersed": amt,
#                     "analysis_mode": "calendar_day",
#                     "data_quality": "date_only"
#                 }
#             })

#     return results
# import re
# import pandas as pd
# from app.models.transaction import Transaction


# def extract_beneficiary(receiver, description):
#     if receiver:
#         return receiver

#     if not description:
#         return None

#     patterns = [
#         r"UPI/(?:DR|CR)/[^/]+/([^/]+)/",
#         r"IMPS/[^/]+/[^-]+-([^/]+)/",
#         r"NEFT\*[^*]+\*[^*]+\*([^*]+)"
#     ]

#     for pattern in patterns:
#         match = re.search(pattern, description)
#         if match:
#             return match.group(1).strip().upper()

#     return None


# def detect_beneficiary_burst(case_id):

#     txns = (
#         Transaction.query
#         .filter_by(case_id=case_id, is_failed=False)
#         .order_by(Transaction.date)
#         .all()
#     )

#     if not txns:
#         return []

#     rows = []

#     for t in txns:

#         beneficiary = extract_beneficiary(
#             t.receiver_account,
#             t.description
#         )

#         if not beneficiary:
#             continue

#         rows.append({
#             "txn_id": t.id,
#             "sender": t.sender_account or "UNKNOWN",
#             "beneficiary": beneficiary,
#             "amount": abs(t.amount),
#             "timestamp": pd.to_datetime(t.date)
#         })

#     df = pd.DataFrame(rows)

#     if df.empty:
#         return []

#     df = df.sort_values(["sender", "timestamp"])

#     df["is_new"] = ~df.duplicated(
#         subset=["sender", "beneficiary"]
#     )

#     df["date_only"] = df["timestamp"].dt.date

#     daily = (
#         df[df["is_new"]]
#         .groupby(["sender", "date_only"])
#         .agg(
#             beneficiary_count=("beneficiary", "nunique"),
#             total_amount=("amount", "sum"),
#             txn_ids=("txn_id", list)
#         )
#         .reset_index()
#     )

#     results = []

#     flagged = daily[
#         (daily["beneficiary_count"] >= 4) |
#         (daily["total_amount"] >= 5000)
#     ]

#     for _, row in flagged.iterrows():

#         score = min(
#             100,
#             50 + row["beneficiary_count"] * 5
#         )

#         results.append({
#             "detector": "BeneficiaryBurst",
#             "triggered": True,
#             "score": int(score),
#             "severity": (
#                 "critical"
#                 if score >= 90
#                 else "high"
#             ),
#             "reason":
#                 f"{row['beneficiary_count']} new "
#                 f"beneficiaries on "
#                 f"{row['date_only']} "
#                 f"(₹{row['total_amount']:,.2f}).",
#             "transactions_involved":
#                 row["txn_ids"],
#             "metadata": {
#                 "beneficiary_count":
#                     int(row["beneficiary_count"]),
#                 "total_amount":
#                     float(row["total_amount"])
#             }
#         })

#     return results

import re
import pandas as pd
from app.models.transaction import Transaction


MIN_BENEFICIARIES = 4
MIN_DISPERSED_AMOUNT = 5000


def extract_beneficiary(receiver_account, description):

    if receiver_account:
        return receiver_account.strip().upper()

    if not description:
        return None

    patterns = [
        r"UPI/(?:DR|CR)/[^/]+/([^/]+)/",
        r"IMPS/[^/]+/[^/]+/([^/]+)/?",
        r"NEFT.*?([A-Z ]{3,})"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            description.upper()
        )

        if match:
            return match.group(1).strip()

    return None


def detect_beneficiary_burst(case_id: str):

    transactions = (
        Transaction.query
        .filter_by(case_id=case_id, is_failed=False)
        .order_by(Transaction.date)
        .all()
    )

    if not transactions:
        return []

    rows = []

    for t in transactions:

        beneficiary = extract_beneficiary(
            t.receiver_account,
            t.description
        )

        if not beneficiary:
            continue

        rows.append({
            "txn_id": t.id,
            "sender": t.sender_account or "UNKNOWN",
            "beneficiary": beneficiary,
            "amount": abs(float(t.amount)),
            "timestamp": pd.to_datetime(t.date)
        })

    df = pd.DataFrame(rows)

    if df.empty:
        return []

    df = df.sort_values(
        ["sender", "timestamp"]
    )

    df["is_new"] = ~df.duplicated(
        subset=["sender", "beneficiary"]
    )

    df["date_only"] = df["timestamp"].dt.date

    daily = (
        df[df["is_new"]]
        .groupby(["sender", "date_only"])
        .agg(
            beneficiary_count=(
                "beneficiary",
                "nunique"
            ),
            amount_dispersed=(
                "amount",
                "sum"
            ),
            txn_ids=(
                "txn_id",
                list
            )
        )
        .reset_index()
    )

    results = []

    flagged = daily[
        (daily["beneficiary_count"] >= MIN_BENEFICIARIES)
        &
        (daily["amount_dispersed"] >= MIN_DISPERSED_AMOUNT)
    ]

    for _, row in flagged.iterrows():

        score = min(
            100,
            50 + row["beneficiary_count"] * 5
        )

        results.append({
            "detector": "BeneficiaryBurst",
            "triggered": True,
            "score": int(score),
            "severity":
                "critical"
                if score >= 90
                else "high",
            "reason":
                f"{row['beneficiary_count']} "
                f"new beneficiaries "
                f"were paid on "
                f"{row['date_only']} "
                f"(₹{row['amount_dispersed']:,.2f}).",
            "transactions_involved":
                row["txn_ids"],
            "metadata": {
                "beneficiary_count":
                    int(
                        row["beneficiary_count"]
                    ),
                "amount_dispersed":
                    float(
                        row["amount_dispersed"]
                    ),
                "analysis_mode":
                    "calendar_day"
            }
        })

    return results