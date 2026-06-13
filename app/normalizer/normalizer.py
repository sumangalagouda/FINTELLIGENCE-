import uuid
from datetime import datetime
from dateutil import parser as date_parser

def process_and_normalize(raw_transactions, statement_id, case_id):
    """
    Takes raw parser output and standardizes it into the canonical schema.
    """
    normalized_txns = []
    
    for raw_txn in raw_transactions:
        # In a real system, you would have bank-specific mapping logic here.
        # This is a generic stub representing the normalizer rules.
        parsed = raw_txn.get('parsed_data', {})
        
        # Stub logic to extract fields
        amount = 0.0
        txn_type = 'debit'
        date_str = '2000-01-01'
        description = raw_txn.get('raw_text', '')
        
        if isinstance(parsed, dict):
            # Try to map from dictionary (like CSV/Excel output)
            if 'Credit' in parsed:
                amount = float(parsed['Credit'])
                txn_type = 'credit'
            elif 'Debit' in parsed:
                amount = float(parsed['Debit'])
                txn_type = 'debit'
            elif 'Amount' in parsed:
                amt = float(parsed['Amount'])
                amount = abs(amt)
                txn_type = 'credit' if amt > 0 else 'debit'
                
            if 'Date' in parsed:
                date_str = str(parsed['Date'])
            if 'Description' in parsed:
                description = str(parsed['Description'])
                
        # 1. Normalize Date (YYYY-MM-DD)
        try:
            parsed_date = date_parser.parse(date_str).strftime('%Y-%m-%d')
        except:
            parsed_date = None

        # 2. Descriptions stripped
        clean_desc = " ".join(description.split())
        
        # 3. Create canonical dict
        canonical_txn = {
            "txn_id": str(uuid.uuid4()),
            "statement_id": statement_id,
            "case_id": case_id,
            "date": parsed_date,
            "amount": amount,
            "type": txn_type,
            "sender_account": None, # Logic to extract from description
            "receiver_account": None,
            "description": clean_desc,
            "balance_after": 0.0, # Logic to extract
            "raw_text": raw_txn.get('raw_text', '')
        }
        
        normalized_txns.append(canonical_txn)
        
    return normalized_txns
