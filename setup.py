#!/usr/bin/env python3
"""
Quick setup script for Oman Central Bank Document Analyzer
This script helps you get started quickly with the application.
"""

import os
import sys
import subprocess

def set_environment_variables():
    """Set environment variables for the application"""
    print("Setting up environment variables...")
    
    # Set PostgreSQL URI
    os.environ['POSTGRES_URI'] = 'postgresql://postgres:1234@localhost:5432/doc_analyzer'
    print("✓ POSTGRES_URI set to: postgresql://postgres:1234@localhost:5432/doc_analyzer")
    
    # Set Flask secret key
    os.environ['FLASK_SECRET_KEY'] = 'dev-secret-key-change-in-production'
    print("✓ FLASK_SECRET_KEY set (development mode)")
    
    # Check for Gemini API key
    gemini_key = os.environ.get('GEMINI_API_KEY')
    if gemini_key:
        print("✓ GEMINI_API_KEY found")
    else:
        print("⚠ GEMINI_API_KEY not set - AI features will be limited")
        print("  To enable AI features, set: export GEMINI_API_KEY='your-key-here'")
    
    # Set database name
    os.environ['DB_NAME'] = 'doc_analyzer'
    print("✓ DB_NAME set to: doc_analyzer")

def check_dependencies():
    """Check if required packages are installed"""
    print("\nChecking dependencies...")
    
    required_packages = [
        'flask', 'psycopg2-binary', 'SQLAlchemy', 'Flask-SQLAlchemy', 'bcrypt', 'PyPDF2', 
        'python-docx', 'pytesseract', 'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - Missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Please run: pip install -r requirements.txt")
        return False
    
    return True

def initialize_database():
    """Initialize the database with test users"""
    print("\nInitializing database...")
    
    try:
        from lib.db import init_db, seed_users
        
        # Initialize database
        init_db()
        print("✓ Database initialized")
        
        # Seed users
        if seed_users():
            print("✓ Test users created")
            return True
        else:
            print("✗ Failed to create test users")
            return False
            
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        print("Make sure PostgreSQL is running and database 'doc_analyzer' exists")
        return False

def main():
    """Main setup function"""
    print("=" * 60)
    print("Oman Central Bank - Document Analyzer Setup")
    print("=" * 60)
    
    # Set environment variables
    set_environment_variables()
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Setup failed: Missing dependencies")
        return 1
    
    # Initialize database
    if not initialize_database():
        print("\n❌ Setup failed: Database initialization error")
        return 1
    
    print("\n" + "=" * 60)
    print("✅ Setup completed successfully!")
    print("=" * 60)
    print("\nYou can now start the application with:")
    print("  python app.py")
    print("\nTest user credentials:")
    print("  Username: finance_user, Password: finance123")
    print("  Username: policy_user, Password: policy123")
    print("  Username: currency_user, Password: currency123")
    print("  Username: legal_user, Password: legal123")
    print("  Username: itfinance_user, Password: itfinance123")
    print("\nThe application will be available at: http://localhost:5000")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
