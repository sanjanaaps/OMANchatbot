#!/usr/bin/env python3
"""
Simple script to run the Flask application
"""

import os
import sys

# Set environment variables
os.environ['POSTGRES_URI'] = 'postgresql://postgres:1234@localhost:5432/doc_analyzer'
os.environ['FLASK_SECRET_KEY'] = 'dev-secret-key-change-in-production'
os.environ['DB_NAME'] = 'doc_analyzer'
os.environ['GEMINI_API_KEY'] = '' # Set your actual Gemini API key here

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Starting Oman Central Bank Document Analyzer...")
print("Environment variables set:")
print(f"  MONGO_URI: {os.environ.get('MONGO_URI')}")
print(f"  FLASK_SECRET_KEY: {os.environ.get('FLASK_SECRET_KEY')}")
print(f"  DB_NAME: {os.environ.get('DB_NAME')}")

try:
    from app import app
    print("✓ App imported successfully")
    print("🚀 Starting Flask server...")
    print("📱 Application will be available at: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
