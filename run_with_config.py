#!/usr/bin/env python3
"""
Main startup script with configuration prompt
Handles RAG enable/disable choice before starting the app
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Main startup function"""
    print("\n🚀 Oman Central Bank Document Analyzer - Startup")
    print("="*60)
    
    # Import and run startup configuration
    try:
        from startup_config import configure_rag_choice, check_rag_dependencies
        
        # Get user choice for RAG
        enable_rag = configure_rag_choice()
        
        if enable_rag:
            print("\n🔍 Checking RAG dependencies...")
            if check_rag_dependencies():
                print("✅ RAG dependencies found - RAG will be enabled")
            else:
                print("❌ RAG dependencies not found")
                print("📦 To install RAG dependencies, run:")
                print("   pip install -r requirements_rag.txt")
                
                install_choice = input("Do you want to install RAG dependencies now? (yes/no) [no]: ").strip().lower()
                
                if install_choice in ['yes', 'y']:
                    print("📦 Installing RAG dependencies...")
                    import subprocess
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements_rag.txt"])
                        print("✅ RAG dependencies installed successfully")
                    except subprocess.CalledProcessError:
                        print("❌ Failed to install RAG dependencies")
                        print("⚠️  Continuing without RAG functionality")
                        enable_rag = False
                else:
                    print("⚠️  Continuing without RAG functionality")
                    enable_rag = False
        else:
            print("📝 RAG functionality disabled - app will run without RAG")
        
        # Set the RAG_ENABLED flag in the app module
        import app
        app.RAG_ENABLED = enable_rag
        
        print(f"\n🎯 Configuration complete: RAG {'enabled' if enable_rag else 'disabled'}")
        print("="*60)
        
        # Start the Flask app
        print("\n🚀 Starting Flask application...")
        app.app.run(debug=True, host='0.0.0.0', port=5000)
        
    except KeyboardInterrupt:
        print("\n\n👋 Application stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error during startup: {str(e)}")
        print("💡 Try running the app directly: python app.py")
        sys.exit(1)

if __name__ == "__main__":
    main()
