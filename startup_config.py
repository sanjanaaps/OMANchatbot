#!/usr/bin/env python3
"""
Startup Configuration Module
Handles console prompts for optional features like RAG
"""

import sys
import os

def get_user_choice(prompt_text: str, default: str = "no") -> bool:
    """
    Get user choice from console input
    
    Args:
        prompt_text: Text to display to user
        default: Default choice if user presses Enter
        
    Returns:
        True if user chooses 'yes', False otherwise
    """
    while True:
        try:
            choice = input(f"{prompt_text} (yes/no) [{default}]: ").strip().lower()
            
            if not choice:  # User pressed Enter
                choice = default
            
            if choice in ['yes', 'y']:
                return True
            elif choice in ['no', 'n']:
                return False
            else:
                print("Please enter 'yes' or 'no'")
                continue
                
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)
        except EOFError:
            print(f"\nUsing default choice: {default}")
            return default.lower() in ['yes', 'y']

def configure_rag_choice() -> bool:
    """
    Ask user if they want to enable Hallucination Fixed RAG functionality
    
    Returns:
        True if RAG should be enabled, False otherwise
    """
    print("\n" + "="*60)
    print("🤖 Hallucination Fixed RAG Configuration")
    print("="*60)
    print("RAG provides advanced document-based question answering with reduced hallucination.")
    print("⚠️  RAG requires GPU or significant CPU resources and additional packages.")
    print("📦 Required packages: langchain, transformers, torch, sentence-transformers, deep-translator")
    print("🔧 Uses Falcon-H1-1B-Base model with deterministic output to reduce hallucination")
    print("="*60)
    
    return get_user_choice(
        "Do you want to enable Hallucination Fixed RAG functionality?",
        default="no"
    )

def check_rag_dependencies() -> bool:
    """
    Check if Hallucination Fixed RAG dependencies are available
    
    Returns:
        True if dependencies are available, False otherwise
    """
    try:
        import langchain
        import transformers
        import torch
        import sentence_transformers
        import faiss
        import deep_translator
        import pdfplumber
        import pytesseract
        return True
    except ImportError:
        return False

def main():
    """Main configuration function"""
    print("\n🚀 Oman Central Bank Document Analyzer - Startup Configuration")
    print("="*70)
    
    # Configure RAG
    enable_rag = configure_rag_choice()
    
    if enable_rag:
        print("\n🔍 Checking RAG dependencies...")
        if check_rag_dependencies():
            print("✅ RAG dependencies found - RAG will be enabled")
            return True
        else:
            print("❌ Hallucination Fixed RAG dependencies not found")
            print("📦 To install RAG dependencies, run:")
            print("   pip install -r requirements_hallucination_fixed_rag.txt")
            
            install_choice = get_user_choice(
                "Do you want to install Hallucination Fixed RAG dependencies now?",
                default="no"
            )
            
            if install_choice:
                print("📦 Installing Hallucination Fixed RAG dependencies...")
                import subprocess
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements_hallucination_fixed_rag.txt"])
                    print("✅ Hallucination Fixed RAG dependencies installed successfully")
                    return True
                except subprocess.CalledProcessError:
                    print("❌ Failed to install Hallucination Fixed RAG dependencies")
                    print("⚠️  Continuing without RAG functionality")
                    return False
            else:
                print("⚠️  Continuing without RAG functionality")
                return False
    else:
        print("📝 RAG functionality disabled - app will run without RAG")
        return False

if __name__ == "__main__":
    rag_enabled = main()
    print(f"\n🎯 Configuration complete: RAG {'enabled' if rag_enabled else 'disabled'}")
    print("="*70)
