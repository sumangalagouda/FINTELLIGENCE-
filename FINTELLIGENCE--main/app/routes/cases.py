import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.case import Case
from app.models.statement import Statement
from app.models.transaction import Transaction
from app.models.beneficiary import Beneficiary
from app.models.audit_trail import AuditTrail
from app.models.user import User
from app.models.evidence_item import EvidenceItem
from werkzeug.security import check_password_hash
from app.extensions import db, limiter

cases_bp = Blueprint('cases', __name__)

@cases_bp.route('/', methods=['GET'])
@jwt_required()
@limiter.limit("30 per minute")
def get_cases():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if user and user.role == 'supervisor':
        cases = Case.query.filter(Case.status.in_(['escalated', 'pending_sio_closure', 'closed'])).all()
    else:
        cases = Case.query.filter((Case.created_by == current_user_id) | (Case.assigned_to == current_user_id)).all()
    
    return jsonify([{
        "id": c.id,
        "display_id": getattr(c, 'display_id', None),
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
    account_holder = "Unknown"
    account_number = "Unknown"
    bank_name = "Unknown"
    account_type = "Unknown"
    statement_period = "Unknown"
    total_debited = 0.0
    total_credited = 0.0
    
    if c.statements:
        s = c.statements[0]
        account_holder = s.account_holder or account_holder
        account_number = s.account_number or account_number
        bank_name = s.bank_name or bank_name
        if s.statement_period_start and s.statement_period_end:
            statement_period = f"{s.statement_period_start.isoformat()} -> {s.statement_period_end.isoformat()}"
            
    txns = Transaction.query.filter_by(case_id=c.id).all()
    for t in txns:
        if t.type == 'debit':
            total_debited += float(t.amount)
        elif t.type == 'credit':
            total_credited += float(t.amount)

    return jsonify({
        "id": c.id,
        "display_id": getattr(c, 'display_id', None),
        "title": c.title,
        "description": c.description,
        "status": c.status,
        "severity": c.severity,
        "risk_level": c.risk_level,
        "suspicion_score": c.suspicion_score,
        "account_holder": account_holder,
        "account_number": account_number,
        "bank_name": bank_name,
        "account_type": account_type,
        "statement_period": statement_period,
        "total_debited": total_debited,
        "total_credited": total_credited,
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
        "description": t.description,
        "sender_account": t.sender_account,
        "receiver_account": t.receiver_account,
        "is_flagged": t.is_flagged,
        "risk_level": t.risk_level
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
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    c = Case.query.get_or_404(case_id)
    
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form

    new_status = data.get('status')
    
    # Specific logic for Investigator closing a case with digital signature
    if new_status == 'closed':
        closing_reason = data.get('closing_reason')
        signature_password = data.get('signature_password')
        
        if not closing_reason or not signature_password:
            return jsonify({"msg": "Closing reason and digital signature (password) are required to close a case."}), 400
            
        if not check_password_hash(user.password_hash, signature_password):
            return jsonify({"msg": "Invalid digital signature (incorrect password)."}), 401
            
        # File upload handling
        file_path = None
        if 'evidence_file' in request.files:
            file = request.files['evidence_file']
            if file and file.filename:
                filename = secure_filename(file.filename)
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                evidence_dir = os.path.join(upload_folder, 'evidence', case_id)
                os.makedirs(evidence_dir, exist_ok=True)
                file_path = os.path.join(evidence_dir, filename)
                file.save(file_path)

        # Threshold check
        if c.suspicion_score >= 70.0 and user.role != 'supervisor':
            new_status = 'pending_sio_closure'
            note_content = f"CASE SUBMITTED FOR SIO CLOSURE\n\nReason: {closing_reason}\nDigitally Signed By: {user.name} ({user.email})"
        else:
            note_content = f"CASE CLOSED\n\nReason: {closing_reason}\nDigitally Signed By: {user.name} ({user.email})"
            
            # Auto-resolve any pending escalations
            from app.models.case_escalation import CaseEscalation
            pending_escalations = CaseEscalation.query.filter_by(case_id=case_id, status='pending').all()
            for esc in pending_escalations:
                esc.status = 'closed'
                esc.resolved_at = db.func.now()
                esc.reviewed_by = current_user_id
                esc.reviewer_notes = f"Case closed by {user.role}. Remarks: {closing_reason}"
                
        if not file_path:
            import time
            timestamp = int(time.time())
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            evidence_dir = os.path.join(upload_folder, 'evidence', case_id)
            os.makedirs(evidence_dir, exist_ok=True)
            filename = f"closing_{case_id}_{timestamp}.txt"
            file_path = os.path.join(evidence_dir, filename)
            with open(file_path, 'w') as f:
                f.write(note_content)

        # Create a Document in Evidence Locker
        evidence = EvidenceItem(
            case_id=case_id,
            item_type='closing_document',
            file_path=file_path,
            uploaded_by=current_user_id,
            note_text=note_content
        )
        db.session.add(evidence)
    
    old_status = c.status
    c.status = new_status
    
    audit = AuditTrail(
        case_id=c.id,
        action="STATUS_CHANGE",
        performed_by=current_user_id,
        old_value={"status": old_status},
        new_value={"status": new_status},
        ip_address=request.remote_addr
    )
    
    db.session.add(audit)
    db.session.commit()
    
    return jsonify({"msg": "Status updated"}), 200
