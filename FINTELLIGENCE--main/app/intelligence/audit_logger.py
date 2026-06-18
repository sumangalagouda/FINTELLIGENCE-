from app.extensions import db
from app.models.audit_trail import AuditTrail

def log_action(case_id, action, user_id, old_val=None, new_val=None, notes=""):
    try:
        entry = AuditTrail(
            case_id=case_id,
            action=action,
            performed_by=user_id,
            old_value=old_val,
            new_value=new_val,
            notes=notes
        )
        db.session.add(entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Failed to log action: {e}")
