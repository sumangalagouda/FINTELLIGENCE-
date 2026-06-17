import json
from app.ai.groq_client import call_groq
from app.models.transaction import Transaction
from app.detectors.evidence_confidence import calculate_evidence_confidence
from app.ai.pattern_library import identify_patterns
from sqlalchemy import func

def get_case_severity(case_id: str) -> dict:
    evidence = calculate_evidence_confidence(case_id)
    patterns = identify_patterns(case_id)
    
    # Transaction stats
    txns = Transaction.query.filter_by(case_id=case_id).all()
    flagged_txns = [t for t in txns if getattr(t, 'is_flagged', False)] # depends on how is_flagged is used
    
    # If is_flagged isn't reliably updated, just use total txns as a metric
    total_txns = len(txns)
    total_amount = sum(t.amount for t in txns if t.amount)
    
    system_prompt = (
        "You are a financial crime risk assessor. Given fraud detection results, "
        "assign a severity score 0-100 and list the top 5 reasons in order of severity. "
        "Be specific with amounts. Respond ONLY in valid JSON format matching this schema: "
        "{'severity_score': 84, 'risk_level': 'HIGH', 'reasons': ['reason 1'], 'recommended_action': 'action'}"
    )
    
    pattern_names = [p['pattern_name'] for p in patterns]
    
    user_prompt = (
        f"Case Data:\n"
        f"Overall Evidence Confidence: {evidence.get('overall_confidence')}%\n"
        f"Patterns Detected: {', '.join(pattern_names) if pattern_names else 'None'}\n"
        f"Total Transactions: {total_txns}\n"
        f"Total Volume: ₹{total_amount:,.2f}\n"
        f"Triggered Detectors Count: {evidence.get('triggered_count')}\n\n"
        f"Assess the severity."
    )
    
    response_text = call_groq(system_prompt, user_prompt, max_tokens=1000)
    
    try:
        clean_json = response_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        return data
    except Exception:
        if "[MOCK RESPONSE]" in response_text:
            return {
                "severity_score": 84,
                "risk_level": "HIGH",
                "reasons": [
                    "Multiple high-risk patterns detected",
                    "Significant transaction volume involved",
                    "[MOCK] Add API Key for real assessment"
                ],
                "recommended_action": "Immediate escalation to AML team and Supervisor review required"
            }
        
        # Fallback heuristic
        score = evidence.get('overall_confidence', 0)
        return {
            "severity_score": score,
            "risk_level": "HIGH" if score > 75 else "MEDIUM" if score > 40 else "LOW",
            "reasons": ["Fallback heuristic applied due to parsing error."],
            "recommended_action": "Manual Review."
        }
