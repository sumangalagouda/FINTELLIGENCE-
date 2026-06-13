import uuid
from datetime import datetime, timezone
from app.extensions import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False) # investigator/supervisor/auditor/aml_analyst/compliance_officer/cyber_crime_investigator
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    cases_created = db.relationship('Case', foreign_keys='Case.created_by', backref='creator', lazy=True)
    cases_assigned = db.relationship('Case', foreign_keys='Case.assigned_to', backref='assignee', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'
