# RAG Integration for Oman Central Bank Chatbot

## Overview

The `OMANCBRAG` class from `rag_module_py.py` has been successfully integrated into the Flask application's chatbot functionality. This integration provides advanced document-based question answering using Retrieval-Augmented Generation (RAG) technology.

## Features

### 🔍 **Intelligent Document Processing**
- **Multi-format Support**: PDF, PNG, JPG, JPEG, TIFF files
- **OCR Capabilities**: Text extraction from images with English and Arabic support
- **Automatic Translation**: Content translation between English and Arabic
- **Department Tagging**: Automatic categorization based on content analysis

### 🤖 **Advanced RAG System**
- **Vector Search**: FAISS-based similarity search for relevant document chunks
- **Context-Aware Responses**: Uses document content to provide accurate answers
- **Multilingual Support**: Responses in both English and Arabic
- **Fallback System**: Graceful degradation when RAG is unavailable

### 🔄 **Seamless Integration**
- **Automatic Ingestion**: Documents are automatically added to RAG when uploaded
- **Priority System**: RAG responses take precedence over other methods
- **Real-time Updates**: New documents immediately available for querying
- **Status Monitoring**: API endpoints to check RAG system status

## Architecture

### Response Priority Order
1. **RAG System** - Document-based intelligent responses
2. **Local Search** - Existing document search functionality
3. **Gemini API** - External AI service
4. **Difflib Fallback** - Simple Q&A matching
5. **Hardcoded Responses** - Final fallback

### Components

#### `app_lib/rag_integration.py`
- **OmanCBRAG**: Main RAG system class
- **DocumentProcessor**: Handles file processing and translation
- **DepartmentTagger**: Categorizes documents by department
- **Global Functions**: Easy integration with Flask app

#### Modified `app.py`
- **RAG Initialization**: System startup with RAG components
- **Enhanced Chat Route**: Integrated RAG querying
- **Document Upload**: Automatic RAG ingestion
- **API Endpoints**: Status and manual ingestion routes

## Installation

### Prerequisites
The RAG system requires additional dependencies not included in the base Flask application:

```bash
pip install -r requirements_rag.txt
```

### Required Packages
- **LangChain**: Framework for RAG applications
- **PyTorch**: Machine learning backend
- **Transformers**: Hugging Face model library
- **FAISS**: Vector similarity search
- **PDF Processing**: pdfplumber, pytesseract
- **Translation**: deep-translator

## Usage

### Automatic Integration
The RAG system is automatically integrated into the existing chat functionality:

1. **Upload Documents**: Files are automatically processed and added to RAG
2. **Ask Questions**: Chat interface uses RAG for intelligent responses
3. **Multilingual**: Supports both English and Arabic queries

### API Endpoints

#### Check RAG Status
```http
GET /rag/status
```
Returns system status and statistics.

#### Manual Document Ingestion
```http
POST /rag/ingest
```
Manually ingest all department documents into RAG system.

### Example Usage

```python
# Query the RAG system directly
from app_lib.rag_integration import query_rag

response, response_en = query_rag("What is the Central Bank of Oman's monetary policy?", "en")
print(response)

# Arabic query
response_ar, response_en = query_rag("ما هي السياسة النقدية للبنك المركزي العماني؟", "ar")
print(response_ar)
```

## Configuration

### Department Keywords
The system automatically categorizes documents based on content:

```python
keywords = {
    "Finance": ["budget", "revenue", "expense", "finance", "financial", "accounting", "monetary"],
    "Currency": ["banknotes", "coins", "mint", "currency", "exchange", "rate", "foreign"],
    "IT / Finance": ["network", "software", "hardware", "technology", "it", "digital", "system"],
    "Legal & Compliance": ["regulation", "law", "compliance", "legal", "policy", "framework"],
    "Monetary Policy & Banking": ["policy", "banking", "supervision", "stability", "monetary"]
}
```

### Model Configuration
- **Embeddings**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **LLM**: `google/flan-t5-base`
- **Chunk Size**: 800 characters with 100 character overlap
- **Retrieval**: Top 3 most similar chunks

## Benefits

### 🎯 **Improved Accuracy**
- Document-based responses are more accurate than generic AI responses
- Context-aware answers based on actual Central Bank documents
- Reduced hallucination through retrieval-augmented generation

### 🌐 **Multilingual Support**
- Native Arabic and English processing
- Automatic translation capabilities
- OCR support for Arabic text in images

### 🔄 **Scalable Architecture**
- Easy to add new documents
- Automatic indexing and search
- Efficient vector-based similarity matching

### 🛡️ **Robust Fallbacks**
- Multiple response layers ensure availability
- Graceful degradation when components fail
- Maintains existing functionality

## Monitoring

### Logs
The system provides comprehensive logging:
- RAG initialization status
- Document ingestion success/failure
- Query processing and response generation
- Error handling and fallback usage

### Status API
Monitor system health through the `/rag/status` endpoint:
```json
{
  "status": "success",
  "rag_ready": true,
  "stats": {
    "initialized": true,
    "document_count": 15,
    "embeddings_ready": true,
    "llm_ready": true,
    "qa_chain_ready": true
  }
}
```

## Troubleshooting

### Common Issues

1. **Dependencies Missing**
   - Install requirements: `pip install -r requirements_rag.txt`
   - Check for GPU availability for better performance

2. **RAG Not Initializing**
   - Check logs for initialization errors
   - Verify all dependencies are installed
   - Ensure sufficient system resources

3. **No Responses from RAG**
   - Check if documents are ingested: `/rag/status`
   - Manually ingest documents: `POST /rag/ingest`
   - Verify document processing is working

4. **Poor Response Quality**
   - Ensure documents contain relevant content
   - Check department tagging accuracy
   - Verify translation quality

## Future Enhancements

- **Fine-tuned Models**: Custom models trained on Central Bank data
- **Advanced Chunking**: Semantic chunking for better context
- **Multi-modal Support**: Image and table understanding
- **Real-time Updates**: Live document synchronization
- **Analytics**: Query analytics and usage patterns

## Support

For issues or questions about the RAG integration:
1. Check the application logs for error messages
2. Verify all dependencies are installed correctly
3. Test the `/rag/status` endpoint for system health
4. Review the integration code in `app_lib/rag_integration.py`
