import uuid
from datetime import datetime, timezone
from app.extensions import db

class Case(db.Model):
    __tablename__ = 'cases'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    display_id = db.Column(db.Integer, server_default=db.FetchedValue(), unique=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='open') # open/under_review/escalated/closed/flagged_for_audit
    severity = db.Column(db.String(50), default='medium') # low/medium/high/critical
    assigned_to = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    fir_readiness_score = db.Column(db.Float, default=0.0)
    suspicion_score = db.Column(db.Float, default=0.0)
    risk_level = db.Column(db.String(50), default='low') # low/medium/high/critical

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    statements = db.relationship('Statement', backref='case', lazy=True)
    transactions = db.relationship('Transaction', backref='case', lazy=True)
    beneficiaries = db.relationship('Beneficiary', backref='case', lazy=True)
    detection_results = db.relationship('DetectionResult', backref='case', lazy=True)
    verification_checklist = db.relationship('Verification', backref='case', uselist=False)
    audit_trails = db.relationship('AuditTrail', backref='case', lazy=True)
    supervisor_approvals = db.relationship('SupervisorApproval', backref='case', lazy=True)

    def __repr__(self):
        return f'<Case {self.title}>'
