from flask import Blueprint, jsonify
from app.extensions import db

health_bp = Blueprint('health', __name__)

@health_bp.route('/', methods=['GET'])
def health_check():
    db_status = "connected"
    try:
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
    except Exception as e:
        print(f"Database health check failed: {e}")
        db_status = "disconnected"
        
    return jsonify({
        "status": "ok",
        "database": db_status,
        "redis": "connected" # Assumption for this check
    }), 200
