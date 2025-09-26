#!/usr/bin/env python3
"""
Demo script showing the configuration system
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def demo_configuration():
    """Demonstrate the configuration system"""
    print("\n🎯 Oman Central Bank Document Analyzer - Configuration Demo")
    print("="*70)
    
    # Import configuration module
    from startup_config import configure_rag_choice, check_rag_dependencies
    
    print("\n📋 This demo shows how the configuration system works:")
    print("1. Asks user if they want to enable RAG")
    print("2. Checks for required dependencies")
    print("3. Offers to install missing dependencies")
    print("4. Sets up the app accordingly")
    
    print("\n🔧 Current dependency status:")
    rag_deps_available = check_rag_dependencies()
    print(f"   RAG dependencies available: {'✅ Yes' if rag_deps_available else '❌ No'}")
    
    print("\n💡 To run with configuration prompt:")
    print("   python run_with_config.py")
    
    print("\n💡 To run without RAG (direct start):")
    print("   python app.py")
    
    print("\n💡 To install RAG dependencies:")
    print("   pip install -r requirements_rag.txt")
    
    print("\n" + "="*70)
    print("🎉 Configuration system ready!")
    print("="*70)

if __name__ == "__main__":
    demo_configuration()
