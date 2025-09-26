"""
SQLAlchemy models for the Document Analyzer application
"""

from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index, Text
import uuid

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication and authorization"""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(100), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    documents = db.relationship('Document', backref='uploader', lazy=True)
    chat_messages = db.relationship('ChatMessage', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        """Convert user to dictionary for session storage"""
        return {
            'id': self.id,
            'username': self.username,
            'department': self.department
        }

class Document(db.Model):
    """Document model for storing uploaded files and their metadata"""
    __tablename__ = 'documents'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(100), nullable=False, index=True)
    uploaded_by = db.Column(db.String(80), nullable=False)
    uploader_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    content = db.Column(Text, nullable=False)
    file_type = db.Column(db.String(10), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    summary = db.Column(Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Create indexes for better performance
    __table_args__ = (
        Index('idx_documents_department_upload_date', 'department', 'upload_date'),
        Index('idx_documents_content_search', 'content', postgresql_using='gin'),
        Index('idx_documents_filename_search', 'filename', postgresql_using='gin'),
    )
    
    def __repr__(self):
        return f'<Document {self.filename}>'
    
    def to_dict(self):
        """Convert document to dictionary"""
        return {
            'id': self.id,
            'filename': self.filename,
            'department': self.department,
            'uploaded_by': self.uploaded_by,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'summary': self.summary,
            'content_preview': self.content[:200] + '...' if len(self.content) > 200 else self.content
        }

class ChatMessage(db.Model):
    """Chat message model for storing conversation history"""
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    type = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(Text, nullable=False)
    language = db.Column(db.String(5), default='en', nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    department = db.Column(db.String(100), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Create indexes for better performance
    __table_args__ = (
        Index('idx_chat_messages_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_chat_messages_department_timestamp', 'department', 'timestamp'),
    )
    
    def __repr__(self):
        return f'<ChatMessage {self.type}: {self.content[:50]}...>'
    
    def to_dict(self):
        """Convert chat message to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type,
            'content': self.content,
            'language': self.language,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'department': self.department
        }

def init_database(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create full-text search indexes for PostgreSQL
        try:
            # Create GIN index for full-text search on document content
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_content_gin 
                ON documents USING gin(to_tsvector('english', content))
            """)
            
            # Create GIN index for full-text search on document filename
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_filename_gin 
                ON documents USING gin(to_tsvector('english', filename))
            """)
            
            print("✓ Database tables and indexes created successfully")
        except Exception as e:
            print(f"Warning: Could not create full-text search indexes: {e}")
            print("The application will still work, but search performance may be slower")

def drop_all_tables():
    """Drop all tables (for testing/development)"""
    db.drop_all()
    print("All tables dropped")

def get_db_session():
    """Get database session"""
    return db.session
