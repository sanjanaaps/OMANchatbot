#!/usr/bin/env python3
"""
Simple run script for Oman Central Bank Document Analyzer
This script sets up the environment and starts the application.
"""

import os
import sys

def _startup_device_check() -> None:
    """Detect processor and set startup flags for RAG and Whisper.

    - RAG_ENABLED: on only if CUDA GPU is available
    - WHISPER_DEVICE: 'cuda' or 'cpu'
    - WHISPER_MODEL: pick a sensible default per device
    """
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

    # Concise one-liner
    print(f"[Startup] device={whisper_device}, rag={'on' if rag_enabled=='1' else 'off'}, whisper={whisper_model}")

def main():
    """Main function to run the application"""
    print("=" * 60)
    print("Oman Central Bank - Document Analyzer")
    print("Starting Application...")
    print("=" * 60)
    
    # Set environment variables
    os.environ['POSTGRES_URI'] = 'postgresql://postgres:1234@localhost:5432/doc_analyzer'
    os.environ['FLASK_SECRET_KEY'] = 'dev-secret-key-change-in-production'
    os.environ['DB_NAME'] = 'doc_analyzer'
    
    # Add current directory to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Startup device gating (sets env for downstream services)
    _startup_device_check()

    # Check for Gemini API key
    if not os.environ.get('GEMINI_API_KEY'):
        print("⚠ GEMINI_API_KEY not set - AI features will be limited")
        print("  To enable AI features, set: export GEMINI_API_KEY='your-key-here'")
    
    print("✓ Environment variables set")
    print("✓ PostgreSQL URI: postgresql://postgres:1234@localhost:5432/doc_analyzer")
    print("✓ Database: doc_analyzer")
    
    try:
        # Import and run the app
        from app import app
        # Propagate RAG flag into app if supported
        try:
            app.RAG_ENABLED = os.environ.get('RAG_ENABLED', '0') == '1'  # type: ignore[attr-defined]
        except Exception:
            pass
        print("\n🚀 Starting Flask application...")
        print("📱 Application will be available at: http://localhost:5000")
        print("\nTest user credentials:")
        print("  Username: finance_user, Password: finance123")
        print("  Username: policy_user, Password: policy123")
        print("  Username: currency_user, Password: currency123")
        print("  Username: legal_user, Password: legal123")
        print("  Username: itfinance_user, Password: itfinance123")
        print("\nPress Ctrl+C to stop the application")
        print("=" * 60)
        
        app.run(debug=True, host='0.0.0.0', port=5000)
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please make sure all dependencies are installed:")
        print("  pip install -r requirements.txt")
        return 1
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
