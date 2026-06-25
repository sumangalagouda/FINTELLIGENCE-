import os
from app.extensions import db
from app.models.evidence_item import EvidenceItem
from app import create_app

app = create_app()
with app.app_context():
    item = EvidenceItem.query.get('1bceeede-18fd-4091-9b19-705c35272adb')
    if item:
        print(f"File path: {item.file_path}")
        print(f"Exists on disk: {os.path.exists(item.file_path) if item.file_path else 'N/A'}")
        if item.file_path and not os.path.isabs(item.file_path):
            print(f"Absolute path: {os.path.abspath(item.file_path)}")
    else:
        print("Item not found in DB")
