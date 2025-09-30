#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone Document Ingestion Script for GPU Processing
Run this script on a GPU-enabled machine to process documents for RAG Integration

This script processes all documents in the uploads folder and creates:
1. FAISS vector store with document embeddings
2. Processed document chunks with metadata
3. RAG system ready for queries

Usage:
    python ingest_documents_gpu.py --upload_folder ./uploads --verbose
    python ingest_documents_gpu.py --upload_folder ./uploads --force
"""

import os
import sys
import argparse
import logging
import time
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_gpu_availability():
    """Check if GPU is available for processing"""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0)
            print(f"✅ GPU detected: {gpu_name} (Count: {gpu_count})")
            return True
        else:
            print("⚠️ No GPU detected. RAG model will use CPU.")
            print("   Document processing will still work, but may be slower.")
            return False
    except ImportError:
        print("❌ PyTorch not installed. Please install torch first.")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Ingest documents for Oman Central Bank RAG Integration system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with uploads folder
  python ingest_documents_gpu.py --upload_folder ./uploads

  # With verbose logging
  python ingest_documents_gpu.py --upload_folder ./uploads --verbose

  # Force re-processing
  python ingest_documents_gpu.py --upload_folder ./uploads --force

  # Process specific folder
  python ingest_documents_gpu.py --upload_folder /path/to/documents --verbose
        """
    )
    
    parser.add_argument('--upload_folder', required=True, 
                       help='Path to upload folder containing documents (PDF, TXT, MD files)')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Enable verbose logging')
    parser.add_argument('--force', '-f', action='store_true',
                       help='Force re-processing even if vector store exists')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("="*60)
    print("🚀 Oman Central Bank - RAG Integration Ingestion")
    print("="*60)
    
    # Check GPU availability
    gpu_available = check_gpu_availability()
    
    # Validate upload folder
    upload_folder = Path(args.upload_folder)
    if not upload_folder.exists():
        print(f"❌ Error: Upload folder {upload_folder} does not exist")
        sys.exit(1)
    
    if not upload_folder.is_dir():
        print(f"❌ Error: {upload_folder} is not a directory")
        sys.exit(1)
    
    # Check for documents
    supported_extensions = {'.pdf', '.txt', '.md'}
    documents = []
    for ext in supported_extensions:
        documents.extend(upload_folder.glob(f'*{ext}'))
    
    if not documents:
        print(f"❌ No supported documents found in {upload_folder}")
        print(f"   Supported formats: {', '.join(supported_extensions)}")
        sys.exit(1)
    
    print(f"📁 Found {len(documents)} documents to process:")
    for doc in documents[:5]:  # Show first 5
        print(f"   - {doc.name}")
    if len(documents) > 5:
        print(f"   ... and {len(documents) - 5} more")
    
    # Check if vector store already exists (look for common vector store files)
    vector_store_files = list(upload_folder.glob("*.pkl")) + list(upload_folder.glob("*.faiss"))
    if vector_store_files and not args.force:
        print(f"⚠️ Vector store files already exist: {[f.name for f in vector_store_files]}")
        print("   Use --force to re-process documents")
        sys.exit(0)
    
    try:
        # Import and initialize RAG system
        print("\n🔧 Initializing RAG Integration system...")
        from app_lib.rag_integration import initialize_rag_system
        
        start_time = time.time()
        rag = initialize_rag_system(str(upload_folder))
        
        if not rag:
            print("❌ Failed to initialize RAG system")
            sys.exit(1)
        
        print("📚 Ingesting documents...")
        success = rag.ingest_documents_from_folder(str(upload_folder))
        
        if success:
            ingestion_time = time.time() - start_time
            print(f"✅ Document ingestion completed successfully in {ingestion_time:.2f} seconds")
            
            # Show stats
            stats = rag.get_stats()
            print(f"\n📊 Processing Statistics:")
            print(f"   - Documents indexed: {stats.get('document_count', 0)}")
            print(f"   - System initialized: {stats.get('initialized', False)}")
            print(f"   - Embeddings ready: {stats.get('embeddings_ready', False)}")
            print(f"   - LLM ready: {stats.get('llm_ready', False)}")
            print(f"   - QA chain ready: {stats.get('qa_chain_ready', False)}")
            print(f"   - Processing time: {ingestion_time:.2f} seconds")
            
            # Test the system
            print(f"\n🧪 Testing RAG system...")
            try:
                test_response, _ = rag.query("What is the Central Bank of Oman?", 'en')
                if test_response and not test_response.startswith("RAG system not"):
                    print("✅ RAG system test successful")
                    print(f"   Sample response: {test_response[:100]}...")
                else:
                    print("⚠️ RAG system test failed - will use Gemini fallback")
            except Exception as e:
                print(f"⚠️ RAG system test error: {str(e)}")
            
            # Show final status
            if not gpu_available:
                print(f"\n💡 Note: No GPU detected - RAG model will use CPU")
                print(f"   Processing may be slower but will still work")
                print(f"   Document processing and vector search work normally")
            
            print(f"\n🎉 Ingestion completed successfully!")
            print(f"   You can now use the RAG system in your application.")
            print(f"   Vector store created in: {upload_folder}")
            
        else:
            print("❌ Document ingestion failed")
            sys.exit(1)
            
    except ImportError as e:
        print(f"❌ Import error: {str(e)}")
        print("   Please install required dependencies:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

