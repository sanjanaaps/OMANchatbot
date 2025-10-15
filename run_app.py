#!/usr/bin/env python3
"""
Simple script to run the Flask application
"""

import os
import sys

def _startup_device_check() -> None:
    try:
        import torch  # type: ignore
        has_cuda = bool(getattr(torch, "cuda", None) and torch.cuda.is_available())
    except Exception:
        has_cuda = False

    whisper_device = 'cuda' if has_cuda else 'cpu'
    whisper_model = 'small' if has_cuda else 'base'
    rag_enabled = '1' if has_cuda else '0'

    os.environ['WHISPER_DEVICE'] = whisper_device
    os.environ['WHISPER_MODEL'] = whisper_model
    os.environ['RAG_ENABLED'] = rag_enabled

    print(f"[Startup] device={whisper_device}, rag={'on' if rag_enabled=='1' else 'off'}, whisper={whisper_model}")

# Set environment variables
os.environ['POSTGRES_URI'] = 'postgresql://postgres:1234@localhost:5432/doc_analyzer'
os.environ['FLASK_SECRET_KEY'] = 'dev-secret-key-change-in-production'
os.environ['DB_NAME'] = 'doc_analyzer'
os.environ['GEMINI_API_KEY'] = 'AIzaSyBX5T_0LqeeVa6Bu5y7MOAHSKngF547920' 

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Starting Oman Central Bank Document Analyzer...")
print("Environment variables set:")
print(f"  MONGO_URI: {os.environ.get('MONGO_URI')}")
print(f"  FLASK_SECRET_KEY: {os.environ.get('FLASK_SECRET_KEY')}")
print(f"  DB_NAME: {os.environ.get('DB_NAME')}")

_startup_device_check()

try:
    from app import app
    print("✓ App imported successfully")
    try:
        app.RAG_ENABLED = os.environ.get('RAG_ENABLED', '0') == '1'  # type: ignore[attr-defined]
    except Exception:
        pass
    print("🚀 Starting Flask server...")
    print("📱 Application will be available at: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
