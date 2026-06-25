from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.detection_result import DetectionResult
from app.models.transaction import Transaction
from app.models.case import Case

suspicion_bp = Blueprint('suspicion_score', __name__, url_prefix='/api/intelligence')

WEIGHTS = {
    "CircularFlow": 30,
    "LayeringChain": 28,
    "LayeringSeverity": 25,
    "PassThrough": 22,
    "TransactionVelocity": 20,
    "Structuring": 20,
    "LargeTransaction": 15,
    "DormantRevival": 15,
    "BeneficiaryBurst": 12,
    "CashCycling": 10,
    "HighRiskTime": 8
}

def update_case_suspicion_score(case_id, results=None):
    # This is called during silent engine to just update, but we can also just fetch from DB
    results_db = DetectionResult.query.filter_by(case_id=case_id, triggered=True).all()
    
    # We want unique detectors in case they triggered multiple times
    # We'll take the highest score for each detector
    detector_scores = {}
    for r in results_db:
        if r.detector_name in detector_scores:
            detector_scores[r.detector_name] = max(detector_scores[r.detector_name], r.score)
        else:
            detector_scores[r.detector_name] = r.score
            
    raw_score = 0.0
    max_possible = 0.0
    breakdown = {}
    
    for d_name, d_score in detector_scores.items():
        weight = WEIGHTS.get(d_name, 0)
        if weight > 0:
            contribution = weight * (d_score / 100.0)
            raw_score += contribution
            max_possible += weight
            breakdown[d_name] = {
                "score": d_score,
                "weight": weight,
                "contribution": contribution
            }
            
    final_score = 0.0
    if max_possible > 0:
        final_score = (raw_score / max_possible) * 100.0
        
    risk_level = "LOW"
    if final_score > 85:
        risk_level = "CRITICAL"
    elif final_score > 60:
        risk_level = "HIGH"
    elif final_score > 30:
        risk_level = "MEDIUM"
        
    # Total amount flagged
    flagged_amount = 0.0
    txns = Transaction.query.filter_by(case_id=case_id, is_failed=False).join(DetectionResult, Transaction.id == DetectionResult.txn_id).all()
    # Wait, the transactions_involved is a JSON array in DetectionResult, not a simple join.
    # We'll fetch all unique transaction ids involved
    txn_ids = set()
    for r in results_db:
        if r.transactions_involved:
            for tid in r.transactions_involved:
                txn_ids.add(tid)
                
    if txn_ids:
        # Avoid huge IN queries
        txns = Transaction.query.filter(Transaction.id.in_(list(txn_ids))).all()
        flagged_amount = sum(t.amount for t in txns)
        
    # Update case
    case = Case.query.get(case_id)
    if case:
        case.suspicion_score = final_score
        case.risk_level = risk_level
        db.session.commit()
        
    return {
        "risk_score": round(final_score, 1),
        "risk_level": risk_level,
        "triggered_detectors": list(detector_scores.keys()),
        "breakdown": breakdown,
        "total_detectors_triggered": len(detector_scores),
        "total_amount_flagged": flagged_amount
    }

@suspicion_bp.route('/suspicion-score/<case_id>', methods=['GET'])
@jwt_required()
def get_suspicion_score_endpoint(case_id):
    result = update_case_suspicion_score(case_id)
    return jsonify(result)
