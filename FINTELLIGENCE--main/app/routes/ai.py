from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.ai.chat_investigator import ask_investigator
from app.ai.explainer import generate_explanation
from app.ai.legitimate_explainer import check_legitimate_explanation
from app.ai.pattern_library import identify_patterns
from app.ai.case_severity import get_case_severity
from app.intelligence.escalation import determine_escalation
from app.intelligence.submission import recommend_submission

ai_bp = Blueprint('ai', __name__, url_prefix='/api')

@ai_bp.route('/ai/chat', methods=['POST'])
@jwt_required()
def chat_investigator_endpoint():
    data = request.get_json(silent=True) or {}
    question = data.get('question')
    case_id = data.get('case_id')
    history = data.get('conversation_history', [])
    if not case_id or not question:
        return jsonify({"error": "case_id and question are required"}), 400
    
    result = ask_investigator(question, case_id, history)
    return jsonify(result)

@ai_bp.route('/ai/explain', methods=['POST'])
@jwt_required()
def explain_endpoint():
    data = request.get_json(silent=True) or {}
    txn_id = data.get('txn_id')
    case_id = data.get('case_id')
    if not case_id or not txn_id:
        return jsonify({"error": "case_id and txn_id are required"}), 400
    
    result = generate_explanation(txn_id, case_id)
    return jsonify({"explanation": result})

@ai_bp.route('/ai/legitimate-check', methods=['POST'])
@jwt_required()
def legitimate_check_endpoint():
    data = request.get_json(silent=True) or {}
    txn_id = data.get('txn_id')
    case_id = data.get('case_id')
    if not case_id or not txn_id:
        return jsonify({"error": "case_id and txn_id are required"}), 400
    
    result = check_legitimate_explanation(txn_id, case_id)
    return jsonify(result)

@ai_bp.route('/ai/identify-patterns', methods=['POST'])
@jwt_required()
def identify_patterns_endpoint():
    data = request.get_json(silent=True) or {}
    case_id = data.get('case_id')
    if not case_id:
        return jsonify({"error": "case_id is required"}), 400
    
    result = identify_patterns(case_id)
    return jsonify(result)

@ai_bp.route('/ai/case-severity/<case_id>', methods=['GET'])
@jwt_required()
def case_severity_endpoint(case_id):
    result = get_case_severity(case_id)
    return jsonify(result)

@ai_bp.route('/intelligence/escalation/<case_id>', methods=['GET'])
@jwt_required()
def escalation_endpoint(case_id):
    result = determine_escalation(case_id)
    return jsonify({"escalation_action": result})

@ai_bp.route('/intelligence/submission-recommendation/<case_id>', methods=['GET'])
@jwt_required()
def submission_recommendation_endpoint(case_id):
    result = recommend_submission(case_id)
    return jsonify(result)
