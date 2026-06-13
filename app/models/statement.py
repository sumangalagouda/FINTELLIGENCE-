import uuid
from datetime import datetime, timezone
from app.extensions import db

class Statement(db.Model):
    __tablename__ = 'statements'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = db.Column(db.String(36), db.ForeignKey('cases.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_format = db.Column(db.String(50), nullable=False) # pdf/csv/excel/scanned_pdf/image
    bank_name = db.Column(db.String(100), nullable=True)
    account_number = db.Column(db.String(100), nullable=True)
    account_holder = db.Column(db.String(255), nullable=True)
    statement_period_start = db.Column(db.Date, nullable=True)
    statement_period_end = db.Column(db.Date, nullable=True)
    upload_status = db.Column(db.String(50), default='processing') # processing/completed/failed
    uploaded_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    transaction_count = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    transactions = db.relationship('Transaction', backref='statement', lazy=True)
    detection_results = db.relationship('DetectionResult', backref='statement', lazy=True)

    def __repr__(self):
        return f'<Statement {self.filename}>'
