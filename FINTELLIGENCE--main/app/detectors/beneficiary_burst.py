import pandas as pd
from app.models.transaction import Transaction

def detect_beneficiary_burst(case_id: str):
    transactions = Transaction.query.filter_by(case_id=case_id, is_failed=False).order_by(Transaction.date).all()
    if not transactions:
        return []

    # Need timestamp for 24H rolling. If 'date' is just Date, we assume 00:00:00 or parse if it has time.
    # In Fintelligence, 'date' is usually Date but could be datetime. Let's ensure it's datetime.
    df = pd.DataFrame([{
        'txn_id': t.id,
        'sender_account': t.sender_account,
        'receiver_account': t.receiver_account,
        'amount': t.amount,
        'timestamp': pd.to_datetime(t.date) # If date only, this treats it as midnight
    } for t in transactions if t.sender_account and t.receiver_account])

    if df.empty:
        return []

    df = df.sort_values(by=['sender_account', 'timestamp'])
    
    # Identify first time a beneficiary appears for a sender
    df['is_new_beneficiary'] = ~df.duplicated(subset=['sender_account', 'receiver_account'])
    
    has_time_data = (
        (df["timestamp"].dt.hour != 0) |
        (df["timestamp"].dt.minute != 0) |
        (df["timestamp"].dt.second != 0)
    ).any()

    results = []

    if has_time_data:
        # --------------------------------------------------
        # Rolling 24H Mode
        # --------------------------------------------------
        df = df.set_index('timestamp')
        df['new_beneficiaries_count'] = df.groupby('sender_account')['is_new_beneficiary'].transform(
            lambda x: x.rolling('24h').sum()
        )
        df['amount_dispersed'] = df.groupby('sender_account')['amount'].transform(
            lambda x: x.rolling('24h').sum()
        )
        df = df.reset_index()

        flagged = df[df['new_beneficiaries_count'] >= 5.0].copy()

        for sender, group in flagged.groupby('sender_account'):
            # Get the peak burst row
            peak_row = group.loc[group['new_beneficiaries_count'].idxmax()]
            
            count = int(peak_row['new_beneficiaries_count'])
            amt = peak_row['amount_dispersed']
            
            if count < 10 and amt < 10000:
                continue
            
            score = min(100, 60 + ((count - 5) * 5))
            
            end_time = peak_row['timestamp']
            start_time = end_time - pd.Timedelta(hours=24)
            
            involved_txns = df[
                (df['sender_account'] == sender) &
                (df['timestamp'] > start_time) &
                (df['timestamp'] <= end_time) &
                (df['is_new_beneficiary'])
            ]['txn_id'].tolist()

            results.append({
                "detector": "BeneficiaryBurst",
                "triggered": True,
                "score": score,
                "reason": f"{count} new beneficiaries paid within 24 hours. Total dispersed: ₹{amt:,.2f}",
                "transactions_involved": involved_txns,
                "severity": "high" if score >= 80 else "medium",
                "metadata": {
                    "new_beneficiaries_count": count,
                    "amount_dispersed": amt,
                    "analysis_mode": "rolling_24h"
                }
            })
    else:
        # --------------------------------------------------
        # Calendar-Day Mode (Fallback)
        # --------------------------------------------------
        df['date_only'] = df['timestamp'].dt.date
        
        # Group by sender and date, counting only new beneficiaries
        daily_stats = df[df['is_new_beneficiary']].groupby(['sender_account', 'date_only']).agg(
            new_beneficiaries_count=('is_new_beneficiary', 'sum'),
            amount_dispersed=('amount', 'sum'),
            txn_ids=('txn_id', list)
        ).reset_index()

        flagged = daily_stats[daily_stats['new_beneficiaries_count'] >= 5].copy()

        for _, row in flagged.iterrows():
            sender = row['sender_account']
            count = int(row['new_beneficiaries_count'])
            amt = row['amount_dispersed']
            
            if count < 10 and amt < 10000:
                continue

            score = min(100, 60 + ((count - 5) * 5))
            
            results.append({
                "detector": "BeneficiaryBurst",
                "triggered": True,
                "score": score,
                "reason": f"{count} new beneficiaries paid on {row['date_only']}. Total dispersed: ₹{amt:,.2f}",
                "transactions_involved": row['txn_ids'],
                "severity": "high" if score >= 80 else "medium",
                "metadata": {
                    "new_beneficiaries_count": count,
                    "amount_dispersed": amt,
                    "analysis_mode": "calendar_day",
                    "data_quality": "date_only"
                }
            })

    return results
