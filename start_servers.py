#!/usr/bin/env python3
"""
Start both Apache and Flask servers
"""

import subprocess
import sys
import os
import time
import threading
from pathlib import Path

def start_flask():
    """Start Flask application in a separate thread"""
    print("🐍 Starting Flask application...")
    os.chdir(Path(__file__).parent)
    
    try:
        # Start Flask app
        subprocess.run([sys.executable, "app.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Flask application failed to start: {e}")
    except KeyboardInterrupt:
        print("🛑 Flask application stopped")

def start_apache():
    """Start Apache server"""
    print("🚀 Starting Apache server...")
    
    try:
        # Try to start Apache service
        subprocess.run(["net", "start", "Apache2.4"], check=True)
        print("✅ Apache started successfully!")
    except subprocess.CalledProcessError:
        try:
            # Try alternative method
            subprocess.run(["httpd", "-k", "start"], check=True)
            print("✅ Apache started successfully!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to start Apache: {e}")
            print("Please make sure Apache is installed and configured")

def main():
    print("🎯 Starting CBO Flask Application with Apache")
    print("=" * 50)
    
    # Start Apache
    start_apache()
    
    # Wait a moment for Apache to start
    time.sleep(2)
    
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    
    print("\n✅ Servers started!")
    print("🌐 Your application should now be available at:")
    print("   http://localhost")
    print("   http://localhost:80")
    print("\n📝 Press Ctrl+C to stop all servers")
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping servers...")
        
        # Stop Apache
        try:
            subprocess.run(["net", "stop", "Apache2.4"], check=True)
            print("✅ Apache stopped")
        except subprocess.CalledProcessError:
            try:
                subprocess.run(["httpd", "-k", "stop"], check=True)
                print("✅ Apache stopped")
            except subprocess.CalledProcessError:
                print("❌ Failed to stop Apache")
        
        print("👋 Goodbye!")

if __name__ == "__main__":
    main()