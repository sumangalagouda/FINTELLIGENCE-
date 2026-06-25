import json
from app.ai.ollama_client import call_ollama
from app.ai.pattern_library import identify_patterns
from app.models.transaction import Transaction

def recommend_submission(case_id: str) -> dict:
    patterns_data = identify_patterns(case_id)
    pattern_names = [p['pattern_name'] for p in patterns_data]
    
    txns = Transaction.query.filter_by(case_id=case_id, is_failed=False).all()
    total_amount = sum(t.amount for t in txns if t.amount)
    
    system_prompt = (
        "You are an Indian AML compliance officer. Based on the detected patterns and amount, "
        "recommend the appropriate Indian authorities to report to (e.g., ED, FIU, EOW, Cyber Crime Cell). "
        "Draft a short referral letter. "
        "Respond ONLY in raw JSON matching this schema: "
        "{'primary_authority': 'string', 'secondary_authority': 'string', "
        "'reason': 'string', 'urgency': 'high|medium|low', 'draft_referral': 'string'}"
    )
    
    user_prompt = (
        f"Detected Patterns: {', '.join(pattern_names) if pattern_names else 'None'}\n"
        f"Total Amount Involved: ₹{total_amount:,.2f}\n"
        f"Recommend authorities and draft referral."
    )
    
    try:
        response_text = call_ollama(system_prompt, user_prompt, max_tokens=1500)
    except Exception:
        return {
            "primary_authority": "Financial Intelligence Unit (FIU)",
            "secondary_authority": "",
            "reason": "AI submission recommendation unavailable; manual review required.",
            "urgency": "medium",
            "draft_referral": "Manual referral draft required."
        }
    
    try:
        clean_json = response_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        return data
    except Exception:
        return {
            "primary_authority": "Financial Intelligence Unit (FIU)",
            "secondary_authority": "",
            "reason": "Failed to parse AI response. Manual review required.",
            "urgency": "medium",
            "draft_referral": "Manual referral draft required."
        }
