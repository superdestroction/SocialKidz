"""
User Profile and Social Routes
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Follow
from datetime import datetime

users_bp = Blueprint('users', __name__, url_prefix='/api/users')

@users_bp.route('/<username>', methods=['GET'])
@jwt_required()
def get_user_profile(username):
    """Get user profile by username"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = user.to_dict()
        
        # Add follow status
        is_following = Follow.query.filter_by(
            follower_id=current_user_id,
            following_id=user.id
        ).first() is not None
        
        data['is_following'] = is_following
        data['posts'] = [post.to_dict(current_user_id=current_user_id) for post in user.posts[:10]]
        
        return jsonify(data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/<username>/follow', methods=['POST'])
@jwt_required()
def follow_user(username):
    """Follow a user"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        target_user = User.query.filter_by(username=username).first()
        
        if not target_user:
            return jsonify({'error': 'User not found'}), 404
        
        if current_user_id == target_user.id:
            return jsonify({'error': 'Cannot follow yourself'}), 400
        
        # Check parental controls
        if current_user.is_kids_mode and current_user.parental_control:
            if not current_user.parental_control.can_follow:
                return jsonify({'error': 'Following disabled by parental controls'}), 403
        
        # Check if already following
        existing_follow = Follow.query.filter_by(
            follower_id=current_user_id,
            following_id=target_user.id
        ).first()
        
        if existing_follow:
            return jsonify({'error': 'Already following'}), 400
        
        follow = Follow(follower_id=current_user_id, following_id=target_user.id)
        db.session.add(follow)
        db.session.commit()
        
        return jsonify({
            'message': f'Now following {username}',
            'following_count': len(current_user.following)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@users_bp.route('/<username>/unfollow', methods=['POST'])
@jwt_required()
def unfollow_user(username):
    """Unfollow a user"""
    try:
        current_user_id = get_jwt_identity()
        target_user = User.query.filter_by(username=username).first()
        
        if not target_user:
            return jsonify({'error': 'User not found'}), 404
        
        follow = Follow.query.filter_by(
            follower_id=current_user_id,
            following_id=target_user.id
        ).first()
        
        if not follow:
            return jsonify({'error': 'Not following'}), 400
        
        db.session.delete(follow)
        db.session.commit()
        
        current_user = User.query.get(current_user_id)
        return jsonify({
            'message': f'Unfollowed {username}',
            'following_count': len(current_user.following)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@users_bp.route('/<username>/followers', methods=['GET'])
@jwt_required()
def get_followers(username):
    """
    Get followers of a user
    Query params: page (default 1), limit (default 20)
    """
    try:
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 20, type=int), 100)
        
        follows = Follow.query.filter_by(following_id=user.id).paginate(page=page, per_page=limit)
        followers = [follow.follower_user.to_dict() for follow in follows.items]
        
        return jsonify({
            'followers': followers,
            'total': follows.total,
            'pages': follows.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/<username>/following', methods=['GET'])
@jwt_required()
def get_following(username):
    """
    Get users followed by a user
    Query params: page (default 1), limit (default 20)
    """
    try:
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 20, type=int), 100)
        
        follows = Follow.query.filter_by(follower_id=user.id).paginate(page=page, per_page=limit)
        following = [follow.following_user.to_dict() for follow in follows.items]
        
        return jsonify({
            'following': following,
            'total': follows.total,
            'pages': follows.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/search', methods=['GET'])
@jwt_required()
def search_users():
    """
    Search for users by username or bio
    Query params: q (required), page (default 1), limit (default 20)
    """
    try:
        q = request.args.get('q', '').strip()
        
        if not q or len(q) < 2:
            return jsonify({'error': 'Search query must be at least 2 characters'}), 400
        
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 20, type=int), 100)
        
        # Search by username or bio
        users = User.query.filter(
            (User.username.ilike(f'%{q}%')) | (User.bio.ilike(f'%{q}%'))
        ).paginate(page=page, per_page=limit)
        
        return jsonify({
            'users': [user.to_dict() for user in users.items],
            'total': users.total,
            'pages': users.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
