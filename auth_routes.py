"""
Authentication and User Management Routes
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import db, User, ParentalControl
from email_validator import validate_email, EmailNotValidError
import re
from datetime import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user
    Required: email, username, password, age
    Optional: is_kids_mode
    """
    try:
        data = request.get_json()
        
        # Validation
        if not data or not all(key in data for key in ['email', 'username', 'password', 'age']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        email = data['email'].strip().lower()
        username = data['username'].strip()
        password = data['password']
        age = data['age']
        is_kids_mode = data.get('is_kids_mode', False)
        
        # Validate email
        try:
            validate_email(email)
        except EmailNotValidError:
            return jsonify({'error': 'Invalid email address'}), 400
        
        # Validate username (3-20 chars, alphanumeric and underscore only)
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
            return jsonify({'error': 'Username must be 3-20 characters (letters, numbers, underscore)'}), 400
        
        # Validate password (minimum 8 characters)
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        
        # Validate age
        try:
            age = int(age)
            if age < 6 or age > 120:
                return jsonify({'error': 'Age must be between 6 and 120'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Age must be a valid number'}), 400
        
        # Check if email exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        # Check if username exists
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already taken'}), 400
        
        # Create user
        user = User(
            email=email,
            username=username,
            age=age,
            is_kids_mode=is_kids_mode and age <= 12
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Create parental control if kids mode
        if user.is_kids_mode:
            parent_email = data.get('parent_email', email)
            parental_control = ParentalControl(
                user_id=user.id,
                parent_email=parent_email
            )
            db.session.add(parental_control)
            db.session.commit()
        
        # Generate token
        access_token = create_access_token(identity=user.id)
        
        return jsonify({
            'message': 'Registration successful',
            'user': user.to_dict(include_email=True),
            'access_token': access_token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login user
    Required: email, password
    """
    try:
        data = request.get_json()
        
        if not data or not all(key in data for key in ['email', 'password']):
            return jsonify({'error': 'Missing email or password'}), 400
        
        email = data['email'].strip().lower()
        password = data['password']
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        access_token = create_access_token(identity=user.id)
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(include_email=True),
            'access_token': access_token
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current authenticated user"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = user.to_dict(include_email=True)
        
        # Add parental control info if available
        if user.parental_control:
            data['parental_control'] = user.parental_control.to_dict()
        
        return jsonify(data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """
    Update user profile
    Optional: bio, profile_picture_url
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        if 'bio' in data:
            user.bio = data['bio'][:500]  # Max 500 chars
        
        if 'profile_picture_url' in data:
            user.profile_picture_url = data['profile_picture_url']
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated',
            'user': user.to_dict(include_email=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """
    Change user password
    Required: current_password, new_password
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        if not data or not all(key in data for key in ['current_password', 'new_password']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        if not user.check_password(data['current_password']):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        if len(data['new_password']) < 8:
            return jsonify({'error': 'New password must be at least 8 characters'}), 400
        
        user.set_password(data['new_password'])
        db.session.commit()
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
