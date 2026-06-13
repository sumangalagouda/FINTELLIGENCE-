import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import JSON
from app.extensions import db

class DetectionResult(db.Model):
    __tablename__ = 'detection_results'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = db.Column(db.String(36), db.ForeignKey('cases.id'), nullable=False)
    statement_id = db.Column(db.String(36), db.ForeignKey('statements.id'), nullable=False)
    txn_id = db.Column(db.String(36), db.ForeignKey('transactions.id'), nullable=True)
    detector_name = db.Column(db.String(100), nullable=False)
    triggered = db.Column(db.Boolean, default=False)
    score = db.Column(db.Float, nullable=False) # 0-100
    reason = db.Column(db.Text, nullable=True)
    transactions_involved = db.Column(JSON, nullable=True) # JSON array of txn_ids
    severity = db.Column(db.String(50), default='low') # low/medium/high/critical

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<DetectionResult {self.detector_name} {self.score}>'
