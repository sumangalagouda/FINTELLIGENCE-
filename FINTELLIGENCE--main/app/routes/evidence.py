import os
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.evidence_item import EvidenceItem
from app.intelligence.audit_logger import log_action

evidence_bp = Blueprint('evidence', __name__, url_prefix='/api/evidence')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'csv', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@evidence_bp.route('/<case_id>', methods=['GET'])
@jwt_required()
def get_evidence(case_id):
    items = EvidenceItem.query.filter_by(case_id=case_id).order_by(EvidenceItem.created_at.desc()).all()
    results = []
    for item in items:
        results.append({
            "id": item.id,
            "item_type": item.item_type,
            "file_path": item.file_path,
            "note_text": item.note_text,
            "uploaded_by": item.uploaded_by,
            "created_at": item.created_at.isoformat() if item.created_at else None
        })
    return jsonify(results)

@evidence_bp.route('/<case_id>/upload', methods=['POST'])
@jwt_required()
def upload_evidence(case_id):
    user_id = get_jwt_identity()
    item_type = request.form.get('item_type')
    note_text = request.form.get('note_text', '')
    
    if not item_type:
        return jsonify({"error": "item_type is required"}), 400
        
    file_path = None
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'evidence', case_id)
            os.makedirs(save_dir, exist_ok=True)
            path = os.path.join(save_dir, filename)
            file.save(path)
            file_path = path
            
    if not file_path and not note_text:
        return jsonify({"error": "Either file or note_text is required"}), 400
        
    item = EvidenceItem(
        case_id=case_id,
        item_type=item_type,
        file_path=file_path,
        note_text=note_text,
        uploaded_by=user_id
    )
    db.session.add(item)
    db.session.commit()
    
    log_action(case_id, "evidence_uploaded", user_id, notes=f"Uploaded {item_type}")
    
    return jsonify({"message": "Evidence uploaded successfully.", "id": item.id}), 201

@evidence_bp.route('/<item_id>', methods=['DELETE'])
@jwt_required()
def delete_evidence(item_id):
    user_id = get_jwt_identity()
    item = EvidenceItem.query.get(item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
        
    case_id = item.case_id
    if item.file_path and os.path.exists(item.file_path):
        try:
            os.remove(item.file_path)
        except OSError:
            pass
            
    db.session.delete(item)
    db.session.commit()
    
    log_action(case_id, "evidence_deleted", user_id, notes=f"Deleted {item.item_type}")
    
    return jsonify({"message": "Evidence deleted successfully."})

@evidence_bp.route('/<item_id>/download', methods=['GET'])
@jwt_required()
def download_evidence(item_id):
    from flask import send_file
    import os
    item = EvidenceItem.query.get(item_id)
    if not item or not item.file_path:
        return jsonify({"error": "File not found"}), 404
        
    # Resolve relative paths against the project root (CWD) where they were saved
    file_path = item.file_path
    if not os.path.isabs(file_path):
        file_path = os.path.abspath(file_path)
        
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found on disk"}), 404
        
    return send_file(file_path, as_attachment=True)
