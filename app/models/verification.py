import uuid
from datetime import datetime, timezone
from app.extensions import db

class Verification(db.Model):
    __tablename__ = 'verification_checklist'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = db.Column(db.String(36), db.ForeignKey('cases.id'), nullable=False)
    customer_contacted = db.Column(db.Boolean, default=False)
    documents_received = db.Column(db.Boolean, default=False)
    source_verified = db.Column(db.Boolean, default=False)
    additional_notes = db.Column(db.Text, nullable=True)
    verified_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    completion_percentage = db.Column(db.Float, default=0.0)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Verification {self.case_id}>'
