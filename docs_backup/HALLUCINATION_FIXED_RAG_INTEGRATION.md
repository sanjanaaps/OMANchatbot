# Hallucination Fixed RAG Integration

This document describes the integration of the hallucination-fixed RAG (Retrieval-Augmented Generation) system into the Oman Central Bank Document Analyzer application.

## Overview

The hallucination-fixed RAG system replaces the previous RAG implementation with a more robust solution that:

1. **Reduces Hallucination**: Uses a specialized prompt template that strictly enforces using only provided context
2. **GPU Acceleration**: Leverages Falcon-H1-1B model with GPU support for faster processing
3. **Weights Persistence**: Saves and loads model weights for consistent performance
4. **Gemini Fallback**: Falls back to Gemini API when RAG system is unavailable
5. **Document Summarization**: Uses the RAG system for generating document summaries

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Document      │───▶│  Hallucination   │───▶│   Falcon-H1     │
│   Upload        │    │  Fixed RAG       │    │   Model         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   FAISS Vector   │
                       │   Store          │
                       └──────────────────┘
                                │
                                ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Query          │───▶│   Gemini        │
                       │   Processing     │    │   Fallback      │
                       └──────────────────┘    └─────────────────┘
```

## Key Components

### 1. HallucinationFixedRAG Class (`app_lib/hallucination_fixed_rag.py`)

The main RAG system class that handles:
- Document processing and chunking
- Vector store creation with FAISS
- Falcon model initialization and management
- Query processing with hallucination prevention
- Weights saving/loading

### 2. Prompt Template

The system uses a strict prompt template that prevents hallucination:

```
You are an assistant for the Oman Central Bank. You must follow these rules strictly:

RULES:
1. Use ONLY the information provided in the Context section below
2. If the exact answer is not found in the Context, respond with "I don't have that specific information available"
3. Do NOT add any information from your general knowledge
4. Do NOT make assumptions or inferences beyond what is explicitly stated
5. Quote directly from the context when possible

Context: {context}
Question: {question}

Instructions: Read the context carefully and provide an answer using ONLY the information above. If you cannot find the answer in the context, say "I don't have that specific information available."

Answer:
```

### 3. Document Processing Pipeline

1. **Text Extraction**: Supports PDF, TXT, and MD files
2. **Translation**: Translates Arabic content to English for processing
3. **Chunking**: Splits documents into 800-character chunks with 100-character overlap
4. **Embedding**: Uses multilingual sentence transformers for embeddings
5. **Indexing**: Creates FAISS vector store for efficient retrieval

### 4. Model Management

- **Falcon-H1-1B-Base**: Primary language model for generation
- **Weights Persistence**: Saves model weights to `falcon_h1_weights.pth`
- **GPU Support**: Automatically detects and uses GPU when available
- **Fallback**: Uses Gemini API when model is unavailable

## Installation and Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

The requirements include:
- `torch>=2.8.0` - PyTorch for model inference
- `transformers>=4.56.2` - Hugging Face transformers
- `langchain>=0.3.27` - LangChain for RAG pipeline
- `faiss-cpu>=1.12.0` - FAISS for vector search
- `accelerate>=0.20.0` - Model acceleration
- `bitsandbytes>=0.41.0` - Quantization support

### 2. GPU Setup (Optional but Recommended)

The system works in two modes:

**GPU Mode (Recommended):**
- Loads Falcon model for local inference
- Faster response times
- Reduced API costs

**CPU Mode (Fallback):**
- Skips Falcon model loading to avoid memory issues
- Uses Gemini API for all queries
- Still processes documents and creates vector store

```bash
# Check GPU availability
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

# If using CUDA, install CUDA-specific PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 3. Document Ingestion

Run the standalone GPU ingestion script to process documents:

```bash
# Basic usage
python ingest_documents_gpu.py --upload_folder ./uploads

# With verbose logging
python ingest_documents_gpu.py --upload_folder ./uploads --verbose

# Custom weights path
python ingest_documents_gpu.py --upload_folder ./uploads --weights_path ./custom_weights.pth

# Force re-processing
python ingest_documents_gpu.py --upload_folder ./uploads --force
```

## Usage

### 1. Application Integration

The RAG system is automatically integrated into the Flask application:

```python
# RAG is enabled by default
RAG_ENABLED = True

# Initialize on first request
if RAG_ENABLED and not RAG_AVAILABLE:
    initialize_rag_if_enabled()
```

### 2. Document Upload

When uploading documents, the system:
1. Extracts text from the document
2. Attempts to use RAG system for summarization
3. Falls back to structured analysis if RAG fails
4. Saves summaries in both English and Arabic

### 3. Chat Interface

The chat interface uses the following priority order:
1. **FAQ Service** - For CBO-specific questions
2. **RAG System** - For document-based questions
3. **Local Search** - For document search
4. **Gemini Fallback** - For general questions

### 4. API Endpoints

- `GET /rag/status` - Get RAG system status
- `POST /rag/init` - Manually initialize RAG system
- `POST /rag/ingest` - Manually ingest documents

## Configuration

### Environment Variables

```bash
# Optional: Custom model path
FALCON_MODEL_PATH=/path/to/custom/model

# Optional: Custom weights path
FALCON_WEIGHTS_PATH=/path/to/weights.pth

# Optional: GPU device
CUDA_VISIBLE_DEVICES=0
```

### Model Configuration

The system uses the following default configuration:

```python
MODEL_CONFIG = {
    "model_name": "tiiuae/Falcon-H1-1B-Base",
    "max_new_tokens": 512,
    "do_sample": False,  # Deterministic output
    "chunk_size": 800,
    "chunk_overlap": 100,
    "embedding_model": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
}
```

## Performance Optimization

### 1. GPU Utilization

- The system automatically detects and uses GPU when available
- Model weights are loaded once and reused for multiple queries
- Batch processing for document ingestion

### 2. Memory Management

- Documents are processed in chunks to manage memory usage
- Vector store is created incrementally
- Model weights are saved to disk to avoid re-downloading

### 3. Caching

- FAISS vector store is persisted and reused
- Model weights are cached locally
- Document embeddings are computed once and reused

## Troubleshooting

### Common Issues

1. **GPU Not Detected (Expected Behavior)**
   ```bash
   # Check CUDA installation
   nvidia-smi
   python -c "import torch; print(torch.cuda.is_available())"
   ```
   **Note:** If no GPU is detected, the system will automatically skip Falcon model loading and use Gemini fallback. This is normal behavior and the system will still work correctly.

2. **Model Download Fails**
   ```bash
   # Clear Hugging Face cache
   rm -rf ~/.cache/huggingface/
   # Or set custom cache directory
   export HF_HOME=/path/to/cache
   ```

3. **Memory Issues**
   ```bash
   # Reduce batch size or use CPU
   export CUDA_VISIBLE_DEVICES=""
   ```

4. **Weights File Issues**
   ```bash
   # Remove corrupted weights file
   rm uploads/falcon_h1_weights.pth
   # Re-run ingestion
   python ingest_documents_gpu.py --upload_folder ./uploads --force
   ```

### Debug Mode

Enable verbose logging for debugging:

```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Or use verbose flag
python ingest_documents_gpu.py --upload_folder ./uploads --verbose
```

## Monitoring and Maintenance

### 1. System Status

Check RAG system status via API:

```bash
curl http://localhost:5000/rag/status
```

### 2. Performance Metrics

Monitor the following metrics:
- Document ingestion time
- Query response time
- GPU utilization
- Memory usage
- Vector store size

### 3. Regular Maintenance

- **Weekly**: Check system status and performance
- **Monthly**: Update model weights if new documents are added
- **Quarterly**: Review and optimize prompt templates

## Security Considerations

1. **Model Weights**: Store weights securely and restrict access
2. **Document Content**: Ensure sensitive documents are properly secured
3. **API Access**: Implement proper authentication for RAG endpoints
4. **Data Privacy**: Consider data residency requirements for document processing

## Future Enhancements

1. **Model Updates**: Upgrade to newer Falcon models as they become available
2. **Multi-Modal Support**: Add support for image and table processing
3. **Fine-Tuning**: Implement domain-specific fine-tuning for CBO documents
4. **Distributed Processing**: Support for multi-GPU and distributed inference
5. **Advanced Caching**: Implement Redis-based caching for better performance

## Support

For issues or questions regarding the hallucination-fixed RAG system:

1. Check the troubleshooting section above
2. Review application logs for error messages
3. Test with the standalone ingestion script
4. Verify GPU and dependency installation

## License

This implementation follows the same license as the parent project and respects the licensing terms of the Falcon model and other dependencies.
