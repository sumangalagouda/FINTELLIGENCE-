from app.models.case import Case
from app.models.verification import Verification
from app.models.supervisor_approval import SupervisorApproval
from app.detectors.evidence_confidence import calculate_evidence_confidence

def calculate_fir_readiness(case_id):
    case = Case.query.get(case_id)

    if not case:
        return {"error": "Case not found"}

    # AI suspicion score
    suspicion = case.suspicion_score or 0.0

    # Evidence confidence
    evidence_res = calculate_evidence_confidence(case_id)
    evidence = evidence_res.get("overall_confidence", 0.0)

    # Verification score
    verification_record = Verification.query.filter_by(
        case_id=case_id
    ).first()

    verification = (
        verification_record.completion_percentage
        if verification_record
        else 0.0
    )

    # Supervisor approval
    approval_record = (
        SupervisorApproval.query
        .filter_by(case_id=case_id)
        .order_by(SupervisorApproval.requested_at.desc())
        .first()
    )

    approved = (
        approval_record is not None
        and approval_record.status == "approved"
    )

    approval_score = 100 if approved else 0

    # Evidence score combines AI + evidence confidence
    evidence_score = (
        (suspicion * 0.5) +
        (evidence * 0.5)
    )

    # FIR Readiness
    fir_readiness = (
        (evidence_score * 0.50) +
        (verification * 0.30) +
        (approval_score * 0.20)
    )

    blocking_factors = []

    if verification < 100:
        blocking_factors.append(
            "Verification checklist is incomplete."
        )

    if not approved:
        blocking_factors.append(
            "Pending supervisor approval."
        )

    if evidence_score < 50:
        blocking_factors.append(
            "Evidence confidence or suspicion score is too low."
        )

    # Debug
    print("Suspicion Score:", suspicion)
    print("Evidence Result:", evidence_res)
    print("Evidence Confidence:", evidence)
    print("Verification Score:", verification)
    print("Approval Score:", approval_score)
    print("Evidence Score:", evidence_score)
    print("FIR Readiness:", fir_readiness)

    return {
        "fir_readiness_score": round(fir_readiness, 1),
        "evidence_score": round(evidence_score, 1),
        "verification_score": round(verification, 1),
        "approval_score": approval_score,
        "ready": fir_readiness >= 70,
        "blocking_factors": blocking_factors,
        "risk_level": case.risk_level,
        "suspicion_score": round(suspicion, 1),
        "evidence_confidence": round(evidence, 1)
    }