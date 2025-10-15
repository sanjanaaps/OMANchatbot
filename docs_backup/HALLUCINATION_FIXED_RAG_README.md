# Hallucination Fixed RAG System

This document explains how to use the new Hallucination Fixed RAG system for the Oman Central Bank Document Analyzer.

## Overview

The Hallucination Fixed RAG system is based on the `hallucination_fixed.py` implementation and provides:

- **Reduced Hallucination**: Uses deterministic output with the Falcon-H1-1B-Base model
- **Multilingual Support**: Automatic translation between English and Arabic
- **Document Processing**: Supports PDF, TXT, and MD files with OCR capabilities
- **Department Tagging**: Automatically categorizes documents by department
- **Fallback to Gemini**: Falls back to Gemini API when RAG system is unavailable

## Features

### 1. Document Processing
- **PDF Processing**: Extracts text using pdfplumber
- **Image OCR**: Uses Tesseract for Arabic and English text extraction
- **Text Files**: Supports TXT and MD files
- **Translation**: Automatic translation to English for processing

### 2. RAG System
- **Model**: Falcon-H1-1B-Base with deterministic output
- **Embeddings**: Multilingual sentence transformers
- **Vector Store**: FAISS for efficient similarity search
- **Chunking**: 800-character chunks with 100-character overlap

### 3. Department Tagging
Automatically tags documents based on keywords:
- **Finance**: budget, revenue, expense, finance, financial, monetary, banking
- **Currency**: banknotes, coins, mint, currency, rial, exchange, foreign exchange
- **IT**: network, software, hardware, technology, it, digital, cyber
- **Legal**: regulation, law, compliance, legal, policy, governance
- **Policy**: policy, regulation, framework, guidelines, standards
- **Operations**: operations, process, procedure, workflow, management

## Installation

### 1. Install Dependencies
```bash
pip install -r requirements_hallucination_fixed_rag.txt
```

### 2. Enable RAG System
Run the startup configuration:
```bash
python startup_config.py
```
Choose "yes" when prompted to enable Hallucination Fixed RAG functionality.

## Usage

### 1. Automatic Integration
The RAG system is automatically integrated into the Flask application. When enabled:
- Documents uploaded through the web interface are automatically processed
- Chat queries use the RAG system with fallback to Gemini
- FAQ documents are automatically ingested

### 2. Standalone GPU Processing
For GPU-accelerated document processing, use the standalone script:

```bash
python ingest_documents_gpu.py --upload_folder /path/to/upload/folder --verbose
```

Options:
- `--upload_folder`: Path to folder containing documents
- `--weights_path`: Optional path to save model weights
- `--verbose`: Enable verbose logging

### 3. Manual RAG Queries
```python
from app_lib.hallucination_fixed_rag import HallucinationFixedRAG

# Initialize RAG system
rag = HallucinationFixedRAG("/path/to/upload/folder")
rag.ingest_documents("/path/to/upload/folder")

# Query the system
answer_ar, answer_en = rag.query("What is the banking regulation framework?", language='ar')
print(f"Arabic: {answer_ar}")
print(f"English: {answer_en}")
```

## Configuration

### 1. Model Configuration
The system uses the Falcon-H1-1B-Base model with:
- **Device**: Auto (GPU if available, CPU otherwise)
- **Precision**: bfloat16 for efficiency
- **Max Tokens**: 512
- **Sampling**: Deterministic (do_sample=False)

### 2. Document Processing
- **Chunk Size**: 800 characters
- **Chunk Overlap**: 100 characters
- **Translation Chunk Size**: 4000 characters
- **OCR Languages**: English + Arabic

### 3. Weights Management
- **Save Weights**: Automatically saves model weights after processing
- **Load Weights**: Can load pre-trained weights for faster startup
- **Default Path**: `falcon_h1_weights.pth` in upload folder

## FAQ Integration

The system automatically processes FAQ documents:
- **banking_knowledge.txt**: Banking knowledge base
- **cbo_faq_mapping.md**: FAQ mappings

These are processed as Q&A format and integrated into the vector store.

## Fallback System

When the RAG system is unavailable:
1. **Primary Fallback**: Gemini API with department-specific prompts
2. **Secondary Fallback**: Local document search
3. **Final Fallback**: Generic department-specific responses

## Performance Considerations

### GPU Requirements
- **Recommended**: NVIDIA GPU with 8GB+ VRAM
- **Minimum**: CPU with 16GB+ RAM
- **Model Size**: ~2GB for Falcon-H1-1B-Base

### Processing Time
- **GPU**: ~2-5 seconds per document
- **CPU**: ~30-60 seconds per document
- **Translation**: ~1-2 seconds per 4000 characters

## Troubleshooting

### Common Issues

1. **CUDA Out of Memory**
   - Reduce batch size or use CPU
   - Use smaller model or quantization

2. **Translation Errors**
   - Check internet connection
   - Verify deep-translator installation

3. **OCR Issues**
   - Install Tesseract system package
   - Verify language packs (eng+ara)

4. **Model Loading Errors**
   - Check internet connection for model download
   - Verify transformers and torch versions

### Debug Mode
Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

## API Integration

The RAG system integrates with the existing Flask API:

### Endpoints
- `POST /rag/init`: Initialize RAG system
- `POST /rag/ingest`: Ingest documents
- `GET /rag/status`: Get RAG system status

### Chat Integration
The chat endpoint automatically uses RAG when available:
```python
# In chat route
if rag_system and rag_system.is_ready():
    response, response_en = query_rag(message, language)
```

## Security Considerations

- **Model Weights**: Stored locally, not transmitted
- **Document Processing**: All processing happens locally
- **Translation**: Uses Google Translate API (internet required)
- **Fallback**: Secure fallback to Gemini API

## Future Enhancements

- [ ] Support for more document formats
- [ ] Custom model fine-tuning
- [ ] Batch processing optimization
- [ ] Multi-GPU support
- [ ] Model quantization for smaller deployments

