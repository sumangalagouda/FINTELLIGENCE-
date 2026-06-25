import uuid
from dateutil import parser as date_parser


def extract_accounts(description, txn_type=None):
    """
    Extract sender and receiver accounts from narration.

    Example:
    UPI/HDFC_ACC001/TO/SBI_ACC002/Rahul Kumar

    Sender   = HDFC_ACC001
    Receiver = SBI_ACC002
    """
    sender = None
    receiver = None

    try:
        parts = str(description).split('/')

        if "TO" in parts:
            idx = parts.index("TO")

            if idx > 0:
                sender = parts[idx - 1].strip()

            if idx < len(parts) - 1:
                receiver = parts[idx + 1].strip()
        else:
            # Handle cases like ATM/AXIS_ACC004/CASH DEPOSIT/Branch
            if len(parts) > 1 and "ACC" in parts[1]:
                account = parts[1].strip()
                if txn_type == 'credit':
                    sender = "CASH/EXTERNAL"
                    receiver = account
                elif txn_type == 'debit':
                    sender = account
                    receiver = "CASH/EXTERNAL"

    except Exception as e:
        print(f"Error extracting accounts: {e}")

    return sender, receiver


def process_and_normalize(raw_transactions, statement_id, case_id):
    """
    Normalize parsed transactions into canonical schema.
    """

    normalized_txns = []

    for raw_txn in raw_transactions:

        parsed = raw_txn.get("parsed_data", {})

        amount = 0.0
        txn_type = "debit"
        date_str = None
        description = raw_txn.get("raw_text", "")
        balance_after = 0.0

        if isinstance(parsed, dict):

            # --------------------
            # CREDIT
            # --------------------
            credit = parsed.get("Credit")

            if credit is not None and str(credit).strip() != "":
                try:
                    amount = float(credit)
                    txn_type = "credit"
                except:
                    pass

            # --------------------
            # DEBIT
            # --------------------
            debit = parsed.get("Debit")

            if (
                debit is not None
                and str(debit).strip() != ""
                and amount == 0
            ):
                try:
                    amount = float(debit)
                    txn_type = "debit"
                except:
                    pass

            # --------------------
            # GENERIC AMOUNT
            # --------------------
            if amount == 0 and parsed.get("Amount") is not None:
                try:
                    amt = float(parsed["Amount"])
                    amount = abs(amt)
                    txn_type = "credit" if amt > 0 else "debit"
                except:
                    pass

            # --------------------
            # DATE
            # --------------------
            if parsed.get("Date") is not None:
                date_str = str(parsed["Date"])

            # --------------------
            # DESCRIPTION
            # --------------------
            if parsed.get("Description") is not None:
                description = str(parsed["Description"])

            # --------------------
            # BALANCE
            # --------------------
            if parsed.get("Balance") is not None:
                try:
                    balance_after = float(parsed["Balance"])
                except:
                    pass

        # --------------------
        # DATE NORMALIZATION
        # --------------------
        parsed_date = None

        if date_str:
            try:
                parsed_date = date_parser.parse(
                    date_str,
                    dayfirst=True
                ).date()
            except:
                parsed_date = None

        # --------------------
        # CLEAN DESCRIPTION
        # --------------------
        clean_desc = " ".join(str(description).split())

        # --------------------
        # ACCOUNT EXTRACTION
        # --------------------
        sender_account, receiver_account = extract_accounts(
            clean_desc, txn_type
        )

        if parsed_date is None:
            continue

        canonical_txn = {
            "txn_id": str(uuid.uuid4()),
            "statement_id": statement_id,
            "case_id": case_id,
            "date": parsed_date,
            "amount": amount,
            "type": txn_type,
            "sender_account": sender_account,
            "receiver_account": receiver_account,
            "description": clean_desc,
            "balance_after": balance_after,
            "raw_text": raw_txn.get("raw_text", ""),
            "is_failed": parsed.get("is_failed", False),
            "failure_reason": parsed.get("failure_reason")
        }

        normalized_txns.append(canonical_txn)

    return normalized_txns