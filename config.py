import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///socialkidz.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=30)
    
    # File Upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Kids Mode Settings
    KIDS_MODE_MIN_AGE = 6
    KIDS_MODE_MAX_AGE = 12
    
    # Parental Controls
    SCREEN_TIME_LIMIT_MINUTES = 120
    CONTENT_FILTER_ENABLED = True
    
    # AI Content Filtering
    AI_MODEL_NAME = 'facebook/bart-large-mnli'
    TOXICITY_THRESHOLD = 0.7
    SLOP_DETECTION_THRESHOLD = 0.6
    
    # API Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_POSTS_PER_HOUR = 20
    RATELIMIT_COMMENTS_PER_HOUR = 50

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
