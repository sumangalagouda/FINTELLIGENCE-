import os
import re
from typing import List, Optional, Tuple

import pandas as pd
from dateutil import parser as dateparser

try:
    import pdfplumber
except Exception:
    pdfplumber = None


# ---------------------------------------------------------------------------
# Bank mapping by IFSC prefix
# ---------------------------------------------------------------------------
BANK_MAP = {
    'SBIN': 'State Bank of India',
    'HDFC': 'HDFC Bank',
    'ICIC': 'ICICI Bank',
    'UTIB': 'Axis Bank',
    'KKBK': 'Kotak Mahindra Bank',
    'BARB': 'Bank of Baroda',
    'PUNB': 'Punjab National Bank',
    'CNRB': 'Canara Bank',
    'UBIN': 'Union Bank of India',
    'YESB': 'Yes Bank',
    'IDFB': 'IDFC First Bank',
    'IDBI': 'IDBI Bank',
    'INDB': 'IndusInd Bank',
    'BKID': 'Bank of India',
    'MAHB': 'Bank of Maharashtra',
    'FDRL': 'Federal Bank',
    'KARB': 'Karnataka Bank',
    'KVBL': 'Karur Vysya Bank',
    'SIBL': 'South Indian Bank',
    'TMBL': 'Tamilnad Mercantile Bank',
    'PAYTM': 'Paytm Payments Bank',
    'FINO': 'Fino Payments Bank',
    'AIRP': 'Airtel Payments Bank',
}

# ---------------------------------------------------------------------------
# Failure keyword → canonical reason mapping (order matters for priority)
# ---------------------------------------------------------------------------
FAIL_KEYWORDS = {
    'INSUF':               'INSUFFICIENT FUNDS',
    'INSUFFICIENT':        'INSUFFICIENT FUNDS',
    'ACCOUNT CLOSED':      'ACCOUNT CLOSED',
    'A/C CLOSED':          'ACCOUNT CLOSED',
    'INVALID ACCOUNT':     'INVALID ACCOUNT',
    'WRONG ACCOUNT':       'INVALID ACCOUNT',
    'BENEFICIARY REJECTED':'BENEFICIARY REJECTED',
    'TECHNICAL':           'TECHNICAL FAILURE',
    'SYSTEM ERROR':        'TECHNICAL FAILURE',
    'ECS RETURN':          'RETURNED',
    'ACH RETURN':          'RETURNED',
    'NEFT RETURN':         'RETURNED',
    'BUNCH_RETURN':        'RETURNED',
    'RETURN':              'RETURNED',
    'RTN':                 'RETURNED',
    'RTRN':                'RETURNED',
    'BOUNCE':              'BOUNCED',
    'DISHONOURED':         'BOUNCED',
    'DISHONOUR':           'BOUNCED',
    'REJECTED':            'BENEFICIARY REJECTED',
    'FAILED':              'OTHER',
    'REVERSAL':            'OTHER',
    'REVERSED':            'OTHER',
    'NOT PROCESSED':       'OTHER',
    'DECLINED':            'OTHER',
    'LIEN':                'OTHER',
}

# ---------------------------------------------------------------------------
# FIX #3 — IFSC extraction: no word-boundary so it also finds IFSC codes
# embedded inside narrations like "NEFT CR-HDFC0001234-NAME"
# ---------------------------------------------------------------------------
def _extract_ifsc_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    # Standard IFSC: 4 letters + 0 + 6 alphanumeric (11 chars total)
    m = re.search(r'([A-Z]{4}0[0-9A-Z]{6})', text)
    if m:
        return m.group(1)
    # Fallback: 4 letters + 7 digits (some bank print variants)
    m = re.search(r'([A-Z]{4}\d{7})', text)
    if m:
        return m.group(1)
    return None


def _bank_name_from_ifsc(ifsc: Optional[str]) -> str:
    if not ifsc:
        return 'UNKNOWN'
    prefix = ifsc[:4]
    return BANK_MAP.get(prefix, 'UNKNOWN')


def _parse_amount(val) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        v = float(val)
        return None if (v == 0.0 and val == '') else v
    s = str(val).strip()
    if not s:
        return None
    # Remove currency symbols and commas
    s = (s.replace('₹', '')
          .replace('INR', '')
          .replace(',', '')
          .replace('\u20B9', '')
          .strip())
    # Parentheses indicate negative
    negative = False
    if s.startswith('(') and s.endswith(')'):
        negative = True
        s = s[1:-1]
    # Trailing DR/CR markers
    if s.upper().endswith('DR'):
        negative = True
        s = s[:-2]
    if s.upper().endswith('CR'):
        s = s[:-2]
    s = s.strip()
    try:
        num = float(s)
        return -num if negative else num
    except Exception:
        return None


def _parse_date(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = str(s).strip()
    if not s:
        return None
    try:
        dt = dateparser.parse(s, dayfirst=True, fuzzy=True)
        if dt:
            return dt.date().isoformat()
        return None
    except Exception:
        return None


def _parse_time(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = str(s).strip()
    if not s:
        return None
    try:
        dt = dateparser.parse(s, fuzzy=True)
        if dt:
            return dt.time().strftime('%H:%M:%S')
        return None
    except Exception:
        return None


def _detect_failure(description: str) -> Tuple[bool, Optional[str]]:
    if not description:
        return False, None
    desc = description.upper()
    found = []
    for key, mapped in FAIL_KEYWORDS.items():
        if key in desc:
            found.append((key, mapped))
    if not found:
        return False, None
    # Prefer first non-OTHER match
    for _k, mapped in found:
        if mapped != 'OTHER':
            return True, mapped
    return True, found[0][1]


def _standardize_columns(cols: List[str]) -> List[str]:
    return [str(c).strip().lower() for c in cols]


def _find_column(df_cols: List[str], candidates: List[str]) -> Optional[str]:
    cols = _standardize_columns(df_cols)
    for cand in candidates:
        for i, c in enumerate(cols):
            if cand in c:
                return df_cols[i]
    return None


# ---------------------------------------------------------------------------
# FIX #7 — PDF table extraction handles continuation pages (no header row)
# ---------------------------------------------------------------------------
def _dataframe_from_pdf(path: str) -> pd.DataFrame:
    if pdfplumber is None:
        return pd.DataFrame()

    header_cols = None
    all_rows: List[List] = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            try:
                page_tables = page.extract_tables()
            except Exception:
                continue
            if not page_tables:
                continue

            for table in page_tables:
                if not table or len(table) < 2:
                    continue

                header_row = table[0]
                header_low = ' '.join(
                    [str(h).lower() if h else '' for h in header_row]
                )

                is_txn_header = any(
                    k in header_low
                    for k in ['date', 'value date', 'description',
                               'narration', 'withdrawal', 'deposit',
                               'debit', 'credit', 'balance']
                )

                if is_txn_header:
                    # First or repeated header page
                    if header_cols is None:
                        header_cols = header_row
                    # Add data rows (skip header row itself)
                    all_rows.extend(table[1:])
                elif header_cols is not None:
                    # Continuation page — no header, same column count
                    if len(table[0]) == len(header_cols):
                        all_rows.extend(table)
                    else:
                        # Try all rows that match column count
                        for row in table:
                            if len(row) == len(header_cols):
                                all_rows.append(row)

    if header_cols is None or not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows, columns=header_cols)
    return df

# ---------------------------------------------------------------------------
# Fallback Regex Text Parser for Complex Bank PDFs
# ---------------------------------------------------------------------------
def _regex_parse_pdf(file_path: str, bank_name: str) -> pd.DataFrame:
    """
    Reads the PDF using layout=True to preserve spacing, and extracts rows 
    using regex based on the bank's known column layout.
    """
    if pdfplumber is None:
        return pd.DataFrame()
        
    bank_name = str(bank_name).upper()
    
    # Define expected columns based on bank
    if 'CANARA' in bank_name:
        # CANARA: DATE | PARTICULARS | DEPOSITS (CR) | WITHDRAWALS (DR) | BALANCE
        debit_idx, credit_idx = 1, 0
    else:
        # SBI, BOB, PNB default: DEBIT | CREDIT | BALANCE
        debit_idx, credit_idx = 0, 1

    extracted_rows = []
    current_row = None
    
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=True)
            if not text:
                continue
                
            for line in text.split('\n'):
                # Strip excessive trailing spaces but keep internal spacing
                line = line.rstrip()
                if not line:
                    continue
                    
                # Match start of a transaction row (Date)
                # Formats: DD/MM/YYYY, DD-MM-YYYY, DD/MM/YY
                date_match = re.match(r'^\s*(\d{2}[/-]\d{2}[/-]\d{2,4})\s+(.*)', line)
                
                if date_match:
                    # Save previous row
                    if current_row:
                        extracted_rows.append(current_row)
                        
                    date_str = date_match.group(1)
                    remainder = date_match.group(2)
                    
                    # Some banks (SBI) have a Post Date immediately following the Value Date.
                    # We can optionally strip it if it perfectly matches a date again.
                    second_date_match = re.match(r'^(\d{2}[/-]\d{2}[/-]\d{2,4})\s+(.*)', remainder)
                    if second_date_match:
                        remainder = second_date_match.group(2)
                    
                    # Extract amounts from the end of the line
                    # Look for 1 or more amounts: e.g. " 50.00   1,450.72 " or " 50.00 Cr "
                    amounts = re.findall(r'([0-9]{1,3}(?:,[0-9]{2,3})*\.\d{2}\s*(?:Cr|Dr|CR|DR|cr|dr)?)', remainder)
                    
                    debit = ''
                    credit = ''
                    balance = ''
                    
                    if amounts:
                        # Remove amounts from the description
                        for amt in amounts:
                            remainder = remainder.replace(amt, '')
                        
                        # Process amounts based on bank format
                        if len(amounts) >= 2:
                            balance = amounts[-1]
                            amt_val = amounts[-2]
                            
                            # Determine if amt_val is Debit or Credit based on position
                            # To do this correctly, we check the index of amt_val in the original string
                            # compared to the middle of the empty space. But a simpler heuristic:
                            # If the original line has 2 distinct columns of numbers before balance, 
                            # we assign it to debit_idx or credit_idx based on Bank format.
                            # Since spaces are preserved by layout=True, we can split by multiple spaces:
                            parts = re.split(r'\s{3,}', line.strip())
                            # Grab the last 3 parts (which are usually the amounts)
                            trailing = parts[-3:] if len(parts) >= 3 else parts
                            
                            # If trailing has 3 items that look like numbers:
                            if len(trailing) == 3 and all(re.search(r'\d+\.\d{2}', p) for p in trailing):
                                debit = trailing[debit_idx]
                                credit = trailing[credit_idx]
                                balance = trailing[2]
                            else:
                                # We only have 1 transaction amount and a balance.
                                # Check if it explicitly says Cr or Dr
                                if 'Cr' in amt_val or 'CR' in amt_val:
                                    credit = amt_val.replace('Cr', '').replace('CR', '').strip()
                                elif 'Dr' in amt_val or 'DR' in amt_val:
                                    debit = amt_val.replace('Dr', '').replace('DR', '').strip()
                                else:
                                    # We have to guess based on standard column alignment
                                    # If the amount is closer to the end, it's probably Credit
                                    # For now, default to Debit as it's more common, unless CANARA
                                    if 'CANARA' in bank_name:
                                        debit = amt_val  # Withdrawals
                                    else:
                                        debit = amt_val  # SBI, BOB, PNB
                    
                    current_row = {
                        'Date': date_str,
                        'Description': remainder.strip(),
                        'Debit': debit,
                        'Credit': credit,
                        'Balance': balance
                    }
                else:
                    # Not a date row. If we have a current_row, this is a multi-line description.
                    if current_row and not re.match(r'^\s*Page\s+\d+', line, re.IGNORECASE):
                        current_row['Description'] += ' ' + line.strip()
                        
    if current_row:
        extracted_rows.append(current_row)
        
    if not extracted_rows:
        return pd.DataFrame()
        
    df = pd.DataFrame(extracted_rows)
    # Ensure columns map perfectly to _rows_from_dataframe expected formats
    df.rename(columns={'Date': 'txn date', 'Description': 'description', 'Debit': 'debit', 'Credit': 'credit', 'Balance': 'balance'}, inplace=True)
    return df



def _dataframe_from_spreadsheet(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == '.csv':
            df = pd.read_csv(path, dtype=str, keep_default_na=False)
        else:
            df = pd.read_excel(path, dtype=str)
        return df
    except Exception:
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# FIX #1 — time column detection now uses _find_column (case-insensitive)
# FIX #2 — _detect_failure called ONCE here; extract_statement does NOT
#            re-run it so the result is preserved correctly
# ---------------------------------------------------------------------------
def _rows_from_dataframe(df: pd.DataFrame) -> List[dict]:
    if df is None or df.empty:
        return []

    cols = list(df.columns)

    date_col       = _find_column(cols, ['txn date', 'transaction date', 'date', 'tran date'])
    value_date_col = _find_column(cols, ['value date', 'value_date', 'val date'])
    desc_col       = _find_column(cols, ['description', 'narration', 'particulars', 'remarks', 'details'])
    debit_col      = _find_column(cols, ['debit', 'withdrawal', 'dr', 'amount withdrawn', 'withdraw'])
    credit_col     = _find_column(cols, ['credit', 'deposit', 'cr', 'amount credited', 'deposited'])
    balance_col    = _find_column(cols, ['balance', 'running balance', 'closing balance', 'bal'])
    ref_col        = _find_column(cols, ['ref', 'reference', 'utr', 'cheque', 'rrn', 'chq', 'instrument'])
    serial_col     = _find_column(cols, ['sl', 's.no', 'sr.', 'sr no', 'sno', 'serial'])

    # FIX #1: use _find_column for time detection
    time_col = _find_column(cols, ['time'])

    rows = []
    gen_idx = 1

    for _idx, r in df.iterrows():
        row = r.to_dict()

        # txn_id
        raw_serial = str(row.get(serial_col, '')).strip() if serial_col else ''
        if raw_serial and raw_serial not in ('nan', 'None', ''):
            txn_id = raw_serial
        else:
            txn_id = f"TXN_{gen_idx:03d}"
            gen_idx += 1

        date        = _parse_date(row.get(date_col)) if date_col else None
        # FIX #1: time_col is now properly resolved
        time        = _parse_time(row.get(time_col)) if time_col else None
        value_date  = _parse_date(row.get(value_date_col)) if value_date_col else None
        description = row.get(desc_col, '') if desc_col else ''
        if description is None:
            description = ''

        debit    = _parse_amount(row.get(debit_col)) if debit_col else None
        credit   = _parse_amount(row.get(credit_col)) if credit_col else None
        balance  = _parse_amount(row.get(balance_col)) if balance_col else None
        reference = row.get(ref_col) if ref_col else None

        # FIX #2: detect failure exactly once here
        is_failed, failure_reason = _detect_failure(str(description))

        rows.append({
            'txn_id':         txn_id,
            'date':           date,
            'time':           time,
            'value_date':     value_date,
            'description':    str(description),
            'debit':          debit,
            'credit':         credit,
            'balance':        balance,
            'reference_no':   str(reference).strip() if reference and str(reference).strip() not in ('nan', 'None', '') else None,
            'is_failed':      bool(is_failed),
            'failure_reason': failure_reason if is_failed else None,
        })

    return rows


# ---------------------------------------------------------------------------
# Header extraction helpers
# ---------------------------------------------------------------------------

# FIX #4 — account holder name: covers all Indian bank label variants
#           including "Account Name", bare "Name:", salutation-prefixed names
#           like "MR. RAMESH KUMAR", and "Shri/Smt" prefixes
def _extract_account_holder(text: str) -> Optional[str]:
    specific_patterns = [
        r'Account\s*Holder(?:\s*Name)?',     # Account Holder / Account Holder Name
        r'Name\s*of\s*Account\s*Holder',     # Name of Account Holder
        r'Account\s*Name',                    # Account Name
        r'A/?C\s*(?:Holder\s*)?Name',         # A/C Name / AC Holder Name
        r'Customer\s*Name',                   # Customer Name
        r'Holder\s*Name',                     # Holder Name
    ]

    for pat in specific_patterns:
        m = re.search(
            pat + r'[:\s]+([A-Za-z][A-Za-z\s\.\-&,]{2,60})',
            text, re.IGNORECASE
        )
        if m:
            name = m.group(1).strip()
            name = re.split(r'\s{3,}|\n|[|/]', name)[0].strip()
            if len(name) >= 3:
                return name

    # Bare "Name:" — last priority, and only at the start of a line so it
    # doesn't match "...Name" embedded inside Branch/Bank/Address/etc. text
    m = re.search(
        r'^\s*Name[:\s]+([A-Za-z][A-Za-z\s\.\-&,]{2,60})',
        text, re.IGNORECASE | re.MULTILINE
    )
    if m:
        name = m.group(1).strip()
        name = re.split(r'\s{3,}|\n|[|/]', name)[0].strip()
        if len(name) >= 3:
            return name

    # Pattern 2: salutation-prefixed name like "MR. RAMESH KUMAR"
    #            or Indian honorifics "Shri", "Smt"
    salutation = re.search(
        r'\b(Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Shri\.?|Smt\.?)\s+([A-Z][A-Z\s\.]{2,50})',
        text, re.IGNORECASE
    )
    if salutation:
        name = (salutation.group(1) + ' ' + salutation.group(2)).strip()
        name = re.split(r'\s{3,}|\n|[|/]', name)[0].strip()
        if len(name) >= 3:
            return name

    return None


# FIX #5 — opening/closing balance: tighter regex, stops at non-numeric chars
def _extract_balance(text: str, label: str) -> Optional[float]:
    # label is like "Opening Balance" or "Closing Balance"
    m = re.search(
        label + r'[:\s]*([\u20B9₹]?[\s]*[\d,]+(?:\.\d{1,2})?)',
        text, re.IGNORECASE
    )
    if m:
        return _parse_amount(m.group(1))
    return None


# FIX #6 — statement period: handles both "to" and hyphen/en-dash separators
def _extract_period(text: str):
    patterns = [
        r'(?:Statement\s*Period|Period|From)[:\s]*([\d\w\-/,\. ]+?)\s+[Tt]o\s+([\d\w\-/,\. ]+?)(?:\s*\n|$)',
        r'(?:Statement\s*Period|Period)[:\s]*([\d\w\-/,\. ]+?)\s*[-\u2013]\s*([\d\w\-/,\. ]+?)(?:\s*\n|$)',
        r'From[:\s]*([\d]{1,2}[/-][\d]{1,2}[/-][\d]{2,4})[^\d].*?[Tt]o[:\s]*([\d]{1,2}[/-][\d]{1,2}[/-][\d]{2,4})',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            frm = _parse_date(m.group(1).strip())
            to  = _parse_date(m.group(2).strip())
            if frm and to:
                return frm, to
    return None, None


# FIX #8 — branch name: extract only the branch value, not the full line
_BRANCH_HEADING_NOISE = {'INFORMATION', 'DETAILS', 'INFO', 'SECTION', 'DETAIL', 'ADDRESS'}

def _extract_branch(text: str, ifsc: Optional[str]) -> Optional[str]:
    for m in re.finditer(
        r'Branch\s*(?:Name)?\s*:\s*([A-Za-z0-9][A-Za-z0-9\s,\.\-]{2,60})',
        text, re.IGNORECASE
    ):
        branch = m.group(1).strip()
        branch = re.split(r'\s{3,}|\n|[|/]', branch)[0].strip()
        if branch.upper() in _BRANCH_HEADING_NOISE:
            continue
        if len(branch) >= 3:
            return branch

    if ifsc:
        for line in text.split('\n')[:50]:
            if ifsc in line:
                candidate = line.replace(ifsc, '').strip()
                candidate = re.sub(r'\b\d{9}\b', '', candidate).strip()
                candidate = re.sub(r'[|:,\-]+', ' ', candidate).strip()
                candidate = re.sub(r'\s+', ' ', candidate).strip()
                if 3 <= len(candidate) <= 80:
                    return candidate
    return None


# FIX #9 — account number: stricter pattern, avoids matching phone/dates
def _extract_account_number(text: str) -> Optional[str]:
    # Explicit label first
    m = re.search(
        r'(?:Account\s*(?:Number|No\.?|#)|A/?C\s*(?:No\.?|Number))[:\s]*([A-Z0-9xX\*\#]{4,20})',
        text, re.IGNORECASE
    )
    if m:
        return m.group(1).strip()
    # Masked account pattern like XXXX1234 or ****1234
    m = re.search(r'([Xx\*#]{4,}\d{2,6})', text)
    if m:
        return m.group(1)
    # Bare account number: 9–18 contiguous digits
    m = re.search(r'\b(\d{9,18})\b', text)
    if m:
        return m.group(1)
    return None


# ---------------------------------------------------------------------------
# Main entry function
# ---------------------------------------------------------------------------
def extract_statement(file_path: str) -> dict:
    """
    Main entry function.
    Returns a dict matching the required JSON schema.
    Does NOT feed into any detector or scoring engine.
    Used only for case creation and failed transaction flagging.
    """

    account = {
        'account_holder_name':  None,
        'account_number':       None,
        'ifsc_code':            None,
        'bank_name':            'UNKNOWN',
        'branch_name':          None,
        'account_type':         None,
        'statement_period_from':None,
        'statement_period_to':  None,
        'opening_balance':      None,
        'closing_balance':      None,
        'currency':             'INR',
        'customer_id':          None,
        'email':                None,
        'phone':                None,
        'address':              None,
    }

    transactions: List[dict] = []
    raw_text = ''
    ext = os.path.splitext(file_path)[1].lower()

    # ------------------------------------------------------------------
    # Parse file into transactions list and raw_text for header extraction
    # ------------------------------------------------------------------
    try:
        if ext in ('.xls', '.xlsx', '.csv'):
            df = _dataframe_from_spreadsheet(file_path)
            if not df.empty:
                # FIX #2: parse once here; do NOT re-run failure detection later
                transactions = _rows_from_dataframe(df)
                raw_text = '\n'.join(
                    str(v) for v in df.head(30).astype(str).values.flatten()
                )

        elif ext == '.pdf':
            if pdfplumber is not None:
                text_pages = []
                with pdfplumber.open(file_path) as pdf:
                    for p in pdf.pages[:15]:
                        try:
                            text_pages.append(p.extract_text() or '')
                        except Exception:
                            text_pages.append('')
                raw_text = '\n'.join(text_pages)

                df = _dataframe_from_pdf(file_path)
                
                # Try parsing with table dataframe
                if not df.empty:
                    transactions = _rows_from_dataframe(df)
                    
                # FIX: Fallback to Bank-Specific Regex if table extraction failed to yield transactions
                valid_txns = [t for t in transactions if t.get('date') or t.get('description')]
                if not valid_txns:
                    temp_ifsc = _extract_ifsc_from_text(raw_text)
                    temp_bank = _bank_name_from_ifsc(temp_ifsc) if temp_ifsc else 'UNKNOWN'
                    
                    df_fallback = _regex_parse_pdf(file_path, temp_bank)
                    if not df_fallback.empty:
                        transactions = _rows_from_dataframe(df_fallback)

        else:
            # Unknown extension: try CSV
            try:
                df = pd.read_csv(file_path, dtype=str)
                transactions = _rows_from_dataframe(df)
                raw_text = '\n'.join(
                    str(v) for v in df.head(30).astype(str).values.flatten()
                )
            except Exception:
                pass

    except Exception:
        pass  # Never raise; fall back to empty results

    # ------------------------------------------------------------------
    # Header extraction from raw_text
    # ------------------------------------------------------------------
    if raw_text:
        # IFSC — FIX #3: no word boundary, finds IFSC in narrations too
        ifsc = _extract_ifsc_from_text(raw_text)
        account['ifsc_code'] = ifsc
        account['bank_name'] = _bank_name_from_ifsc(ifsc)

        # Account number — FIX #9
        account['account_number'] = _extract_account_number(raw_text)

        # Account holder name — FIX #4
        account['account_holder_name'] = _extract_account_holder(raw_text)

        # Statement period — FIX #6
        frm, to = _extract_period(raw_text)
        account['statement_period_from'] = frm
        account['statement_period_to']   = to

        # Opening balance — FIX #5
        account['opening_balance'] = _extract_balance(raw_text, r'Opening\s*Balance')

        # Closing balance — FIX #5 + FIX #11
        # Search for "Closing Balance" explicitly, not just any balance figure
        account['closing_balance'] = _extract_balance(raw_text, r'Closing\s*Balance')

        # Account type — FIX #12: broader label variants (Type of Account,
        # Scheme/Scheme Type) since "Account Type"/"A/C Type" alone misses
        # how many Indian bank statements actually label this field.
        # Falls back to a bare-value scan (e.g. "SAVINGS BANK ACCOUNT")
        # when no label precedes the value at all.
        def _normalize_account_type(raw: str) -> Optional[str]:
            u = raw.strip().upper()
            if 'SAVINGS' in u or u in ('SB', 'SB ACCOUNT'):
                return 'Savings'
            if 'CURRENT' in u:
                return 'Current'
            if 'OVERDRAFT' in u or u == 'OD':
                return 'Overdraft'
            if 'NRE' in u:
                return 'NRE'
            if 'NRO' in u:
                return 'NRO'
            return None

        account_type = None
        m = re.search(
            r'(?:Account\s*Type|A/?C\s*Type|Type\s*of\s*Account|Scheme(?:\s*Type)?)'
            r'[:\s]*([A-Za-z][A-Za-z\s]{2,30})',
            raw_text, re.IGNORECASE
        )
        if m:
            account_type = _normalize_account_type(m.group(1).split('\n')[0])
        if not account_type:
            m = re.search(
                r'\b(SAVINGS\s+BANK\s+ACCOUNT|SAVINGS\s+ACCOUNT|SB\s+ACCOUNT|'
                r'CURRENT\s+ACCOUNT|OVERDRAFT\s+ACCOUNT|NRE\s+ACCOUNT|NRO\s+ACCOUNT)\b',
                raw_text, re.IGNORECASE
            )
            if m:
                account_type = _normalize_account_type(m.group(1))
        account['account_type'] = account_type

        # Customer / CIF ID
        m = re.search(
            r'(?:CIF|Customer\s*(?:ID|No\.?))[:\s]*([A-Z0-9\-]{4,20})',
            raw_text, re.IGNORECASE
        )
        if m:
            account['customer_id'] = m.group(1).strip()

        # Email — FIX #13: skip any email preceded by "Branch" within the
        # nearby text, so the branch's contact email (e.g. "Branch Email ID")
        # isn't mistaken for the account holder's own email.
        for m in re.finditer(r'([\w\.\-]+@[\w\.\-]+\.\w{2,})', raw_text):
            context_before = raw_text[max(0, m.start() - 40):m.start()]
            if re.search(r'Branch', context_before, re.IGNORECASE):
                continue
            account['email'] = m.group(1).strip()
            break

        # Phone — FIX #14: skip any phone preceded by "Branch", same
        # reasoning as email above (avoids "Branch Phone" being mistaken
        # for the account holder's own contact number).
        for m in re.finditer(
            r'(?:Phone|Mobile|Contact)(?:\s*No\.?)?[:\s]*(\+?[\d][\d\s\-]{8,14})',
            raw_text, re.IGNORECASE
        ):
            context_before = raw_text[max(0, m.start() - 20):m.start()]
            if re.search(r'Branch', context_before, re.IGNORECASE):
                continue
            account['phone'] = re.sub(r'\s+', '', m.group(1)).strip()
            break

        # Branch name — FIX #8
        account['branch_name'] = _extract_branch(raw_text, ifsc)

        # Address: look for multi-word address-like block
        m = re.search(
            r'(?:Address|Addr)[:\s]+([A-Za-z0-9\s,\.\-/#]{10,120})',
            raw_text, re.IGNORECASE
        )
        if m:
            addr = m.group(1).strip()
            addr = re.split(r'\n{2,}', addr)[0].strip()
            if len(addr) >= 10:
                account['address'] = addr

    # ------------------------------------------------------------------
    # FIX #2: transactions already have is_failed set by _rows_from_dataframe
    # We only do schema enforcement here — NO re-detection
    # ------------------------------------------------------------------
    cleaned_txns: List[dict] = []
    seen_ids: set = set()
    gen_idx = 1

    for t in transactions:
        # Guarantee unique txn_id
        raw_id = t.get('txn_id') or ''
        if not raw_id or raw_id in seen_ids:
            txn_id = f"TXN_{gen_idx:03d}"
            while txn_id in seen_ids:
                gen_idx += 1
                txn_id = f"TXN_{gen_idx:03d}"
        else:
            txn_id = raw_id
        seen_ids.add(txn_id)
        gen_idx += 1

        # Enforce date/time format
        date       = _parse_date(t.get('date')) or t.get('date') or None
        time       = _parse_time(t.get('time')) or t.get('time') or None
        value_date = _parse_date(t.get('value_date')) or t.get('value_date') or None

        description = t.get('description') or ''

        debit    = _parse_amount(t.get('debit'))
        credit   = _parse_amount(t.get('credit'))
        balance  = _parse_amount(t.get('balance'))

        ref = t.get('reference_no')
        reference_no = str(ref).strip() if ref and str(ref).strip() not in ('nan', 'None', '') else None

        # FIX #2: use already-detected values, do NOT re-detect
        is_failed      = bool(t.get('is_failed', False))
        failure_reason = t.get('failure_reason') if is_failed else None

        cleaned_txns.append({
            'txn_id':         txn_id,
            'transaction_id': txn_id, # Required by failure_detection.py
            'date':           date,
            'time':           time,
            'value_date':     value_date,
            'description':    description,
            'debit':          debit,
            'credit':         credit,
            'balance':        balance,
            'reference_no':   reference_no,
            'reference_number': reference_no, # Required by failure_detection.py
            'is_failed':      is_failed,
            'failure_reason': failure_reason,
            'bank_name':      account.get('bank_name'), # Required by failure_detection.py
        })

    # ------------------------------------------------------------------
    # Advanced Failure Detection and Filtering
    # ------------------------------------------------------------------
    try:
        from app.parsers.failure_detection import classify_transactions, Status
        classified_txns = classify_transactions(cleaned_txns, dedupe=True)
        
        final_txns = []
        failed_count = 0
        
        for txn in classified_txns:
            if txn.get('status') == Status.SUCCESS:
                # Keep successful transactions
                txn['is_failed'] = False
                final_txns.append(txn)
            else:
                # Remove failed transactions
                failed_count += 1
    except ImportError:
        # Fallback if failure_detection is not available
        final_txns = [x for x in cleaned_txns if not x.get('is_failed')]
        failed_count = len(cleaned_txns) - len(final_txns)

    # ------------------------------------------------------------------
    # Summary calculations
    # ------------------------------------------------------------------
    total_transactions  = len(final_txns)
    total_credit_count  = sum(1 for x in final_txns if x.get('credit') is not None)
    total_debit_count   = sum(1 for x in final_txns if x.get('debit')  is not None)
    total_credit_amount = round(sum((x.get('credit') or 0.0) for x in final_txns), 2)
    total_debit_amount  = round(sum((x.get('debit')  or 0.0) for x in final_txns), 2)

    # FIX #10: safe date_range_days — never crashes on bad/missing dates
    date_range_days = 0
    parsed_dates = []
    for x in final_txns:
        if x.get('date'):
            try:
                parsed = dateparser.parse(x['date'], dayfirst=True)
                if parsed:
                    parsed_dates.append(parsed.date())
            except Exception:
                pass
    if len(parsed_dates) >= 2:
        date_range_days = (max(parsed_dates) - min(parsed_dates)).days

    # Enforce numeric types on balances
    if account.get('opening_balance') is not None:
        account['opening_balance'] = float(account['opening_balance'])
    if account.get('closing_balance') is not None:
        account['closing_balance'] = float(account['closing_balance'])

    return {
        'account': account,
        'summary': {
            'total_transactions':       total_transactions,
            'total_credit_count':       total_credit_count,
            'total_debit_count':        total_debit_count,
            'total_credit_amount':      float(f"{total_credit_amount:.2f}"),
            'total_debit_amount':       float(f"{total_debit_amount:.2f}"),
            'failed_transaction_count': failed_count,
            'date_range_days':          date_range_days,
        },
        'transactions': final_txns,
    }


# ---------------------------------------------------------------------------
# CLI helper — python extract_statement.py <file_path>
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    import json
    import sys

    if len(sys.argv) > 1:
        fp = sys.argv[1]
        out = extract_statement(fp)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("Usage: python extract_statement.py <path_to_bank_statement>")