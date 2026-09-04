"""
Feed and Posts Routes
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Post, User, Like, Share, Follow
from ai_filter import ContentFilter
from datetime import datetime
from config import config

feed_bp = Blueprint('feed', __name__, url_prefix='/api/feed')
content_filter = ContentFilter(config['default'])

@feed_bp.route('/posts', methods=['POST'])
@jwt_required()
def create_post():
    """
    Create a new post
    Required: content
    Optional: image_url
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        if not data or 'content' not in data:
            return jsonify({'error': 'Content is required'}), 400
        
        content = data['content'].strip()
        
        if not content:
            return jsonify({'error': 'Content cannot be empty'}), 400
        
        if len(content) > 5000:
            return jsonify({'error': 'Content too long (max 5000 characters)'}), 400
        
        # Filter content
        filter_result = content_filter.filter_content(content)
        
        if user.is_kids_mode and not filter_result['is_safe']:
            return jsonify({
                'error': 'Content violates safety guidelines',
                'reason': filter_result['reason']
            }), 400
        
        post = Post(
            user_id=user_id,
            content=content,
            image_url=data.get('image_url', ''),
            is_flagged=not filter_result['is_safe'],
            is_ai_slop=filter_result['ai_slop'][0],
            content_filter_score=filter_result['overall_score']
        )
        
        db.session.add(post)
        db.session.commit()
        
        return jsonify({
            'message': 'Post created',
            'post': post.to_dict(current_user_id=user_id)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@feed_bp.route('/posts/<post_id>', methods=['GET'])
@jwt_required()
def get_post(post_id):
    """Get a specific post"""
    try:
        user_id = get_jwt_identity()
        post = Post.query.get(post_id)
        
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        return jsonify(post.to_dict(current_user_id=user_id)), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@feed_bp.route('/posts/<post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    """Delete own post"""
    try:
        user_id = get_jwt_identity()
        post = Post.query.get(post_id)
        
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        if post.user_id != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        db.session.delete(post)
        db.session.commit()
        
        return jsonify({'message': 'Post deleted'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@feed_bp.route('/feed', methods=['GET'])
@jwt_required()
def get_feed():
    """
    Get personalized feed
    Query params: page (default 1), limit (default 20)
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 20, type=int), 100)
        
        # Get IDs of users being followed
        following_ids = [f.following_id for f in user.following]
        following_ids.append(user_id)  # Include own posts
        
        # Get posts from followed users
        posts = Post.query.filter(
            Post.user_id.in_(following_ids),
            Post.is_flagged == False
        ).order_by(Post.created_at.desc()).paginate(page=page, per_page=limit)
        
        return jsonify({
            'posts': [post.to_dict(current_user_id=user_id) for post in posts.items],
            'total': posts.total,
            'pages': posts.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@feed_bp.route('/posts/<post_id>/like', methods=['POST'])
@jwt_required()
def like_post(post_id):
    """Like a post"""
    try:
        user_id = get_jwt_identity()
        post = Post.query.get(post_id)
        
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        # Check if already liked
        existing_like = Like.query.filter_by(user_id=user_id, post_id=post_id).first()
        
        if existing_like:
            return jsonify({'error': 'Already liked'}), 400
        
        like = Like(user_id=user_id, post_id=post_id)
        db.session.add(like)
        db.session.commit()
        
        return jsonify({
            'message': 'Post liked',
            'likes_count': len(post.likes)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@feed_bp.route('/posts/<post_id>/unlike', methods=['POST'])
@jwt_required()
def unlike_post(post_id):
    """Unlike a post"""
    try:
        user_id = get_jwt_identity()
        like = Like.query.filter_by(user_id=user_id, post_id=post_id).first()
        
        if not like:
            return jsonify({'error': 'Not liked'}), 400
        
        db.session.delete(like)
        db.session.commit()
        
        post = Post.query.get(post_id)
        return jsonify({
            'message': 'Like removed',
            'likes_count': len(post.likes)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@feed_bp.route('/posts/<post_id>/share', methods=['POST'])
@jwt_required()
def share_post(post_id):
    """Share a post"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        post = Post.query.get(post_id)
        
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        # Check parental controls
        if user.is_kids_mode and user.parental_control:
            if not user.parental_control.sharing_enabled:
                return jsonify({'error': 'Sharing disabled by parental controls'}), 403
        
        # Check if already shared
        existing_share = Share.query.filter_by(user_id=user_id, post_id=post_id).first()
        if existing_share:
            return jsonify({'error': 'Already shared'}), 400
        
        share = Share(user_id=user_id, post_id=post_id)
        db.session.add(share)
        db.session.commit()
        
        return jsonify({
            'message': 'Post shared',
            'shares_count': len(post.shares)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
