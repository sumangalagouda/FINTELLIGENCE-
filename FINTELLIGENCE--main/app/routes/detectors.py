from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.detectors.large_transaction import detect_large_transaction
from app.detectors.dormant_revival import detect_dormant_revival
from app.detectors.beneficiary_burst import detect_beneficiary_burst
from app.detectors.high_risk_time import detect_high_risk_time
from app.detectors.structuring import detect_structuring
from app.detectors.evidence_confidence import calculate_evidence_confidence

detectors_bp = Blueprint('detectors', __name__, url_prefix='/api/detect')

@detectors_bp.route('/large-transaction', methods=['POST'])
@jwt_required()
def large_transaction_endpoint():
    data = request.get_json(silent=True) or {}
    case_id = data.get('case_id')
    if not case_id:
        return jsonify({"error": "case_id is required"}), 400
    results = detect_large_transaction(case_id)
    return jsonify(results)

@detectors_bp.route('/dormant-revival', methods=['POST'])
@jwt_required()
def dormant_revival_endpoint():
    data = request.get_json(silent=True) or {}
    case_id = data.get('case_id')
    if not case_id:
        return jsonify({"error": "case_id is required"}), 400
    results = detect_dormant_revival(case_id)
    return jsonify(results)

@detectors_bp.route('/beneficiary-burst', methods=['POST'])
@jwt_required()
def beneficiary_burst_endpoint():
    data = request.get_json(silent=True) or {}
    case_id = data.get('case_id')
    if not case_id:
        return jsonify({"error": "case_id is required"}), 400
    results = detect_beneficiary_burst(case_id)
    return jsonify(results)

@detectors_bp.route('/high-risk-time', methods=['POST'])
@jwt_required()
def high_risk_time_endpoint():
    data = request.get_json(silent=True) or {}
    case_id = data.get('case_id')
    if not case_id:
        return jsonify({"error": "case_id is required"}), 400
    results = detect_high_risk_time(case_id)
    return jsonify(results)

@detectors_bp.route('/structuring', methods=['POST'])
@jwt_required()
def structuring_endpoint():
    data = request.get_json(silent=True) or {}
    case_id = data.get('case_id')
    if not case_id:
        return jsonify({"error": "case_id is required"}), 400
    results = detect_structuring(case_id)
    return jsonify(results)

@detectors_bp.route('/evidence-confidence', methods=['POST'])
@jwt_required()
def evidence_confidence_endpoint():
    data = request.get_json(silent=True) or {}
    case_id = data.get('case_id')
    if not case_id:
        return jsonify({"error": "case_id is required"}), 400
    results = calculate_evidence_confidence(case_id)
    return jsonify(results)
