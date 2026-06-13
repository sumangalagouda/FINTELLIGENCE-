import uuid
from datetime import datetime, timezone
from app.extensions import db

class SupervisorApproval(db.Model):
    __tablename__ = 'supervisor_approvals'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = db.Column(db.String(36), db.ForeignKey('cases.id'), nullable=False)
    requested_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    approved_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String(50), default='pending') # pending/approved/rejected
    notes = db.Column(db.Text, nullable=True)
    requested_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    decided_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<SupervisorApproval {self.status}>'
