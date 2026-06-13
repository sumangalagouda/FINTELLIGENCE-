import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app.extensions import db, limiter, socketio
from app.models.case import Case
from app.models.statement import Statement
from app.models.transaction import Transaction
from app.parsers.pdf_parser import parse_pdf
from app.parsers.csv_parser import parse_csv_excel
from app.parsers.ocr_parser import parse_image_or_scanned_pdf
from app.normalizer.normalizer import process_and_normalize

upload_bp = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'csv', 'xls', 'xlsx', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_bp.route('/', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")
def upload_file():
    current_user = get_jwt_identity()
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    case_id = request.form.get('case_id')
    if not case_id:
        return jsonify({"error": "case_id is required"}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower()
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{uuid.uuid4()}_{filename}")
        file.save(filepath)
        
        # Create Statement record
        statement = Statement(
            case_id=case_id,
            filename=filename,
            file_format=ext,
            upload_status='processing',
            uploaded_by=current_user
        )
        db.session.add(statement)
        db.session.commit()
        
        try:
            # Detect format and call parser
            if ext == 'pdf':
                # Logic could be added to check if it's scanned and route to OCR instead
                bank_detected, raw_txns = parse_pdf(filepath)
            elif ext in ['csv', 'xls', 'xlsx']:
                bank_detected, raw_txns = parse_csv_excel(filepath)
            else:
                bank_detected, raw_txns = parse_image_or_scanned_pdf(filepath)
                
            # Run normalizer
            normalized_txns = process_and_normalize(raw_txns, statement.id, case_id)
            
            # Save to PostgreSQL
            for txn_data in normalized_txns:
                db_data = txn_data.copy()
                if 'txn_id' in db_data:
                    db_data['id'] = db_data.pop('txn_id')
                txn = Transaction(**db_data)
                db.session.add(txn)
                
            statement.bank_name = bank_detected
            statement.transaction_count = len(normalized_txns)
            statement.upload_status = 'completed'
            db.session.commit()
            
            # Emit SocketIO event
            socketio.emit('upload_complete', {
                'statement_id': statement.id,
                'case_id': case_id,
                'status': 'success'
            }, room=current_user) # Simplified room logic
            
            # TODO (Later): Fire Celery task asynchronously using .delay() when Celery is enabled
            # from celery_worker import run_silent_analysis
            # run_silent_analysis.delay(statement.id, case_id)
            
            # Running synchronously for now without Celery
            from celery_worker import run_silent_analysis
            run_silent_analysis(statement.id, case_id)
            
            return jsonify({
                "statement_id": statement.id,
                "case_id": case_id,
                "transactions_count": len(normalized_txns),
                "bank_detected": bank_detected,
                "status": "success"
            }), 200
            
        except Exception as e:
            statement.upload_status = 'failed'
            db.session.commit()
            return jsonify({"error": str(e)}), 500
            
    return jsonify({"error": "File type not allowed"}), 400
