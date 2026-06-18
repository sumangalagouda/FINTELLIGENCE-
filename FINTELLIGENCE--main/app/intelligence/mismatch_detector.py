from app.extensions import db
from app.models.case import Case
from app.intelligence.audit_logger import log_action

def check_mismatch(case_id, investigator_decision, user_id):
    case = Case.query.get(case_id)

    if not case:
        return {
            "error": "Case not found"
        }

    # Read AI score from case
    ai_score = getattr(case, "risk_score", None)

    # Fallback for older schema
    if ai_score is None:
        ai_score = getattr(case, "suspicion_score", 0.0)

    ai_level = getattr(case, "risk_level", "LOW")

    # Normalize decision
    decision = investigator_decision.lower().strip()

    high_risk_closure_actions = [
        "closed",
        "cleared",
        "no_action"
    ]

    if ai_score >= 70 and decision in high_risk_closure_actions:

        old_status = case.status

        case.status = "supervisor_review"
        db.session.commit()

        log_action(
            case_id=case_id,
            action="mismatch_override",
            user_id=user_id,
            old_val={
                "status": old_status,
                "ai_score": ai_score,
                "risk_level": ai_level
            },
            new_val={
                "decision": decision,
                "new_status": "supervisor_review"
            },
            notes=f"Investigator attempted to close high-risk case (AI score={ai_score})."
        )

        return {
            "mismatch": True,
            "message": "Case flagged for supervisor review due to high AI risk score override.",
            "ai_score": ai_score,
            "risk_level": ai_level,
            "investigator_decision": decision,
            "new_status": "supervisor_review"
        }

    return {
        "mismatch": False,
        "message": "Decision aligned with AI risk or score is below threshold.",
        "ai_score": ai_score,
        "risk_level": ai_level,
        "investigator_decision": decision
    }