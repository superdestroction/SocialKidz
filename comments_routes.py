"""
Comments Routes
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Comment, Post, User, CommentLike
from ai_filter import ContentFilter
from datetime import datetime
from config import config

comments_bp = Blueprint('comments', __name__, url_prefix='/api/comments')
content_filter = ContentFilter(config['default'])

@comments_bp.route('/posts/<post_id>/comments', methods=['POST'])
@jwt_required()
def create_comment(post_id):
    """
    Create a comment on a post
    Required: content
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        post = Post.query.get(post_id)
        
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check parental controls
        if user.is_kids_mode and user.parental_control:
            if not user.parental_control.comments_enabled:
                return jsonify({'error': 'Comments disabled by parental controls'}), 403
        
        data = request.get_json()
        
        if not data or 'content' not in data:
            return jsonify({'error': 'Content is required'}), 400
        
        content = data['content'].strip()
        
        if not content:
            return jsonify({'error': 'Content cannot be empty'}), 400
        
        if len(content) > 1000:
            return jsonify({'error': 'Comment too long (max 1000 characters)'}), 400
        
        # Filter content
        filter_result = content_filter.filter_content(content)
        
        if user.is_kids_mode and not filter_result['is_safe']:
            return jsonify({
                'error': 'Comment violates safety guidelines',
                'reason': filter_result['reason']
            }), 400
        
        comment = Comment(
            post_id=post_id,
            user_id=user_id,
            content=content,
            is_flagged=not filter_result['is_safe'],
            content_filter_score=filter_result['overall_score']
        )
        
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({
            'message': 'Comment created',
            'comment': comment.to_dict(current_user_id=user_id)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@comments_bp.route('/posts/<post_id>/comments', methods=['GET'])
@jwt_required()
def get_comments(post_id):
    """
    Get comments for a post
    Query params: page (default 1), limit (default 20)
    """
    try:
        user_id = get_jwt_identity()
        post = Post.query.get(post_id)
        
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 20, type=int), 100)
        
        comments = Comment.query.filter_by(
            post_id=post_id,
            is_flagged=False
        ).order_by(Comment.created_at.desc()).paginate(page=page, per_page=limit)
        
        return jsonify({
            'comments': [comment.to_dict(current_user_id=user_id) for comment in comments.items],
            'total': comments.total,
            'pages': comments.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@comments_bp.route('/comments/<comment_id>', methods=['DELETE'])
@jwt_required()
def delete_comment(comment_id):
    """Delete own comment"""
    try:
        user_id = get_jwt_identity()
        comment = Comment.query.get(comment_id)
        
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404
        
        if comment.user_id != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        db.session.delete(comment)
        db.session.commit()
        
        return jsonify({'message': 'Comment deleted'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@comments_bp.route('/comments/<comment_id>/like', methods=['POST'])
@jwt_required()
def like_comment(comment_id):
    """Like a comment"""
    try:
        user_id = get_jwt_identity()
        comment = Comment.query.get(comment_id)
        
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404
        
        # Check if already liked
        existing_like = CommentLike.query.filter_by(user_id=user_id, comment_id=comment_id).first()
        
        if existing_like:
            return jsonify({'error': 'Already liked'}), 400
        
        like = CommentLike(user_id=user_id, comment_id=comment_id)
        db.session.add(like)
        db.session.commit()
        
        return jsonify({
            'message': 'Comment liked',
            'likes_count': len(comment.likes)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@comments_bp.route('/comments/<comment_id>/unlike', methods=['POST'])
@jwt_required()
def unlike_comment(comment_id):
    """Unlike a comment"""
    try:
        user_id = get_jwt_identity()
        like = CommentLike.query.filter_by(user_id=user_id, comment_id=comment_id).first()
        
        if not like:
            return jsonify({'error': 'Not liked'}), 400
        
        db.session.delete(like)
        db.session.commit()
        
        comment = Comment.query.get(comment_id)
        return jsonify({
            'message': 'Like removed',
            'likes_count': len(comment.likes)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
