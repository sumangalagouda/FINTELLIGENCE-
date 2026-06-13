import pandas as pd

def normalize_column_names(df):
    """
    Normalizes variations of column names into a standard format.
    """
    col_map = {}
    for col in df.columns:
        col_lower = str(col).lower().strip()
        
        # Date
        if col_lower in ['date', 'value date', 'txn date', 'transaction date', 'tran date']:
            col_map[col] = 'Date'
        # Description
        elif col_lower in ['description', 'narration', 'particulars', 'remarks']:
            col_map[col] = 'Description'
        # Amount (Combined)
        elif col_lower in ['amount']:
            col_map[col] = 'Amount'
        # Credit
        elif col_lower in ['cr', 'deposit', 'credit', 'deposit amount']:
            col_map[col] = 'Credit'
        # Debit
        elif col_lower in ['dr', 'withdrawal', 'debit', 'withdrawal amount']:
            col_map[col] = 'Debit'
        # Balance
        elif col_lower in ['balance', 'closing balance', 'bal']:
            col_map[col] = 'Balance'
            
    return df.rename(columns=col_map)

def parse_csv_excel(file_path):
    """
    Parses CSV or Excel file and returns raw transactions.
    """
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)
        
    df = normalize_column_names(df)
    
    raw_transactions = []
    for _, row in df.iterrows():
        # Convert row to dictionary, dropping NaNs
        row_dict = row.dropna().to_dict()
        if not row_dict:
            continue
            
        raw_transactions.append({
            'raw_text': str(row_dict),
            'parsed_data': row_dict
        })
        
    return 'UNKNOWN', raw_transactions # Bank detection might require looking at file name or content
