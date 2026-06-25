from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.detection_result import DetectionResult
from app.models.case import Case

from app.routes.graph import get_graph_from_db
from app.detectors.circular_flow import detect_circular_flow
from app.detectors.layering_chain import find_layering_chains
from app.detectors.large_transaction import detect_large_transaction
from app.detectors.dormant_revival import detect_dormant_revival
from app.detectors.beneficiary_burst import detect_beneficiary_burst
from app.detectors.high_risk_time import detect_high_risk_time
from app.detectors.structuring import detect_structuring
from app.detectors.velocity import detect_velocity
from app.detectors.pass_through import detect_pass_through
from app.detectors.cash_cycling import detect_cash_cycling
from app.intelligence.suspicion_score import update_case_suspicion_score

intelligence_bp = Blueprint('intelligence', __name__, url_prefix='/api/intelligence')

def save_detection_result(result, case_id, statement_id):
    from app.models.transaction import Transaction
    if not result:
        return
        
    def process_result(r):
        dr = DetectionResult(
            case_id=case_id,
            statement_id=statement_id,
            detector_name=r.get("detector"),
            triggered=r.get("triggered", False),
            score=r.get("score", 0),
            reason=r.get("reason"),
            transactions_involved=r.get("transactions_involved", []),
            severity=r.get("severity", "none")
        )
        db.session.add(dr)
        
        # Update associated transactions
        txns_involved = r.get("transactions_involved", [])
        if txns_involved:
            for txn_id in txns_involved:
                txn = Transaction.query.get(txn_id)
                if txn:
                    txn.is_flagged = True
                    # Only upgrade risk_level/score if this detector's score is higher
                    if float(r.get("score", 0)) > float(txn.risk_score or 0):
                        txn.risk_score = float(r.get("score", 0))
                        txn.risk_level = r.get("severity", "low")

    if isinstance(result, list):
        for r in result:
            process_result(r)
    else:
        process_result(result)
        
    db.session.commit()

def run_silent_analysis(statement_id, case_id):
    """
    Runs all detectors after upload.
    """
    results = []
    
    # Needs graph for M2
    graph = get_graph_from_db(case_id)
    
    # Circular Flow
    try:
        cf_results = detect_circular_flow(graph)
        save_detection_result(cf_results, case_id, statement_id)
        results.extend(cf_results)
    except Exception as e:
        print(f"Error in CircularFlow: {e}")
        
    # Layering Chain
    try:
        lc_results = find_layering_chains(graph)
        save_detection_result(lc_results, case_id, statement_id)
        results.extend(lc_results)
    except Exception as e:
        print(f"Error in LayeringChain: {e}")
        
    # M3 Detectors
    m3_detectors = [
        detect_large_transaction,
        detect_dormant_revival,
        detect_beneficiary_burst,
        detect_high_risk_time,
        detect_structuring
    ]
    
    for detector in m3_detectors:
        try:
            res = detector(case_id)
            save_detection_result(res, case_id, statement_id)
            if isinstance(res, list):
                results.extend(res)
            else:
                results.append(res)
        except Exception as e:
            print(f"Error in {detector.__name__}: {e}")
            
    # M4 Detectors
    m4_detectors = [
        detect_velocity,
        detect_pass_through,
        detect_cash_cycling
    ]
    
    for detector in m4_detectors:
        try:
            res = detector(case_id)
            save_detection_result(res, case_id, statement_id)
            if isinstance(res, list):
                results.extend(res)
            else:
                results.append(res)
        except Exception as e:
            print(f"Error in {detector.__name__}: {e}")
            
    try:
        update_case_suspicion_score(case_id, results)
    except Exception as e:
        print(f"Error updating score: {e}")
        
    return results

@intelligence_bp.route('/run-silent', methods=['POST'])
@jwt_required()
def run_silent_endpoint():
    data = request.get_json(silent=True) or {}
    statement_id = data.get('statement_id')
    case_id = data.get('case_id')
    if not statement_id or not case_id:
        return jsonify({"error": "statement_id and case_id are required"}), 400
        
    results = run_silent_analysis(statement_id, case_id)
    return jsonify({"status": "success", "detectors_run": len(results)})
