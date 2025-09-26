"""
MongoDB data access layer for the Document Analyzer application
"""

from datetime import datetime, timedelta
import os
import logging
from typing import Optional, List, Dict, Any

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError
from bson import ObjectId

logger = logging.getLogger(__name__)

_mongo_client: Optional[MongoClient] = None
_db = None

def _get_config(app=None):
    if app is not None:
        uri = app.config.get('MONGODB_URI')
        name = app.config.get('MONGODB_DB_NAME')
    else:
        uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017')
        name = os.environ.get('MONGODB_DB_NAME', 'doc_analyzer')
    return uri, name

def init_db(app=None):
    """Initialize MongoDB connection and create indexes."""
    global _mongo_client, _db
    try:
        uri, name = _get_config(app)
        _mongo_client = MongoClient(uri)
        _db = _mongo_client[name]

        # Indexes
        _db.users.create_index([('username', ASCENDING)], unique=True)
        _db.users.create_index([('department', ASCENDING)])
        _db.documents.create_index([('department', ASCENDING), ('upload_date', DESCENDING)])
        _db.documents.create_index([('filename', ASCENDING)])
        _db.chat_messages.create_index([('user_id', ASCENDING), ('timestamp', DESCENDING)])
        _db.chat_messages.create_index([('department', ASCENDING), ('timestamp', DESCENDING)])
        _db.otps.create_index([('username', ASCENDING)], expireAfterSeconds=600)
        _db.otps.create_index([('expires_at', ASCENDING)])

        logger.info("MongoDB initialized successfully")
        return True
    except PyMongoError as e:
        logger.error(f"Failed to initialize MongoDB: {str(e)}")
        return False

def _ensure_connected():
    if _db is None:
        init_db()

def seed_users():
    """Seed the database with test users including a higher authority."""
    from app_lib.auth import hash_password
    _ensure_connected()

    test_users = [
        {'username': 'finance_user', 'password_hash': hash_password('finance123'), 'department': 'Finance', 'role': 'staff', 'email': 'finance@mock.local'},
        {'username': 'policy_user', 'password_hash': hash_password('policy123'), 'department': 'Monetary Policy & Banking', 'role': 'staff', 'email': 'policy@mock.local'},
        {'username': 'currency_user', 'password_hash': hash_password('currency123'), 'department': 'Currency', 'role': 'staff', 'email': 'currency@mock.local'},
        {'username': 'legal_user', 'password_hash': hash_password('legal123'), 'department': 'Legal & Compliance', 'role': 'staff', 'email': 'legal@mock.local'},
        {'username': 'itfinance_user', 'password_hash': hash_password('itfinance123'), 'department': 'IT / Finance', 'role': 'staff', 'email': 'itfinance@mock.local'},
        {'username': 'higher_admin', 'password_hash': hash_password('supersecure'), 'department': 'Executive', 'role': 'higher', 'email': 'admin@mock.local'}
    ]

    try:
        _db.users.delete_many({})
        _db.users.insert_many(test_users)
        logger.info(f"Seeded {len(test_users)} users (including higher authority)")
        return True
    except PyMongoError as e:
        logger.error(f"Failed to seed users: {str(e)}")
        return False

def _as_user_dict(doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not doc:
        return None
    return {
        'id': str(doc.get('_id')),
        'username': doc.get('username'),
        'department': doc.get('department'),
        'password_hash': doc.get('password_hash'),
        'role': doc.get('role', 'staff'),
        'email': doc.get('email')
    }

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    _ensure_connected()
    try:
        doc = _db.users.find_one({'username': username})
        return _as_user_dict(doc)
    except PyMongoError as e:
        logger.error(f"Error getting user {username}: {str(e)}")
        return None

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    _ensure_connected()
    try:
        doc = _db.users.find_one({'_id': ObjectId(user_id)})
        return _as_user_dict(doc)
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}")
        return None

def save_document(document_data: Dict[str, Any]) -> Optional[str]:
    _ensure_connected()
    try:
        document = {
            'filename': document_data.get('filename'),
            'department': document_data.get('department'),
            'uploaded_by': document_data.get('uploaded_by'),
            'content': document_data.get('content'),
            'file_type': document_data.get('file_type'),
            'file_size': document_data.get('file_size'),
            'summary': document_data.get('summary'),
            'upload_date': document_data.get('upload_date') or datetime.utcnow(),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        result = _db.documents.insert_one(document)
        return str(result.inserted_id)
    except PyMongoError as e:
        logger.error(f"Error saving document: {str(e)}")
        return None

def get_documents_by_department(department: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    _ensure_connected()
    try:
        cursor = _db.documents.find({'department': department}).sort('upload_date', DESCENDING)
        if limit:
            cursor = cursor.limit(limit)
        docs = list(cursor)
        for d in docs:
            d['id'] = str(d.pop('_id'))
        return docs
    except PyMongoError as e:
        logger.error(f"Error getting documents for department {department}: {str(e)}")
        return []

def search_documents_in_db(query: str, department: str) -> List[Dict[str, Any]]:
    _ensure_connected()
    try:
        regex = {'$regex': query, '$options': 'i'}
        cursor = _db.documents.find({
            'department': department,
            '$or': [
                {'content': regex},
                {'filename': regex}
            ]
        }).limit(20)
        results = []
        for row in cursor:
            score = min(1.0, max(0.1, len(query) / 50.0))
            results.append({
                'id': str(row.get('_id')),
                'filename': row.get('filename'),
                'department': row.get('department'),
                'uploaded_by': row.get('uploaded_by'),
                'upload_date': row.get('upload_date'),
                'content': row.get('content'),
                'file_type': row.get('file_type'),
                'file_size': row.get('file_size'),
                'summary': row.get('summary'),
                'score': float(score)
            })
        return results
    except PyMongoError as e:
        logger.error(f"Error searching documents: {str(e)}")
        return []

def get_document_by_id(document_id: str) -> Optional[Dict[str, Any]]:
    _ensure_connected()
    try:
        doc = _db.documents.find_one({'_id': ObjectId(document_id)})
        if not doc:
            return None
        doc['id'] = str(doc.pop('_id'))
        return doc
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {str(e)}")
        return None

def get_chat_messages_by_user(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    _ensure_connected()
    try:
        cursor = _db.chat_messages.find({'user_id': user_id}).sort('timestamp', DESCENDING).limit(limit)
        msgs = []
        for m in cursor:
            m['id'] = str(m.pop('_id'))
            msgs.append(m)
        return msgs
    except PyMongoError as e:
        logger.error(f"Error getting chat messages for user {user_id}: {str(e)}")
        return []

def save_chat_message(message_data: Dict[str, Any]) -> Optional[str]:
    _ensure_connected()
    try:
        message = {
            'user_id': message_data.get('user_id'),
            'type': message_data.get('type'),
            'content': message_data.get('content'),
            'language': message_data.get('language', 'en'),
            'timestamp': message_data.get('timestamp') or datetime.utcnow(),
            'department': message_data.get('department'),
            'created_at': datetime.utcnow()
        }
        result = _db.chat_messages.insert_one(message)
        return str(result.inserted_id)
    except PyMongoError as e:
        logger.error(f"Error saving chat message: {str(e)}")
        return None

def get_document_count_by_department(department: str) -> int:
    _ensure_connected()
    try:
        return _db.documents.count_documents({'department': department})
    except PyMongoError as e:
        logger.error(f"Error getting document count for department {department}: {str(e)}")
        return 0

def delete_document(document_id: str) -> bool:
    _ensure_connected()
    try:
        result = _db.documents.delete_one({'_id': ObjectId(document_id)})
        return result.deleted_count == 1
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}")
        return False

def update_document_summary(document_id: str, summary: str) -> bool:
    _ensure_connected()
    try:
        res = _db.documents.update_one({'_id': ObjectId(document_id)}, {'$set': {'summary': summary, 'updated_at': datetime.utcnow()}})
        return res.modified_count == 1
    except Exception as e:
        logger.error(f"Error updating document summary {document_id}: {str(e)}")
        return False

def get_recent_documents_by_department(department: str, limit: int = 10) -> List[Dict[str, Any]]:
    _ensure_connected()
    try:
        cursor = _db.documents.find({'department': department}).sort('upload_date', DESCENDING).limit(limit)
        docs = []
        for d in cursor:
            d['id'] = str(d.pop('_id'))
            docs.append(d)
        return docs
    except PyMongoError as e:
        logger.error(f"Error getting recent documents for department {department}: {str(e)}")
        return []

def get_user_statistics(user_id: str) -> Optional[Dict[str, Any]]:
    _ensure_connected()
    try:
        user = get_user_by_id(user_id)
        if not user:
            return None
        doc_count = get_document_count_by_department(user['department'])
        message_count = _db.chat_messages.count_documents({'user_id': user_id})
        return {
            'user': {'id': user['id'], 'username': user['username'], 'department': user['department']},
            'document_count': doc_count,
            'message_count': message_count
        }
    except Exception as e:
        logger.error(f"Error getting user statistics for {user_id}: {str(e)}")
        return None

def check_database_connection() -> bool:
    _ensure_connected()
    try:
        _db.command('ping')
        return True
    except Exception as e:
        logger.error(f"MongoDB connection failed: {str(e)}")
        return False

# OTP helpers for higher authority
def create_or_replace_otp(username: str, code: str, ttl_seconds: int = 300) -> bool:
    _ensure_connected()
    try:
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        _db.otps.update_one({'username': username}, {'$set': {'code': code, 'expires_at': expires_at}}, upsert=True)
        return True
    except PyMongoError as e:
        logger.error(f"Error creating OTP for {username}: {str(e)}")
        return False

def verify_and_delete_otp(username: str, code: str) -> bool:
    _ensure_connected()
    try:
        doc = _db.otps.find_one({'username': username})
        if not doc:
            return False
        if doc.get('code') != code:
            return False
        if doc.get('expires_at') and doc['expires_at'] < datetime.utcnow():
            _db.otps.delete_one({'_id': doc['_id']})
            return False
        _db.otps.delete_one({'_id': doc['_id']})
        return True
    except PyMongoError as e:
        logger.error(f"Error verifying OTP for {username}: {str(e)}")
        return False