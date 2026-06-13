import uuid
from datetime import datetime, timezone
from app.extensions import db

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    statement_id = db.Column(db.String(36), db.ForeignKey('statements.id'), nullable=False)
    case_id = db.Column(db.String(36), db.ForeignKey('cases.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False) # credit/debit
    sender_account = db.Column(db.String(100), nullable=True)
    receiver_account = db.Column(db.String(100), nullable=True)
    description = db.Column(db.String(500), nullable=True)
    balance_after = db.Column(db.Float, nullable=True)
    raw_text = db.Column(db.Text, nullable=True)
    is_flagged = db.Column(db.Boolean, default=False)
    risk_score = db.Column(db.Float, default=0.0)
    risk_level = db.Column(db.String(50), default='low') # low/medium/high/critical

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    detection_results = db.relationship('DetectionResult', backref='transaction', lazy=True)

    def __repr__(self):
        return f'<Transaction {self.id} {self.type} {self.amount}>'
