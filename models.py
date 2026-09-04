from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.Text, default='')
    profile_picture_url = db.Column(db.String(500), default='')
    age = db.Column(db.Integer)
    is_kids_mode = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    posts = db.relationship('Post', backref='author', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy=True, cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='user', lazy=True, cascade='all, delete-orphan')
    followers = db.relationship('Follow', foreign_keys='Follow.follower_id', backref='follower_user', lazy=True, cascade='all, delete-orphan')
    following = db.relationship('Follow', foreign_keys='Follow.following_id', backref='following_user', lazy=True, cascade='all, delete-orphan')
    parental_control = db.relationship('ParentalControl', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self, include_email=False):
        data = {
            'id': self.id,
            'username': self.username,
            'bio': self.bio,
            'profile_picture_url': self.profile_picture_url,
            'age': self.age,
            'is_kids_mode': self.is_kids_mode,
            'followers_count': len(self.followers),
            'following_count': len(self.following),
            'posts_count': len(self.posts),
            'created_at': self.created_at.isoformat()
        }
        if include_email:
            data['email'] = self.email
        return data

class Post(db.Model):
    __tablename__ = 'posts'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500))
    is_flagged = db.Column(db.Boolean, default=False)
    is_ai_slop = db.Column(db.Boolean, default=False)
    content_filter_score = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    comments = db.relationship('Comment', backref='post', lazy=True, cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='post', lazy=True, cascade='all, delete-orphan')
    shares = db.relationship('Share', backref='post', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self, current_user_id=None):
        return {
            'id': self.id,
            'author': self.author.to_dict(),
            'content': self.content,
            'image_url': self.image_url,
            'likes_count': len(self.likes),
            'comments_count': len(self.comments),
            'shares_count': len(self.shares),
            'is_liked_by_user': any(like.user_id == current_user_id for like in self.likes) if current_user_id else False,
            'is_flagged': self.is_flagged,
            'is_ai_slop': self.is_ai_slop,
            'created_at': self.created_at.isoformat()
        }

class Comment(db.Model):
    __tablename__ = 'comments'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = db.Column(db.String(36), db.ForeignKey('posts.id'), nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    is_flagged = db.Column(db.Boolean, default=False)
    content_filter_score = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    likes = db.relationship('CommentLike', backref='comment', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self, current_user_id=None):
        return {
            'id': self.id,
            'post_id': self.post_id,
            'author': self.author.to_dict(),
            'content': self.content,
            'likes_count': len(self.likes),
            'is_liked_by_user': any(like.user_id == current_user_id for like in self.likes) if current_user_id else False,
            'is_flagged': self.is_flagged,
            'created_at': self.created_at.isoformat()
        }

class Like(db.Model):
    __tablename__ = 'likes'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    post_id = db.Column(db.String(36), db.ForeignKey('posts.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_post_like'),)

class CommentLike(db.Model):
    __tablename__ = 'comment_likes'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    comment_id = db.Column(db.String(36), db.ForeignKey('comments.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'comment_id', name='unique_comment_like'),)

class Share(db.Model):
    __tablename__ = 'shares'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    post_id = db.Column(db.String(36), db.ForeignKey('posts.id'), nullable=False, index=True)
    shared_at = db.Column(db.DateTime, default=datetime.utcnow)

class Follow(db.Model):
    __tablename__ = 'follows'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    follower_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    following_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('follower_id', 'following_id', name='unique_follow'),)

class ParentalControl(db.Model):
    __tablename__ = 'parental_controls'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, unique=True)
    parent_email = db.Column(db.String(120), nullable=False)
    screen_time_limit = db.Column(db.Integer, default=120)  # minutes
    content_filter_enabled = db.Column(db.Boolean, default=True)
    comments_enabled = db.Column(db.Boolean, default=True)
    sharing_enabled = db.Column(db.Boolean, default=True)
    can_follow = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'parent_email': self.parent_email,
            'screen_time_limit': self.screen_time_limit,
            'content_filter_enabled': self.content_filter_enabled,
            'comments_enabled': self.comments_enabled,
            'sharing_enabled': self.sharing_enabled,
            'can_follow': self.can_follow,
            'created_at': self.created_at.isoformat()
        }

class ContentReport(db.Model):
    __tablename__ = 'content_reports'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reporter_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    content_type = db.Column(db.String(50), nullable=False)  # 'post' or 'comment'
    content_id = db.Column(db.String(36), nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')  # pending, reviewed, resolved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
