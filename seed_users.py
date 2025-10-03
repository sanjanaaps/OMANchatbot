#!/usr/bin/env python3
"""
Seed script to populate the database with test users for the Oman Central Bank
Document Analyzer application.

This script creates 5 test users with different departments and bcrypt-hashed passwords.
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variables
os.environ['POSTGRES_URI'] = 'postgresql://postgres:1234@localhost:5432/doc_analyzer'

from app_lib.db import init_db, seed_users
from app_lib.auth import hash_password
from flask import Flask
from config import get_config

def main():
    """Main function to seed the database with test users"""
    print("=" * 60)
    print("Oman Central Bank - Document Analyzer")
    print("Database Seeding Script")
    print("=" * 60)
    
    try:
        # Create Flask app for database initialization
        app = Flask(__name__)
        config_class = get_config()
        app.config.from_object(config_class)
        
        # Initialize database and seed users inside app context
        with app.app_context():
            # Initialize database
            print("\n1. Initializing database...")
            init_db(app)
            print("   ✓ Database initialized successfully")

            # Seed users
            print("\n2. Seeding test users...")
            success = seed_users()
        
        if success:
            print("   ✓ Test users created successfully")
            print("\n" + "=" * 60)
            print("SEEDING COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print("\nYou can now start the Flask application with:")
            print("   python app.py")
            print("\nTest user credentials:")
            print("   Username: finance_user, Password: finance123")
            print("   Username: policy_user, Password: policy123")
            print("   Username: currency_user, Password: currency123")
            print("   Username: legal_user, Password: legal123")
            print("   Username: itfinance_user, Password: itfinance123")
            print("\nMake sure to set the following environment variables:")
            print("   - POSTGRES_URI (default: postgresql://postgres:1234@localhost:5432/doc_analyzer)")
            print("   - FLASK_SECRET_KEY (for production)")
            print("   - GEMINI_API_KEY (for AI features)")
        else:
            print("   ✗ Failed to seed users")
            return 1
            
    except Exception as e:
        print(f"\n✗ Error during seeding: {str(e)}")
        print("\nPlease check:")
        print("1. PostgreSQL is running")
        print("2. Database 'doc_analyzer' exists")
        print("3. Environment variables are set correctly")
        print("4. All required Python packages are installed")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
