import sys
import pandas as pd
import json
from app.parsers.statement_extractor import _regex_parse_pdf

def test(path, bank_name):
    print(f"\n--- Testing {bank_name} on {path} ---")
    df = _regex_parse_pdf(path, bank_name)
    if not df.empty:
        print(f"Extracted {len(df)} transactions.")
        print(df.head(5).to_string())
        print(df.tail(2).to_string())
    else:
        print("Extracted 0 transactions.")

if __name__ == "__main__":
    test('uploads/04114e1a-8644-4879-a3c2-c4e0dc862596_SBI.pdf', 'STATE BANK OF INDIA')
    test('uploads/294bf085-0c77-4fc2-88a3-2cea4d034ec6_canara_epassbook_2026-06-18_20_39_21.517933.pdf', 'CANARA BANK')
