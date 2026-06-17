import pandas as pd
from app.models.transaction import Transaction

def detect_beneficiary_burst(case_id: str):
    transactions = Transaction.query.filter_by(case_id=case_id).order_by(Transaction.date).all()
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
    
    # Rolling 24H window to count new beneficiaries
    df = df.set_index('timestamp')
    df['new_beneficiaries_24h'] = df.groupby('sender_account')['is_new_beneficiary'].transform(
        lambda x: x.rolling('24h').sum()
    )
    df['total_amount_24h'] = df.groupby('sender_account')['amount'].transform(
        lambda x: x.rolling('24h').sum()
    )
    df = df.reset_index()

    # Flag if 5+ new beneficiaries in 24h
    flagged = df[df['new_beneficiaries_24h'] >= 5.0].copy()

    results = []
    # Group by sender to aggregate burst events (avoiding reporting every single txn in the burst)
    for sender, group in flagged.groupby('sender_account'):
        # Get the peak burst row
        peak_row = group.loc[group['new_beneficiaries_24h'].idxmax()]
        
        count = int(peak_row['new_beneficiaries_24h'])
        amt = peak_row['total_amount_24h']
        
        # Base score 60, +5 for each additional over 5
        score = 60 + ((count - 5) * 5)
        
        # Cap score at 100
        score = min(100, score)

        # Find all transactions involved in this 24H peak window
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
                "amount_dispersed": amt
            }
        })

    return results
