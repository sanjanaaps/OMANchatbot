"""
Database operations for the Document Analyzer application using PostgreSQL and SQLAlchemy
"""

from datetime import datetime
import os
import logging
from sqlalchemy import text, func
from sqlalchemy.exc import SQLAlchemyError
from app_lib.models import db, User, Document, ChatMessage, init_database

logger = logging.getLogger(__name__)

# Database configuration
POSTGRES_URI = os.environ.get('POSTGRES_URI', 'postgresql://postgres:1234@localhost:5432/doc_analyzer')

def get_db():
    """Get database session - maintained for compatibility"""
    return db.session

def init_db(app=None):
    """Initialize database with collections and indexes"""
    try:
        if app:
            init_database(app)
        else:
            # For backward compatibility, try to get app from Flask's current_app
            from flask import current_app
            if current_app:
                init_database(current_app)
            else:
                logger.error("No Flask app context available for database initialization")
                return False
        
        logger.info("Database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        return False

def seed_users():
    """Seed the database with test users"""
    from app_lib.auth import hash_password
    
    test_users = [
        {
            'username': 'finance_user',
            'password_hash': hash_password('finance123'),
            'department': 'Finance'
        },
        {
            'username': 'policy_user',
            'password_hash': hash_password('policy123'),
            'department': 'Monetary Policy & Banking'
        },
        {
            'username': 'currency_user',
            'password_hash': hash_password('currency123'),
            'department': 'Currency'
        },
        {
            'username': 'legal_user',
            'password_hash': hash_password('legal123'),
            'department': 'Legal & Compliance'
        },
        {
            'username': 'itfinance_user',
            'password_hash': hash_password('itfinance123'),
            'department': 'IT / Finance'
        }
    ]
    
    try:
        # Clear existing users (for development)
        User.query.delete()
        
        # Insert test users
        for user_data in test_users:
            user = User(**user_data)
            db.session.add(user)
        
        db.session.commit()
        logger.info(f"Seeded {len(test_users)} test users")
        
        # Print user credentials for testing
        print("\n" + "="*50)
        print("TEST USER CREDENTIALS:")
        print("="*50)
        for user_data in test_users:
            print(f"Username: {user_data['username']}")
            print(f"Password: {user_data['username'].split('_')[0]}123")
            print(f"Department: {user_data['department']}")
            print("-" * 30)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to seed users: {str(e)}")
        db.session.rollback()
        return False

def get_user_by_username(username):
    """Get user by username"""
    try:
        return User.query.filter_by(username=username).first()
    except Exception as e:
        logger.error(f"Error getting user {username}: {str(e)}")
        return None

def get_user_by_id(user_id):
    """Get user by ID"""
    try:
        return User.query.get(user_id)
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}")
        return None

def save_document(document_data):
    """Save document to database"""
    try:
        document = Document(**document_data)
        db.session.add(document)
        db.session.commit()
        return document.id
    except Exception as e:
        logger.error(f"Error saving document: {str(e)}")
        db.session.rollback()
        return None

def get_documents_by_department(department, limit=None):
    """Get documents by department"""
    try:
        query = Document.query.filter_by(department=department).order_by(Document.upload_date.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    except Exception as e:
        logger.error(f"Error getting documents for department {department}: {str(e)}")
        return []

def search_documents_in_db(query, department):
    """Search documents in database using PostgreSQL full-text search"""
    try:
        # PostgreSQL full-text search using to_tsquery
        search_query = text("""
            SELECT *, ts_rank(to_tsvector('english', content), to_tsquery('english', :search_term)) as rank
            FROM documents 
            WHERE department = :department 
            AND (to_tsvector('english', content) @@ to_tsquery('english', :search_term)
                 OR to_tsvector('english', filename) @@ to_tsquery('english', :search_term))
            ORDER BY rank DESC
        """)
        
        # Prepare search term for to_tsquery (replace spaces with & for AND operation)
        search_term = ' & '.join(query.split())
        
        result = db.session.execute(search_query, {
            'search_term': search_term,
            'department': department
        })
        
        documents = []
        for row in result:
            doc_dict = {
                'id': row.id,
                'filename': row.filename,
                'department': row.department,
                'uploaded_by': row.uploaded_by,
                'upload_date': row.upload_date,
                'content': row.content,
                'file_type': row.file_type,
                'file_size': row.file_size,
                'summary': row.summary,
                'score': float(row.rank) if row.rank else 0.0
            }
            documents.append(doc_dict)
        
        return documents
        
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        # Fallback to simple LIKE search if full-text search fails
        try:
            search_pattern = f"%{query}%"
            documents = Document.query.filter(
                Document.department == department,
                (Document.content.ilike(search_pattern) | Document.filename.ilike(search_pattern))
            ).order_by(Document.upload_date.desc()).all()
            
            return [doc.to_dict() for doc in documents]
        except Exception as e2:
            logger.error(f"Fallback search also failed: {str(e2)}")
            return []

def get_document_by_id(document_id):
    """Get document by ID"""
    try:
        return Document.query.get(document_id)
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {str(e)}")
        return None

def get_chat_messages_by_user(user_id, limit=20):
    """Get chat messages for a user"""
    try:
        return ChatMessage.query.filter_by(user_id=user_id).order_by(ChatMessage.timestamp.desc()).limit(limit).all()
    except Exception as e:
        logger.error(f"Error getting chat messages for user {user_id}: {str(e)}")
        return []

def save_chat_message(message_data):
    """Save chat message to database"""
    try:
        message = ChatMessage(**message_data)
        db.session.add(message)
        db.session.commit()
        return message.id
    except Exception as e:
        logger.error(f"Error saving chat message: {str(e)}")
        db.session.rollback()
        return None

def get_document_count_by_department(department):
    """Get document count for a department"""
    try:
        return Document.query.filter_by(department=department).count()
    except Exception as e:
        logger.error(f"Error getting document count for department {department}: {str(e)}")
        return 0

def delete_document(document_id):
    """Delete a document"""
    try:
        document = Document.query.get(document_id)
        if document:
            db.session.delete(document)
            db.session.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}")
        db.session.rollback()
        return False

def update_document_summary(document_id, summary):
    """Update document summary"""
    try:
        document = Document.query.get(document_id)
        if document:
            document.summary = summary
            document.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating document summary {document_id}: {str(e)}")
        db.session.rollback()
        return False

def get_recent_documents_by_department(department, limit=10):
    """Get recent documents for a department"""
    try:
        return Document.query.filter_by(department=department).order_by(Document.upload_date.desc()).limit(limit).all()
    except Exception as e:
        logger.error(f"Error getting recent documents for department {department}: {str(e)}")
        return []

def get_user_statistics(user_id):
    """Get user statistics"""
    try:
        user = User.query.get(user_id)
        if not user:
            return None
            
        doc_count = Document.query.filter_by(department=user.department).count()
        message_count = ChatMessage.query.filter_by(user_id=user_id).count()
        
        return {
            'user': user.to_dict(),
            'document_count': doc_count,
            'message_count': message_count
        }
    except Exception as e:
        logger.error(f"Error getting user statistics for {user_id}: {str(e)}")
        return None

def check_database_connection():
    """Check if database connection is working"""
    try:
        db.session.execute(text('SELECT 1'))
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False