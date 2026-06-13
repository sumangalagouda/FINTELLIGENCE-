from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, limiter
from app.models.user import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    role = data.get('role', 'investigator')
    
    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Email already exists"}), 400
        
    hashed_password = generate_password_hash(password)
    new_user = User(email=email, password_hash=hashed_password, name=name, role=role)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"msg": "User created successfully"}), 201

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"msg": "Bad email or password"}), 401
        
    access_token = create_access_token(identity=str(user.id), additional_claims={"role": user.role, "email": user.email})
    return jsonify(access_token=access_token), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    current_user = get_jwt_identity()
    user = User.query.get(current_user)
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    return jsonify({
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "is_active": user.is_active
    }), 200

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    # In a real app, you might want to implement token blocklisting here
    return jsonify({"msg": "Successfully logged out"}), 200
