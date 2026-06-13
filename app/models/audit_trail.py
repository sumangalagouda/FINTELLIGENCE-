import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import JSON
from app.extensions import db

class AuditTrail(db.Model):
    __tablename__ = 'audit_trail'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = db.Column(db.String(36), db.ForeignKey('cases.id'), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    performed_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    old_value = db.Column(JSON, nullable=True)
    new_value = db.Column(JSON, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<AuditTrail {self.action}>'
