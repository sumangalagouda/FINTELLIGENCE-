import json
from app.ai.groq_client import call_groq
from app.models.transaction import Transaction

def check_legitimate_explanation(txn_id: str, case_id: str) -> dict:
    transaction = Transaction.query.filter_by(id=txn_id, case_id=case_id).first()
    if not transaction:
        return {"has_legitimate_explanation": False, "explanation": "Transaction not found."}

    system_prompt = (
        "You are a balanced financial analyst. Given a flagged transaction, consider "
        "ALL possible legitimate explanations before concluding it is fraudulent. "
        "Be objective. Suggest verification steps. "
        "Respond ONLY in raw JSON format with the following keys: "
        "'has_legitimate_explanation' (boolean), "
        "'explanation' (string), "
        "'legitimate_confidence' (integer 0-100), "
        "'recommendation' (string), "
        "'verification_steps' (list of strings)."
    )

    user_prompt = (
        f"Evaluate this transaction for legitimate purposes:\n"
        f"Amount: ₹{transaction.amount}\n"
        f"Date: {transaction.date}\n"
        f"From: {transaction.sender_account}\n"
        f"To: {transaction.receiver_account}\n"
        f"Description: {transaction.description}\n\n"
        f"Could this be salary/bonus, festival season spending, property purchase, "
        f"business expense, family emergency, or loan repayment?"
    )

    response_text = call_groq(system_prompt, user_prompt, max_tokens=1000)
    
    try:
        # Strip potential markdown formatting if Groq added it despite instructions
        clean_json = response_text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_json)
        return result
    except json.JSONDecodeError:
        # Fallback if AI fails to return valid JSON
        if "[MOCK RESPONSE]" in response_text:
            return {
                "has_legitimate_explanation": True,
                "explanation": "Amount and timing consistent with Diwali bonus payment. Sender is likely employer.",
                "legitimate_confidence": 65,
                "recommendation": "Verify employment details and payroll records before escalating",
                "verification_steps": ["Request salary slips", "Verify employer details"]
            }
        
        return {
            "has_legitimate_explanation": False,
            "explanation": "Failed to parse AI response. " + response_text,
            "legitimate_confidence": 0,
            "recommendation": "Manual review required.",
            "verification_steps": []
        }
