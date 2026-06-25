from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.case import Case
from app.models.statement import Statement
from app.models.transaction import Transaction
from app.models.detection_result import DetectionResult


dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


@dashboard_bp.route('/overview', methods=['GET'])
@jwt_required()
def overview():
    # Current DB schema doesn’t include organization on cases/users yet.
    # We implement additive, best-effort overview across all cases for the authenticated user
    # based on Case.created_by/assigned_to.
    user_id = get_jwt_identity()

    visible_cases_q = Case.query.filter((Case.created_by == user_id) | (Case.assigned_to == user_id))

    visible_case_ids = [c.id for c in visible_cases_q.with_entities(Case.id).all()]
    if not visible_case_ids:
        return jsonify({
            "total_statements": 0,
            "total_transactions": 0,
            "high_risk_cases": 0,
            "aml_alerts": 0
        }), 200

    total_statements = db.session.query(db.func.count(Statement.id)).filter(Statement.case_id.in_(visible_case_ids)).scalar() or 0
    total_transactions = db.session.query(db.func.count(Transaction.id)).filter(Transaction.case_id.in_(visible_case_ids)).scalar() or 0

    high_risk_cases = db.session.query(db.func.count(Case.id)).filter(
        Case.id.in_(visible_case_ids),
        Case.risk_level.in_(['high', 'critical'])
    ).scalar() or 0

    aml_alerts = db.session.query(db.func.count(DetectionResult.id)).filter(
        DetectionResult.case_id.in_(visible_case_ids),
        DetectionResult.triggered.is_(True)
    ).scalar() or 0

    from sqlalchemy.exc import OperationalError, ProgrammingError
    from app.intelligence.silent_engine import run_silent_analysis

    detector_firings = {}
    try:
        firings = db.session.query(
            DetectionResult.detector_name,
            db.func.count(DetectionResult.id)
        ).filter(
            DetectionResult.case_id.in_(visible_case_ids),
            DetectionResult.triggered.is_(True)
        ).group_by(DetectionResult.detector_name).all()
        
        if not firings:
            # Maybe table exists but empty, try backfilling visible cases
            for cid in visible_case_ids:
                stmts = Statement.query.filter_by(case_id=cid).all()
                for s in stmts:
                    run_silent_analysis(s.id, cid)
            
            firings = db.session.query(
                DetectionResult.detector_name,
                db.func.count(DetectionResult.id)
            ).filter(
                DetectionResult.case_id.in_(visible_case_ids),
                DetectionResult.triggered.is_(True)
            ).group_by(DetectionResult.detector_name).all()

        detector_firings = {name: count for name, count in firings}
    except (OperationalError, ProgrammingError):
        # Table might not exist, create it and backfill
        db.session.rollback()
        DetectionResult.__table__.create(db.engine, checkfirst=True)
        for cid in visible_case_ids:
            stmts = Statement.query.filter_by(case_id=cid).all()
            for s in stmts:
                run_silent_analysis(s.id, cid)
        
        firings = db.session.query(
            DetectionResult.detector_name,
            db.func.count(DetectionResult.id)
        ).filter(
            DetectionResult.case_id.in_(visible_case_ids),
            DetectionResult.triggered.is_(True)
        ).group_by(DetectionResult.detector_name).all()
        detector_firings = {name: count for name, count in firings}

    return jsonify({
        "total_statements": int(total_statements),
        "total_transactions": int(total_transactions),
        "high_risk_cases": int(high_risk_cases),
        "aml_alerts": int(aml_alerts),
        "detector_firings": detector_firings
    }), 200

@dashboard_bp.route('/backfill', methods=['GET'])
def backfill():
    try:
        from app.models.detection_result import DetectionResult
        from app.models.statement import Statement
        from app.intelligence.silent_engine import run_silent_analysis
        
        # Create table
        DetectionResult.__table__.create(db.engine, checkfirst=True)
        
        # Clear and backfill
        db.session.query(DetectionResult).delete()
        db.session.commit()
        
        statements = Statement.query.all()
        count = 0
        for s in statements:
            if s.case_id:
                res = run_silent_analysis(s.id, s.case_id)
                if res:
                    count += len(res)
        return jsonify({"status": "success", "total_generated": count}), 200
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

