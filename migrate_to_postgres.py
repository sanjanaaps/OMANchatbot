#!/usr/bin/env python3
"""
Database migration script to set up PostgreSQL database for the Document Analyzer application.

This script creates the database and tables needed for the application.
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variables
os.environ['POSTGRES_URI'] = 'postgresql://postgres:1234@localhost:5432/doc_analyzer'

def create_database():
    """Create the database if it doesn't exist"""
    try:
        # Connect to PostgreSQL server (without specific database)
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='1234',
            database='postgres'  # Connect to default postgres database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = 'doc_analyzer'")
        exists = cursor.fetchone()
        
        if not exists:
            # Create database
            cursor.execute('CREATE DATABASE doc_analyzer')
            print("✓ Database 'doc_analyzer' created successfully")
        else:
            print("✓ Database 'doc_analyzer' already exists")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error creating database: {str(e)}")
        return False

def create_tables():
    """Create tables using Flask-SQLAlchemy"""
    try:
        from flask import Flask
        from config import get_config
        from app_lib.db import init_db
        
        # Create Flask app
        app = Flask(__name__)
        config_class = get_config()
        app.config.from_object(config_class)
        
        # Initialize database and create tables
        with app.app_context():
            init_db(app)
            print("✓ Database tables created successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Error creating tables: {str(e)}")
        return False

def test_connection():
    """Test database connection"""
    try:
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
        print(f"✗ Database connection failed: {str(e)}")
        return False

def main():
    """Main migration function"""
    print("=" * 60)
    print("Document Analyzer - PostgreSQL Migration Script")
    print("=" * 60)
    
    print("\n1. Testing PostgreSQL connection...")
    if not test_connection():
        print("\nPlease ensure:")
        print("- PostgreSQL is installed and running")
        print("- User 'postgres' exists with password '1234'")
        print("- PostgreSQL is listening on localhost:5432")
        return 1
    
    print("\n2. Creating database...")
    if not create_database():
        return 1
    
    print("\n3. Creating tables...")
    if not create_tables():
        return 1
    
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run the seed script to create test users:")
    print("   python seed_users.py")
    print("2. Start the Flask application:")
    print("   python app.py")
    print("\nDatabase configuration:")
    print("   Host: localhost")
    print("   Port: 5432")
    print("   Database: doc_analyzer")
    print("   User: postgres")
    print("   Password: 1234")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

