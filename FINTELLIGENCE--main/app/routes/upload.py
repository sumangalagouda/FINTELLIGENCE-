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
    display_id = None
    if not case_id:
        new_case = Case(
            title=f"Investigation: {file.filename}",
            created_by=current_user,
            assigned_to=current_user
        )
        db.session.add(new_case)
        db.session.commit()
        case_id = new_case.id
        display_id = new_case.display_id
    else:
        existing_case = Case.query.get(case_id)
        if existing_case:
            display_id = existing_case.display_id
        
    if file and allowed_file(file.filename):
        ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
        count = Statement.query.filter_by(case_id=case_id).count() + 1
        
        # Use display_id for the filename if available
        display_str = f"case{display_id}" if display_id else case_id
        
        if count == 1:
            filename = f"bank_statement_{display_str}.{ext}"
        else:
            filename = f"bank_statement_{display_str}_{count}.{ext}"
            
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'evidence', case_id, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
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
        
        # Add to Evidence Locker automatically
        from app.models.evidence_item import EvidenceItem
        evidence = EvidenceItem(
            case_id=case_id,
            item_type="statement",
            file_path=filepath,
            uploaded_by=current_user,
            note_text=f"Uploaded Bank Statement"
        )
        db.session.add(evidence)
        db.session.commit()
        
        try:
            # 1 & 2: Extract details and remove failed transactions using statement_extractor.py
            from app.parsers.statement_extractor import extract_statement
            
            extracted_data = extract_statement(filepath)
            bank_detected = extracted_data.get('account', {}).get('bank_name', 'UNKNOWN')
            extracted_txns = extracted_data.get('transactions', [])
            
            # 3: Format the cleaned transactions so they can pass through the normalizer parsing logic
            raw_txns = []
            for t in extracted_txns:
                raw_txns.append({
                    "raw_text": str(t.get('description', '')),
                    "parsed_data": {
                        "Date": t.get('date'),
                        "Description": str(t.get('description', '')),
                        "Credit": t.get('credit'),
                        "Debit": t.get('debit'),
                        "Balance": t.get('balance'),
                        "is_failed": t.get('is_failed', False),
                        "failure_reason": t.get('failure_reason')
                    }
                })
                
            # Run normalizer (which extracts sender/receiver accounts)
            normalized_txns = process_and_normalize(raw_txns, statement.id, case_id)
            
            # Save to PostgreSQL
            # Load existing beneficiaries
            beneficiaries_map = {}
            from app.models.beneficiary import Beneficiary
            for b in Beneficiary.query.filter_by(case_id=case_id).all():
                beneficiaries_map[b.account_number] = b

            for txn_data in normalized_txns:
                db_data = txn_data.copy()
                if 'txn_id' in db_data:
                    db_data['id'] = db_data.pop('txn_id')
                if 'description' in db_data and db_data['description']:
                    db_data['description'] = str(db_data['description'])[:500]
                txn = Transaction(**db_data)
                db.session.add(txn)
                
                # Update Beneficiaries
                sender = txn_data.get('sender_account')
                receiver = txn_data.get('receiver_account')
                amt = float(txn_data.get('amount') or 0.0)
                
                if sender:
                    if sender not in beneficiaries_map:
                        b = Beneficiary(case_id=case_id, account_number=sender, total_sent=0.0, total_received=0.0, transaction_count=0)
                        db.session.add(b)
                        beneficiaries_map[sender] = b
                    if beneficiaries_map[sender].total_sent is None:
                        beneficiaries_map[sender].total_sent = 0.0
                    if beneficiaries_map[sender].transaction_count is None:
                        beneficiaries_map[sender].transaction_count = 0
                        
                    beneficiaries_map[sender].total_sent += amt
                    beneficiaries_map[sender].transaction_count += 1
                    
                if receiver:
                    if receiver not in beneficiaries_map:
                        b = Beneficiary(case_id=case_id, account_number=receiver, total_sent=0.0, total_received=0.0, transaction_count=0)
                        db.session.add(b)
                        beneficiaries_map[receiver] = b
                    if beneficiaries_map[receiver].total_received is None:
                        beneficiaries_map[receiver].total_received = 0.0
                    if beneficiaries_map[receiver].transaction_count is None:
                        beneficiaries_map[receiver].transaction_count = 0
                        
                    beneficiaries_map[receiver].total_received += amt
                    beneficiaries_map[receiver].transaction_count += 1
                
            acc_info = extracted_data.get('account', {})
            statement.bank_name = bank_detected
            statement.account_number = acc_info.get('account_number')
            statement.account_holder = acc_info.get('account_holder_name')
            
            import datetime
            def parse_iso_date(d_str):
                if not d_str: return None
                try:
                    return datetime.date.fromisoformat(d_str.split('T')[0])
                except Exception:
                    return None
                    
            statement.statement_period_start = parse_iso_date(acc_info.get('statement_period_from'))
            statement.statement_period_end = parse_iso_date(acc_info.get('statement_period_to'))

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
            from app.intelligence.silent_engine import run_silent_analysis
            run_silent_analysis(statement.id, case_id)
            
            return jsonify({
                "statement_id": statement.id,
                "case_id": case_id,
                "display_id": display_id,
                "transactions_count": len(normalized_txns),
                "bank_detected": bank_detected,
                "status": "success"
            }), 200
            
        except Exception as e:
            statement.upload_status = 'failed'
            db.session.commit()
            return jsonify({"error": str(e)}), 500
            
    return jsonify({"error": "File type not allowed"}), 400
