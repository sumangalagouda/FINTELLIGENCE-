from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models.transaction import Transaction
from app.models.statement import Statement
from app.extensions import limiter

transactions_bp = Blueprint('transactions', __name__)

@transactions_bp.route('/<statement_id>', methods=['GET'])
@jwt_required()
@limiter.limit("30 per minute")
def get_transactions(statement_id):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    pagination = Transaction.query.filter_by(statement_id=statement_id).paginate(page=page, per_page=per_page, error_out=False)
    
    items = []
    for txn in pagination.items:
        items.append({
            "id": txn.id,
            "date": txn.date.isoformat() if txn.date else None,
            "amount": txn.amount,
            "type": txn.type,
            "description": txn.description,
            "is_flagged": txn.is_flagged,
            "risk_level": txn.risk_level
        })
        
    return jsonify({
        "transactions": items,
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": page
    }), 200

@transactions_bp.route('/<statement_id>/summary', methods=['GET'])
@jwt_required()
@limiter.limit("30 per minute")
def get_summary(statement_id):
    txns = Transaction.query.filter_by(statement_id=statement_id).all()
    
    total_credits = sum(t.amount for t in txns if t.type == 'credit')
    total_debits = sum(t.amount for t in txns if t.type == 'debit')
    
    dates = [t.date for t in txns if t.date]
    date_range = {
        "start": min(dates).isoformat() if dates else None,
        "end": max(dates).isoformat() if dates else None
    }
    
    unique_accounts = set(t.sender_account for t in txns if t.sender_account) | \
                      set(t.receiver_account for t in txns if t.receiver_account)
                      
    return jsonify({
        "total_credits": total_credits,
        "total_debits": total_debits,
        "date_range": date_range,
        "unique_accounts_count": len(unique_accounts)
    }), 200

@transactions_bp.route('/<txn_id>/detail', methods=['GET'])
@jwt_required()
@limiter.limit("30 per minute")
def get_transaction_detail(txn_id):
    txn = Transaction.query.get_or_404(txn_id)
    
    results = []
    for dr in txn.detection_results:
        results.append({
            "detector": dr.detector_name,
            "triggered": dr.triggered,
            "score": dr.score,
            "reason": dr.reason,
            "severity": dr.severity
        })
        
    return jsonify({
        "transaction": {
            "id": txn.id,
            "date": txn.date.isoformat() if txn.date else None,
            "amount": txn.amount,
            "type": txn.type,
            "sender_account": txn.sender_account,
            "receiver_account": txn.receiver_account,
            "description": txn.description,
            "balance_after": txn.balance_after,
            "is_flagged": txn.is_flagged,
            "risk_score": txn.risk_score,
            "risk_level": txn.risk_level
        },
        "detection_results": results
    }), 200
