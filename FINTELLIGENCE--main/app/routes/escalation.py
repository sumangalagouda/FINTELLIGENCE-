import os
from flask import Blueprint, jsonify, request, current_app
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.case import Case
from app.models.case_escalation import CaseEscalation
from app.models.user import User
from app.models.evidence_item import EvidenceItem
from app.intelligence.escalation import determine_escalation


escalation_bp = Blueprint('escalation', __name__, url_prefix='/api')


@escalation_bp.route('/cases/<case_id>/escalate', methods=['POST'])
@jwt_required()
def escalate_case(case_id: str):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 403
    if user.role not in ['investigator', 'investigating_officer', 'admin', 'aml_analyst', 'cyber_crime_investigator', 'compliance_officer']:
        return jsonify({"error": f"Unauthorized. Your role is '{user.role}', but you do not have permission to escalate."}), 403
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form

    reason = data.get('reason')

    # Only allow if case is visible/owned by investigator
    c = Case.query.get_or_404(case_id)
    if not ((c.created_by == user_id) or (c.assigned_to == user_id)):
        return jsonify({"error": "Case not accessible"}), 403

    # Optional helper: auto recommendation (not persisted unless we want to)
    _ = determine_escalation(case_id)

    sig_pwd = data.get('signature_password')
    if not sig_pwd:
        return jsonify({"error": "Digital signature password required to escalate case"}), 400
    
    from werkzeug.security import check_password_hash
    if not check_password_hash(user.password_hash, sig_pwd):
        return jsonify({"error": "Invalid digital signature"}), 403

    # Handle file upload if present
    if 'evidence_file' in request.files:
        file = request.files['evidence_file']
        if file and file.filename:
            filename = secure_filename(file.filename)
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            
            # Save file as evidence
            evidence = EvidenceItem(
                case_id=case_id,
                item_type='escalation_document',
                file_path=file_path,
                uploaded_by=user_id,
                note_text=f"ESCALATION DOCUMENT\n\nUploaded by: {user.name}"
            )
            db.session.add(evidence)

    esc = CaseEscalation(
        case_id=case_id,
        escalated_by=user_id,
        escalated_to=None,
        escalation_reason=reason,
        status='pending'
    )
    db.session.add(esc)

    # Update existing case.status (stringly typed in schema)
    c.status = 'escalated'
    db.session.commit()

    return jsonify({"status": "pending", "escalation_id": esc.id}), 201


@escalation_bp.route('/escalations', methods=['GET'])
@jwt_required()
def get_escalations():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != 'supervisor':
        return jsonify({"error": "Unauthorized"}), 403

    q = CaseEscalation.query.order_by(CaseEscalation.created_at.desc())
    items = q.all()

    return jsonify([
        {
            "id": e.id,
            "case_id": e.case_id,
            "escalated_by": e.escalated_by,
            "escalation_reason": e.escalation_reason,
            "status": e.status,
            "fir_recommended": e.fir_recommended,
            "reviewer_notes": e.reviewer_notes,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
        } for e in items
    ]), 200


@escalation_bp.route('/escalations/<esc_id>', methods=['POST'])
@jwt_required()
def escalation_action(esc_id: str):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != 'supervisor':
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json(silent=True) or {}
    action = data.get('action')
    notes = data.get('notes', '')

    if action not in ['close', 'recommend_fir']:
        return jsonify({"error": "Invalid action"}), 400

    esc = CaseEscalation.query.get_or_404(esc_id)
    c = Case.query.get_or_404(esc.case_id)

    esc.reviewed_by = user_id
    esc.reviewer_notes = notes
    esc.status = 'under_review'

    if action == 'close':
        esc.status = 'closed'
        esc.resolved_at = db.func.now()
        c.status = 'closed'
    elif action == 'recommend_fir':
        esc.fir_recommended = True
        esc.status = 'under_review'
        # Leave Case.status update to existing governance/FIR gate flow.
        # This keeps it additive and avoids changing M3/M4 readiness logic.

    db.session.commit()

    return jsonify({"status": esc.status, "fir_recommended": esc.fir_recommended}), 200

