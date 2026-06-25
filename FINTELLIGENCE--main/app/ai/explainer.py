from app.ai.ollama_client import call_ollama
from app.models.transaction import Transaction
from app.models.detection_result import DetectionResult
from sqlalchemy import or_

def generate_explanation(txn_id: str, case_id: str) -> str:
    transaction = Transaction.query.filter_by(id=txn_id, case_id=case_id).first()
    if not transaction:
        return "Transaction not found."

    # Fetch detection results involving this txn
    # DetectionResult.transactions_involved is a JSON array. In SQLite/Postgres we can query, 
    # but for simplicity we can query case_id and filter in python if DB specific JSON query is complex.
    # Alternatively, use SQLAlchemy filter with string conversion or specific JSON operators.
    # We will fetch by case_id and filter in memory to be safe across DB dialects.
    all_results = DetectionResult.query.filter_by(case_id=case_id, triggered=True).all()
    
    triggered_detectors = []
    for r in all_results:
        if r.transactions_involved and txn_id in r.transactions_involved:
            triggered_detectors.append(f"{r.detector_name} (Score: {r.score}) - {r.reason}")
            
    if not triggered_detectors:
        return "No suspicious detectors triggered for this transaction."

    system_prompt = (
        "You are a forensic accountant writing investigation notes. Given a transaction "
        "and list of fraud indicators triggered, write a concise professional explanation. "
        "Format as bullet points. Be specific with amounts and dates. Maximum 5 points."
    )
    
    detector_list_str = "\n".join(triggered_detectors)
    
    user_prompt = (
        f"Transaction: ₹{transaction.amount} {transaction.type} on {transaction.date}\n"
        f"From: {transaction.sender_account} To: {transaction.receiver_account}\n"
        f"Description: {transaction.description}\n"
        f"Detectors triggered:\n{detector_list_str}\n\n"
        f"Explain why this is suspicious."
    )

    try:
        return call_ollama(system_prompt, user_prompt, max_tokens=800)
    except Exception:
        return "Explanation unavailable because AI services are not configured."
