import uuid
from datetime import datetime, timezone
from app.extensions import db

class EvidenceItem(db.Model):
    __tablename__ = 'evidence_items'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = db.Column(db.String(36), db.ForeignKey('cases.id'), nullable=False)
    item_type = db.Column(db.String(50), nullable=False) # statement/screenshot/note/report
    file_path = db.Column(db.String(500), nullable=True)
    note_text = db.Column(db.Text, nullable=True)
    uploaded_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<EvidenceItem {self.id} {self.item_type}>'
