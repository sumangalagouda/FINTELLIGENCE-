from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.case import Case
from app.models.statement import Statement
from app.models.transaction import Transaction
from app.models.beneficiary import Beneficiary
from app.models.audit_trail import AuditTrail
from app.extensions import db, limiter

cases_bp = Blueprint('cases', __name__)

@cases_bp.route('/', methods=['GET'])
@jwt_required()
@limiter.limit("30 per minute")
def get_cases():
    current_user = get_jwt_identity()
    cases = Case.query.filter((Case.created_by == current_user) | (Case.assigned_to == current_user)).all()
    
    return jsonify([{
        "id": c.id,
        "title": c.title,
        "status": c.status,
        "severity": c.severity,
        "risk_level": c.risk_level,
        "created_at": c.created_at.isoformat()
    } for c in cases]), 200

@cases_bp.route('/', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def create_case():
    current_user = get_jwt_identity()
    data = request.get_json()
    
    new_case = Case(
        title=data.get('title'),
        description=data.get('description'),
        severity=data.get('severity', 'medium'),
        created_by=current_user,
        assigned_to=data.get('assigned_to', current_user)
    )
    db.session.add(new_case)
    db.session.commit()
    
    return jsonify({"msg": "Case created", "id": new_case.id}), 201

@cases_bp.route('/<case_id>', methods=['GET'])
@jwt_required()
@limiter.limit("30 per minute")
def get_case_detail(case_id):
    c = Case.query.get_or_404(case_id)
    return jsonify({
        "id": c.id,
        "title": c.title,
        "description": c.description,
        "status": c.status,
        "severity": c.severity,
        "risk_level": c.risk_level,
        "suspicion_score": c.suspicion_score,
        "statements": [{"id": s.id, "filename": s.filename, "status": s.upload_status} for s in c.statements]
    }), 200

@cases_bp.route('/<case_id>/transactions', methods=['GET'])
@jwt_required()
@limiter.limit("30 per minute")
def get_case_transactions(case_id):
    txns = Transaction.query.filter_by(case_id=case_id).limit(100).all() # Simplification
    return jsonify([{
        "id": t.id,
        "date": t.date.isoformat() if t.date else None,
        "amount": t.amount,
        "type": t.type,
        "description": t.description
    } for t in txns]), 200

@cases_bp.route('/<case_id>/beneficiaries', methods=['GET'])
@jwt_required()
@limiter.limit("30 per minute")
def get_case_beneficiaries(case_id):
    bens = Beneficiary.query.filter_by(case_id=case_id).all()
    return jsonify([{
        "account_number": b.account_number,
        "name": b.name,
        "total_received": b.total_received,
        "risk_score": b.risk_score,
        "is_flagged": b.is_flagged
    } for b in bens]), 200

@cases_bp.route('/<case_id>/status', methods=['PATCH'])
@jwt_required()
@limiter.limit("10 per minute")
def update_case_status(case_id):
    current_user = get_jwt_identity()
    data = request.get_json()
    new_status = data.get('status')
    
    c = Case.query.get_or_404(case_id)
    old_status = c.status
    c.status = new_status
    
    audit = AuditTrail(
        case_id=c.id,
        action="STATUS_CHANGE",
        performed_by=current_user,
        old_value={"status": old_status},
        new_value={"status": new_status},
        ip_address=request.remote_addr
    )
    
    db.session.add(audit)
    db.session.commit()
    
    return jsonify({"msg": "Status updated"}), 200
