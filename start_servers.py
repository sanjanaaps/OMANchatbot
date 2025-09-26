#!/usr/bin/env python3
"""
Startup script to run both Flask backend and Node.js API server
"""

import subprocess
import sys
import time
import os
import signal
from threading import Thread

def run_flask_server():
    """Run the Flask backend server"""
    print("🚀 Starting Flask backend server...")
    try:
        subprocess.run([sys.executable, "run_app.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Flask server failed: {e}")
    except KeyboardInterrupt:
        print("🛑 Flask server stopped")

def run_node_server():
    """Run the Node.js API server"""
    print("🚀 Starting Node.js API server...")
    try:
        # Check if node_modules exists, if not install dependencies
        if not os.path.exists("node_modules"):
            print("📦 Installing Node.js dependencies...")
            subprocess.run(["npm", "install"], check=True)
        
        subprocess.run(["node", "server.js"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Node.js server failed: {e}")
    except KeyboardInterrupt:
        print("🛑 Node.js server stopped")

def run_react_frontend():
    """Run the React frontend development server"""
    print("🚀 Starting React frontend server...")
    try:
        # Check if frontend node_modules exists, if not install dependencies
        if not os.path.exists("frontend/node_modules"):
            print("📦 Installing React dependencies...")
            subprocess.run(["npm", "install"], cwd="frontend", check=True)
        
        subprocess.run(["npm", "start"], cwd="frontend", check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ React frontend failed: {e}")
    except KeyboardInterrupt:
        print("🛑 React frontend stopped")

def main():
    """Main function to start all servers"""
    print("🎯 Starting Central Bank of Oman Chatbot System")
    print("=" * 60)
    
    # Start Flask backend in a separate thread
    flask_thread = Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    
    # Wait a bit for Flask to start
    time.sleep(3)
    
    # Start Node.js API server in a separate thread
    node_thread = Thread(target=run_node_server, daemon=True)
    node_thread.start()
    
    # Wait a bit for Node.js to start
    time.sleep(3)
    
    # Start React frontend in a separate thread
    react_thread = Thread(target=run_react_frontend, daemon=True)
    react_thread.start()
    
    print("\n✅ All servers started!")
    print("📱 Frontend: http://localhost:3000")
    print("🔌 API Server: http://localhost:3001")
    print("🐍 Flask Backend: http://localhost:5000")
    print("\nPress Ctrl+C to stop all servers")
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down all servers...")
        sys.exit(0)

if __name__ == "__main__":
    main()
