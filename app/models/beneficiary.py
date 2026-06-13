import uuid
from datetime import datetime, timezone
from app.extensions import db

class Beneficiary(db.Model):
    __tablename__ = 'beneficiaries'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = db.Column(db.String(36), db.ForeignKey('cases.id'), nullable=False)
    account_number = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(255), nullable=True)
    bank_name = db.Column(db.String(100), nullable=True)
    total_received = db.Column(db.Float, default=0.0)
    total_sent = db.Column(db.Float, default=0.0)
    transaction_count = db.Column(db.Integer, default=0)
    first_seen = db.Column(db.Date, nullable=True)
    last_seen = db.Column(db.Date, nullable=True)
    risk_score = db.Column(db.Float, default=0.0)
    is_flagged = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('case_id', 'account_number', name='uq_case_account'),
    )

    def __repr__(self):
        return f'<Beneficiary {self.account_number}>'
