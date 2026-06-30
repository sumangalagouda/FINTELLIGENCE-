from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.detectors.large_transaction import detect_large_transaction
from app.detectors.dormant_revival import detect_dormant_revival
from app.detectors.beneficiary_burst import detect_beneficiary_burst
from app.detectors.high_risk_time import detect_high_risk_time
from app.detectors.structuring import detect_structuring
from app.detectors.evidence_confidence import calculate_evidence_confidence
from app.models.transaction import Transaction

detectors_bp = Blueprint('detectors', __name__, url_prefix='/api/detect')

def populate_transactions(results):
    if not results:
        return results
    
    # Collect all unique transaction IDs across all results
    all_txn_ids = set()
    for res in results:
        for tx in res.get('transactions_involved', []):
            if isinstance(tx, str):
                all_txn_ids.add(tx)
                
    if not all_txn_ids:
        return results
        
    # Bulk fetch transaction data
    txns = Transaction.query.filter(Transaction.id.in_(all_txn_ids)).all()
    txn_map = {t.id: {
        "id": t.id,
        "date": str(t.date),
        "amount": t.amount,
        "description": t.description or "No description"
    } for t in txns}
    
    # Replace string IDs with full objects
    for res in results:
        enriched = []
        for tx in res.get('transactions_involved', []):
            if isinstance(tx, str) and tx in txn_map:
                enriched.append(txn_map[tx])
            else:
                enriched.append(tx)
        res['transactions_involved'] = enriched
        
    return results

@detectors_bp.route('/large-transaction', methods=['POST'])
@jwt_required()
def large_transaction_endpoint():
    data = request.get_json(silent=True) or {}
    case_id = data.get('case_id')
    if not case_id:
        return jsonify({"error": "case_id is required"}), 400
    results = detect_large_transaction(case_id)
    return jsonify(populate_transactions(results))

@detectors_bp.route('/dormant-revival', methods=['POST'])
@jwt_required()
def dormant_revival_endpoint():
    data = request.get_json(silent=True) or {}
    case_id = data.get('case_id')
    if not case_id:
        return jsonify({"error": "case_id is required"}), 400
    results = detect_dormant_revival(case_id)
    return jsonify(populate_transactions(results))

@detectors_bp.route('/beneficiary-burst', methods=['POST'])
@jwt_required()
def beneficiary_burst_endpoint():
    data = request.get_json(silent=True) or {}
    case_id = data.get('case_id')
    if not case_id:
        return jsonify({"error": "case_id is required"}), 400
    results = detect_beneficiary_burst(case_id)
    return jsonify(populate_transactions(results))

@detectors_bp.route('/high-risk-time', methods=['POST'])
@jwt_required()
def high_risk_time_endpoint():
    data = request.get_json(silent=True) or {}
    case_id = data.get('case_id')
    if not case_id:
        return jsonify({"error": "case_id is required"}), 400
    results = detect_high_risk_time(case_id)
    return jsonify(populate_transactions(results))

@detectors_bp.route('/structuring', methods=['POST'])
@jwt_required()
def structuring_endpoint():
    data = request.get_json(silent=True) or {}
    case_id = data.get('case_id')
    if not case_id:
        return jsonify({"error": "case_id is required"}), 400
    results = detect_structuring(case_id)
    return jsonify(populate_transactions(results))

@detectors_bp.route('/evidence-confidence', methods=['POST'])
@jwt_required()
def evidence_confidence_endpoint():
    data = request.get_json(silent=True) or {}
    case_id = data.get('case_id')
    if not case_id:
        return jsonify({"error": "case_id is required"}), 400
    results = calculate_evidence_confidence(case_id)
    return jsonify(populate_transactions(results))

@detectors_bp.route('/pass-through', methods=['POST'])
@jwt_required()
def pass_through_endpoint():
    from app.detectors.pass_through import detect_pass_through
    data = request.get_json(silent=True) or {}
    case_id = data.get('case_id')
    if not case_id:
        return jsonify({"error": "case_id is required"}), 400
    results = detect_pass_through(case_id)
    return jsonify(populate_transactions(results))

@detectors_bp.route('/velocity', methods=['POST'])
@jwt_required()
def velocity_endpoint():
    from app.detectors.velocity import detect_velocity
    data = request.get_json(silent=True) or {}
    case_id = data.get('case_id')
    if not case_id:
        return jsonify({"error": "case_id is required"}), 400
    results = detect_velocity(case_id)
    return jsonify(populate_transactions(results))

@detectors_bp.route('/cash-cycling', methods=['POST'])
@jwt_required()
def cash_cycling_endpoint():
    from app.detectors.cash_cycling import detect_cash_cycling
    data = request.get_json(silent=True) or {}
    case_id = data.get('case_id')
    if not case_id:
        return jsonify({"error": "case_id is required"}), 400
    results = detect_cash_cycling(case_id)
    return jsonify(populate_transactions(results))
