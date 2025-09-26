"""
Configuration settings for Oman Central Bank Document Analyzer
"""

import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database Configuration (MongoDB)
    MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017')
    MONGODB_DB_NAME = os.environ.get('MONGODB_DB_NAME', 'doc_analyzer')

    # Email (Gmail SMTP) for OTP
    SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    SMTP_FROM = os.environ.get('SMTP_FROM', SMTP_USERNAME)
    
    # File Upload Configuration
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'png', 'jpg', 'jpeg', 'tiff'}
    
    # AI Configuration
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    
    # Search Configuration
    SEARCH_THRESHOLD = 0.3  # Minimum score for local search before using AI fallback
    MAX_SEARCH_RESULTS = 10
    SUMMARY_MAX_SENTENCES = 3
    
    # Text Processing Configuration
    CHUNK_SIZE = 4000  # For large document processing
    CHUNK_OVERLAP = 200
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    
    # Security Configuration
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True  # Requires HTTPS

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    MONGODB_URI = 'mongodb://localhost:27017'
    MONGODB_DB_NAME = 'test_doc_analyzer'
    SMTP_HOST = 'smtp.gmail.com'
    SMTP_PORT = 587
    SMTP_USERNAME = ''
    SMTP_PASSWORD = ''
    SMTP_FROM = ''

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
