#!/usr/bin/env python3
"""
Startup script for Oman Central Bank Document Analyzer
This script helps initialize the application and provides helpful information.
"""

import os
import sys
import subprocess

def check_requirements():
    """Check if all required packages are installed"""
    try:
        import flask
        import psycopg2
        import bcrypt
        import PyPDF2
        import docx
        import pytesseract
        import requests
        print("✓ All required packages are installed")
        return True
    except ImportError as e:
        print(f"✗ Missing package: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def check_environment():
    """Check if environment variables are set"""
    required_vars = ['MONGO_URI', 'FLASK_SECRET_KEY']
    optional_vars = ['GEMINI_API_KEY']
    
    print("\nChecking environment variables...")
    
    missing_required = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_required.append(var)
    
    if missing_required:
        print(f"✗ Missing required environment variables: {', '.join(missing_required)}")
        print("Please set these variables or create a .env file")
        return False
    
    print("✓ Required environment variables are set")
    
    if not os.environ.get('GEMINI_API_KEY'):
        print("⚠ GEMINI_API_KEY not set - AI features will be limited")
    else:
        print("✓ GEMINI_API_KEY is set - AI features available")
    
    return True

def check_postgresql():
    """Check if PostgreSQL is accessible"""
    try:
        import psycopg2
        postgres_uri = os.environ.get('POSTGRES_URI', 'postgresql://postgres:1234@localhost:5432/doc_analyzer')
        conn = psycopg2.connect(postgres_uri)
        cursor = conn.cursor()
        cursor.execute('SELECT version()')
        version = cursor.fetchone()
        cursor.close()
        conn.close()
        print("✓ PostgreSQL connection successful")
        return True
    except Exception as e:
        print(f"✗ PostgreSQL connection failed: {e}")
        print("Please ensure PostgreSQL is running and accessible")
        return False

def main():
    """Main startup function"""
    print("=" * 60)
    print("Oman Central Bank - Document Analyzer")
    print("Startup Check")
    print("=" * 60)
    
    # Check requirements
    if not check_requirements():
        return 1
    
    # Check environment
    if not check_environment():
        return 1
    
    # Check PostgreSQL
    if not check_postgresql():
        return 1
    
    print("\n" + "=" * 60)
    print("✓ All checks passed! Starting application...")
    print("=" * 60)
    
    # Start the Flask application
    try:
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"✗ Failed to start application: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
