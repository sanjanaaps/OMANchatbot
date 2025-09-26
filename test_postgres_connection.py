#!/usr/bin/env python3
"""
Test script to verify PostgreSQL connection and basic functionality
"""

import os
import sys
from sqlalchemy import text

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variables
os.environ['POSTGRES_URI'] = 'postgresql://postgres:1234@localhost:5432/doc_analyzer'

def test_postgres_connection():
    """Test basic PostgreSQL connection"""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='1234',
            database='doc_analyzer'
        )
        
        cursor = conn.cursor()
        cursor.execute('SELECT version()')
        version = cursor.fetchone()
        print(f"✓ PostgreSQL connection successful")
        print(f"  Version: {version[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ PostgreSQL connection failed: {str(e)}")
        return False

def test_sqlalchemy_models():
    """Test SQLAlchemy models and database operations with checks"""
    try:
        from flask import Flask
        from config import get_config
        from app_lib.db import init_db, seed_users, get_user_by_username
        from app_lib.models import db, User, Document, ChatMessage
        from app_lib.auth import hash_password

        # Create Flask app
        app = Flask(__name__)
        config_class = get_config()
        app.config.from_object(config_class)

        with app.app_context():
            # Step 1: Initialize database
            try:
                init_db(app)
                print("✓ SQLAlchemy database initialization successful")
            except Exception as e:
                print(f"✗ Database initialization failed: {e}")
                return False

            # Step 2: Test user creation
            try:
                test_user = User(
                    username='test_user',
                    password_hash=hash_password('test123'),
                    department='Test Department'
                )
                db.session.add(test_user)
                db.session.commit()

                # Verify insertion
                created_user = User.query.filter_by(username='test_user').first()
                assert created_user is not None, "User not found after creation"
                assert created_user.department == 'Test Department', "Department mismatch"
                print("✓ User creation and verification successful")
            except Exception as e:
                print(f"✗ User creation failed: {e}")
                db.session.rollback()
                return False

            # Step 3: Test user retrieval via helper function
            try:
                user = get_user_by_username('test_user')
                assert user is not None, "get_user_by_username returned None"
                assert user.username == 'test_user', "Retrieved username mismatch"
                print("✓ User retrieval successful")
            except Exception as e:
                print(f"✗ User retrieval failed: {e}")
                return False

            # Step 4: Test document creation
            try:
                test_doc = Document(
                    filename='test_document.pdf',
                    department='Test Department',
                    uploaded_by='test_user',
                    content='This is a test document content for testing purposes.',
                    file_type='pdf'
                )
                db.session.add(test_doc)
                db.session.commit()

                # Verify insertion
                created_doc = Document.query.filter_by(filename='test_document.pdf').first()
                assert created_doc is not None, "Document not found after creation"
                assert created_doc.uploaded_by == 'test_user', "Uploaded_by mismatch"
                print("✓ Document creation and verification successful")
            except Exception as e:
                print(f"✗ Document creation failed: {e}")
                db.session.rollback()
                return False

            # Step 5: Test document retrieval
            try:
                docs = Document.query.filter_by(department='Test Department').all()
                assert len(docs) > 0, "No documents found in test department"
                print("✓ Document retrieval successful")
            except Exception as e:
                print(f"✗ Document retrieval failed: {e}")
                return False

            # Step 6: Clean up test data
            try:
                db.session.delete(test_doc)
                db.session.delete(test_user)
                db.session.commit()

                # Confirm deletion
                assert User.query.filter_by(username='test_user').first() is None, "User not deleted"
                assert Document.query.filter_by(filename='test_document.pdf').first() is None, "Document not deleted"
                print("✓ Test data cleanup successful")
            except Exception as e:
                print(f"✗ Test data cleanup failed: {e}")
                db.session.rollback()
                return False

        return True

    except Exception as outer_error:
        print(f"✗ Unexpected error during model testing: {outer_error}")
        return False


def test_flask_app_integration():
    """Test Flask app integration with PostgreSQL"""
    try:
        from app import app
        from app_lib.models import db
        from app_lib.models import User, Document  # import models explicitly

        with app.app_context():
            # Test database connection through Flask
            db.session.execute(text("SELECT 1"))
            print("✓ Flask app database integration successful")
            
            # Test if models are accessible
            user_count = db.session.query(User).count()
            doc_count = db.session.query(Document).count()
            print(f"✓ Model queries successful - Users: {user_count}, Documents: {doc_count}")
        
        return True
        
    except Exception as e:
        print(f"✗ Flask app integration test failed: {str(e)}")
        return False

def main():
    """Main test function"""
    print("=" * 60)
    print("PostgreSQL Migration Test Suite")
    print("=" * 60)
    
    tests = [
        ("PostgreSQL Connection", test_postgres_connection),
        ("SQLAlchemy Models", test_sqlalchemy_models),
        ("Flask App Integration", test_flask_app_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 40)
        if test_func():
            passed += 1
        else:
            print(f"✗ {test_name} failed")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("🎉 All tests passed! PostgreSQL migration is successful.")
        print("\nNext steps:")
        print("1. Run: python seed_users.py")
        print("2. Run: python app.py")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
