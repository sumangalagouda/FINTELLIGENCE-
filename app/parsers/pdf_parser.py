import pdfplumber
import fitz  # PyMuPDF
import camelot
import re

def detect_bank(text):
    text_lower = text.lower()
    if 'hdfc bank' in text_lower:
        return 'HDFC'
    elif 'icici bank' in text_lower:
        return 'ICICI'
    elif 'state bank of india' in text_lower or 'sbi' in text_lower:
        return 'SBI'
    elif 'axis bank' in text_lower:
        return 'AXIS'
    return 'UNKNOWN'

def parse_pdf(file_path):
    """
    Parses PDF using pdfplumber as primary, fallback to PyMuPDF/camelot.
    Returns: bank_name, list of raw transactions
    """
    bank_name = 'UNKNOWN'
    raw_transactions = []
    
    try:
        with pdfplumber.open(file_path) as pdf:
            # Extract header text from first page to detect bank
            first_page_text = pdf.pages[0].extract_text()
            if first_page_text:
                bank_name = detect_bank(first_page_text)
            
            # Simple extraction strategy
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        # Clean row and ignore empty
                        cleaned_row = [str(cell).strip() if cell else '' for cell in row]
                        if any(cleaned_row):
                            raw_transactions.append({
                                'raw_text': ' | '.join(cleaned_row),
                                'parsed_data': cleaned_row
                            })
                            
    except Exception as e:
        print(f"pdfplumber failed: {str(e)}, trying camelot...")
        # Fallback to camelot for complex tables
        tables = camelot.read_pdf(file_path, pages='all', flavor='stream')
        for table in tables:
            df = table.df
            for _, row in df.iterrows():
                row_list = row.tolist()
                cleaned_row = [str(cell).strip() for cell in row_list]
                if any(cleaned_row):
                    raw_transactions.append({
                        'raw_text': ' | '.join(cleaned_row),
                        'parsed_data': cleaned_row
                    })

    return bank_name, raw_transactions
