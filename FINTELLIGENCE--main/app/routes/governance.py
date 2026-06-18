from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.case import Case
from app.models.verification import Verification
from app.models.supervisor_approval import SupervisorApproval
from app.models.audit_trail import AuditTrail
from app.models.investigator_note import InvestigatorNote
from app.models.user import User
from app.intelligence.audit_logger import log_action
from app.intelligence.mismatch_detector import check_mismatch
from app.intelligence.fir_readiness import calculate_fir_readiness
from datetime import datetime, timezone

governance_bp = Blueprint('governance', __name__, url_prefix='/api/governance')

# ----------------- Verification Center -----------------
@governance_bp.route('/verification/<case_id>', methods=['GET'])
@jwt_required()
def get_verification(case_id):
    v = Verification.query.filter_by(case_id=case_id).first()
    if not v:
        return jsonify({"message": "No verification checklist found."}), 404
        
    return jsonify({
        "id": v.id,
        "case_id": v.case_id,
        "customer_contacted": v.customer_contacted,
        "documents_received": v.documents_received,
        "source_verified": v.source_verified,
        "additional_notes": v.additional_notes,
        "completion_percentage": v.completion_percentage
    })

@governance_bp.route('/verification/<case_id>', methods=['POST'])
@jwt_required()
def update_verification(case_id):
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    
    v = Verification.query.filter_by(case_id=case_id).first()
    if not v:
        v = Verification(case_id=case_id)
        db.session.add(v)
        
    old_state = {
        "customer_contacted": v.customer_contacted,
        "documents_received": v.documents_received,
        "source_verified": v.source_verified
    }
        
    v.customer_contacted = data.get('customer_contacted', v.customer_contacted)
    v.documents_received = data.get('documents_received', v.documents_received)
    v.source_verified = data.get('source_verified', v.source_verified)
    v.additional_notes = data.get('additional_notes', v.additional_notes)
    v.verified_by = user_id
    v.verified_at = datetime.now(timezone.utc)
    
    completed = sum([1 for x in [v.customer_contacted, v.documents_received, v.source_verified] if x])
    v.completion_percentage = (completed / 3.0) * 100.0
    
    db.session.commit()
    
    new_state = {
        "customer_contacted": v.customer_contacted,
        "documents_received": v.documents_received,
        "source_verified": v.source_verified,
        "completion_percentage": v.completion_percentage
    }
    
    log_action(case_id, "verification_updated", user_id, old_val=old_state, new_val=new_state)
    
    return jsonify(new_state)

# ----------------- Supervisor Approval Gate -----------------
@governance_bp.route('/fir-gate/<case_id>', methods=['GET'])
@jwt_required()
def check_fir_gate(case_id):
    v = Verification.query.filter_by(case_id=case_id).first()
    v_pct = v.completion_percentage if v else 0.0
    
    approval = SupervisorApproval.query.filter_by(case_id=case_id).order_by(SupervisorApproval.requested_at.desc()).first()
    app_status = approval.status if approval else "none"
    
    fir_data = calculate_fir_readiness(case_id)
    
    gate_open = all([
        v_pct == 100.0,
        app_status == "approved",
        fir_data.get("ready", False)
    ])
    
    return jsonify({
        "gate_open": gate_open,
        "checklist_complete": v_pct == 100.0,
        "supervisor_approved": app_status == "approved",
        "fir_score_sufficient": fir_data.get("ready", False),
        "fir_score": fir_data.get("fir_readiness_score", 0.0)
    })

@governance_bp.route('/supervisor-approve/<case_id>', methods=['POST'])
@jwt_required()
def supervisor_approve(case_id):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.role != 'supervisor':
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.get_json(silent=True) or {}
    status = data.get('status')
    notes = data.get('notes', '')
    
    if status not in ['approved', 'rejected']:
        return jsonify({"error": "Status must be approved or rejected"}), 400
        
    approval = SupervisorApproval.query.filter_by(case_id=case_id, status='pending').first()
    if not approval:
        approval = SupervisorApproval(case_id=case_id, requested_by=user_id)
        db.session.add(approval)
        
    approval.status = status
    approval.notes = notes
    approval.approved_by = user_id
    approval.decided_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    log_action(case_id, f"supervisor_{status}", user_id, notes=notes)
    
    return jsonify({"message": f"Case {status} by supervisor."})

# ----------------- Audit Trail -----------------
@governance_bp.route('/audit/<case_id>', methods=['GET'])
@jwt_required()
def get_audit_trail(case_id):
    trails = AuditTrail.query.filter_by(case_id=case_id).order_by(AuditTrail.created_at.desc()).all()
    results = []
    for t in trails:
        results.append({
            "id": t.id,
            "action": t.action,
            "performed_by": t.performed_by,
            "old_value": t.old_value,
            "new_value": t.new_value,
            "notes": t.notes,
            "created_at": t.created_at.isoformat() if t.created_at else None
        })
    return jsonify(results)

# ----------------- Mismatch Detector -----------------
@governance_bp.route('/check-mismatch/<case_id>', methods=['POST'])
@jwt_required()
def trigger_mismatch_check(case_id):
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    decision = data.get('decision')
    
    if not decision:
        return jsonify({"error": "decision is required"}), 400
        
    result = check_mismatch(case_id, decision, user_id)
    return jsonify(result)

# ----------------- Investigator Notes -----------------
@governance_bp.route('/notes/<case_id>', methods=['GET', 'POST'])
@jwt_required()
def investigator_notes(case_id):
    user_id = get_jwt_identity()
    
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        text = data.get('note_text')
        if not text:
            return jsonify({"error": "note_text is required"}), 400
            
        note = InvestigatorNote(case_id=case_id, note_text=text, author_id=user_id)
        db.session.add(note)
        db.session.commit()
        log_action(case_id, "note_added", user_id)
        return jsonify({"message": "Note added successfully."}), 201
        
    notes = InvestigatorNote.query.filter_by(case_id=case_id).order_by(InvestigatorNote.created_at.desc()).all()
    results = []
    for n in notes:
        results.append({
            "id": n.id,
            "note_text": n.note_text,
            "author_id": n.author_id,
            "created_at": n.created_at.isoformat() if n.created_at else None
        })
    return jsonify(results)

# ----------------- Accountability Dashboard -----------------
# ----------------- Accountability Dashboard -----------------

@governance_bp.route('/accountability-dashboard', methods=['GET'])
@jwt_required()
def accountability_dashboard():

    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({
            "error": "User not found"
        }), 404

    if user.role != 'supervisor':
        return jsonify({
            "error": "Unauthorized"
        }), 403

    investigators = User.query.filter_by(
        role='investigator'
    ).all()

    results = []

    for inv in investigators:

        # ----------------------------------------
        # Case Statistics
        # ----------------------------------------

        assigned = Case.query.filter_by(
            assigned_to=inv.id
        ).count()

        closed = Case.query.filter_by(
            assigned_to=inv.id,
            status='closed'
        ).count()

        escalated = Case.query.filter_by(
            assigned_to=inv.id,
            status='supervisor_review'
        ).count()

        # ----------------------------------------
        # Override Statistics
        # ----------------------------------------

        override_logs = AuditTrail.query.filter_by(
            performed_by=inv.id,
            action='mismatch_override'
        ).all()

        override_events = len(override_logs)

        # Unique cases overridden
        override_case_ids = {
            log.case_id
            for log in override_logs
        }

        override_cases = len(
            override_case_ids
        )

        # ----------------------------------------
        # Override Rate
        # ----------------------------------------

        if assigned > 0:
            override_rate = (
                override_cases /
                assigned
            ) * 100
        else:
            override_rate = 0.0

        # ----------------------------------------
        # Investigator Risk Score
        # ----------------------------------------

        risk_score = min(
            round(
                override_rate,
                1
            ),
            100
        )

        # ----------------------------------------
        # Dashboard Row
        # ----------------------------------------

        results.append({

            "user_id": inv.id,

            "name": inv.name,

            "email": inv.email,

            "total_assigned": assigned,

            "cases_closed": closed,

            "cases_escalated": escalated,

            # New metrics
            "ai_override_events": override_events,

            "ai_override_cases": override_cases,

            "override_rate_pct": round(
                override_rate,
                1
            ),

            "investigator_risk_score": risk_score

        })

    return jsonify(results)


# ----------------- Investigator Risk -----------------

@governance_bp.route(
    '/investigator-risk/<inv_id>',
    methods=['GET']
)
@jwt_required()
def investigator_risk(inv_id):

    investigator = User.query.get(inv_id)

    if not investigator:
        return jsonify({
            "error": "Investigator not found"
        }), 404

    assigned = Case.query.filter_by(
        assigned_to=inv_id
    ).count()

    override_logs = AuditTrail.query.filter_by(
        performed_by=inv_id,
        action='mismatch_override'
    ).all()

    override_events = len(
        override_logs
    )

    override_case_ids = {
        log.case_id
        for log in override_logs
    }

    override_cases = len(
        override_case_ids
    )

    if assigned > 0:
        override_rate = (
            override_cases /
            assigned
        ) * 100
    else:
        override_rate = 0.0

    return jsonify({

        "user_id": inv_id,

        "investigator_name": investigator.name,

        "total_assigned": assigned,

        "ai_override_events": override_events,

        "ai_override_cases": override_cases,

        "override_rate_pct": round(
            override_rate,
            1
        )

    })