from app.ai.case_severity import get_case_severity
from app.detectors.evidence_confidence import calculate_evidence_confidence

def determine_escalation(case_id: str) -> str:
    severity_data = get_case_severity(case_id)
    severity_score = severity_data.get('severity_score', 0)
    
    evidence_data = calculate_evidence_confidence(case_id)
    evidence_score = evidence_data.get('overall_confidence', 0)
    
    if severity_score >= 85 or evidence_score >= 90:
        return "IMMEDIATE_INVESTIGATION"
    elif severity_score >= 60 or evidence_score >= 70:
        return "SUPERVISOR_REVIEW"
    elif severity_score >= 35:
        return "MONITOR"
    else:
        return "CLOSE_NO_ACTION"
