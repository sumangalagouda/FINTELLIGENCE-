from app.detectors.structuring import detect_structuring
from app.detectors.dormant_revival import detect_dormant_revival
from app.detectors.large_transaction import detect_large_transaction
from app.detectors.beneficiary_burst import detect_beneficiary_burst
from app.detectors.high_risk_time import detect_high_risk_time


WEIGHTS = {
    "Structuring": 0.25,
    "DormantRevival": 0.25,
    "LargeTransaction": 0.20,
    "BeneficiaryBurst": 0.15,
    "HighRiskTime": 0.15
}


def calculate_evidence_confidence(case_id: str):

    # --------------------------------------------------
    # Run all detectors
    # --------------------------------------------------
    results = {
        "Structuring": detect_structuring(case_id),
        "DormantRevival": detect_dormant_revival(case_id),
        "LargeTransaction": detect_large_transaction(case_id),
        "BeneficiaryBurst": detect_beneficiary_burst(case_id),
        "HighRiskTime": detect_high_risk_time(case_id)
    }

    breakdown = {}
    triggered_count = 0
    total_weighted_score = 0

    # --------------------------------------------------
    # Process detector outputs
    # --------------------------------------------------
    for detector_name, detector_outputs in results.items():

        weight = WEIGHTS.get(detector_name, 0.10)

        triggered_items = [
            d for d in detector_outputs
            if d.get("triggered", False)
        ]

        if triggered_items:

            highest_score = max(
                d.get("score", 0)
                for d in triggered_items
            )

            breakdown[detector_name] = {
                "score": highest_score,
                "weight": weight,
                "triggered": True
            }

            total_weighted_score += (
                highest_score * weight
            )

            triggered_count += 1

        else:

            breakdown[detector_name] = {
                "score": 0,
                "weight": weight,
                "triggered": False
            }

    # --------------------------------------------------
    # Confidence Calculation
    # --------------------------------------------------
    max_weight = sum(WEIGHTS.values())

    if max_weight > 0:
        overall_confidence = (
            total_weighted_score / max_weight
        )
    else:
        overall_confidence = 0

    # --------------------------------------------------
    # Multi-pattern Synergy Bonus
    # --------------------------------------------------
    synergy_bonus = 0

    if triggered_count >= 4:
        synergy_bonus = 25

    elif triggered_count == 3:
        synergy_bonus = 20

    elif triggered_count == 2:
        synergy_bonus = 10

    overall_confidence += synergy_bonus

    overall_confidence = min(
        100,
        round(overall_confidence)
    )

    # --------------------------------------------------
    # Risk Assessment
    # --------------------------------------------------
    if overall_confidence >= 85:

        assessment = (
            "Strong multi-pattern fraud evidence. "
            "Immediate investigator review recommended."
        )

    elif overall_confidence >= 70:

        assessment = (
            "Multiple suspicious patterns detected. "
            "High-risk case requiring investigation."
        )

    elif overall_confidence >= 50:

        assessment = (
            "Moderate suspicious activity detected. "
            "Further review recommended."
        )

    elif overall_confidence > 0:

        assessment = (
            "Limited suspicious activity detected."
        )

    else:

        assessment = (
            "No suspicious patterns detected."
        )

    # --------------------------------------------------
    # Final Response
    # --------------------------------------------------
    return {
        "overall_confidence": overall_confidence,
        "breakdown": breakdown,
        "triggered_count": triggered_count,
        "assessment": assessment,
        "raw_results": results
    }