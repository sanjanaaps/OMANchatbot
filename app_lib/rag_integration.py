# -*- coding: utf-8 -*-
"""
RAG Integration Module for Oman Central Bank Flask Application
Adapted from rag_module_py.py for Flask integration
"""

import os
import logging
from typing import List, Dict, Optional, Tuple
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.llms import HuggingFacePipeline
from langchain_huggingface import HuggingFaceEmbeddings
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import pytesseract
import pdfplumber
from PIL import Image
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Document processing for RAG system"""
    
    def __init__(self):
        self.ocr_lang = 'eng+ara'  # OCR for English + Arabic
        self.translator_en = GoogleTranslator(source='auto', target='en')
        self.translator_ar = GoogleTranslator(source='auto', target='ar')

    def extract_text_from_pdf(self, filepath: str) -> str:
        """Extract text from PDF file"""
        text = ""
        try:
            # Suppress pdfminer warnings
            import logging
            pdfminer_logger = logging.getLogger('pdfminer')
            original_level = pdfminer_logger.level
            pdfminer_logger.setLevel(logging.ERROR)
            
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            # Restore original logging level
            pdfminer_logger.setLevel(original_level)
        except Exception as e:
            logger.error(f"Error extracting text from PDF {filepath}: {str(e)}")
        return text

    def extract_text_from_image(self, filepath: str) -> str:
        """Extract text from image using OCR"""
        try:
            return pytesseract.image_to_string(Image.open(filepath), lang=self.ocr_lang)
        except Exception as e:
            logger.error(f"Error extracting text from image {filepath}: {str(e)}")
            return ""

    def translate_text_in_chunks(self, text: str, dest: str = 'en', chunk_size: int = 4000) -> str:
        """Translate large text safely in chunks"""
        if not text or not text.strip():
            return text
            
        try:
            translated_text = ""
            translator = self.translator_en if dest == 'en' else self.translator_ar
            
            for i in range(0, len(text), chunk_size):
                chunk = text[i:i+chunk_size]
                if chunk.strip():
                    translated_chunk = translator.translate(chunk)
                    translated_text += translated_chunk
                    
            return translated_text
        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return text  # Return original text if translation fails

    def process_document(self, filepath: str, filetype: str = 'pdf') -> Tuple[str, str, str, str]:
        """Process document and return original text, English translation, and summaries"""
        try:
            if filetype == 'pdf':
                text = self.extract_text_from_pdf(filepath)
            else:
                text = self.extract_text_from_image(filepath)

            if not text or not text.strip():
                return "", "", "No text extracted", "لم يتم استخراج نص"

            text_en = self.translate_text_in_chunks(text, dest='en')
            text_ar = text  # keep original as Arabic
            summary_en = "Document processed for RAG system"
            summary_ar = "تم معالجة المستند لنظام RAG"
            
            return text, text_en, summary_en, summary_ar
        except Exception as e:
            logger.error(f"Error processing document {filepath}: {str(e)}")
            return "", "", "Processing failed", "فشل في المعالجة"

class DepartmentTagger:
    """Department tagging based on content analysis"""
    
    def __init__(self):
        self.keywords = {
            "Finance": ["budget", "revenue", "expense", "finance", "financial", "accounting", "monetary"],
            "Currency": ["banknotes", "coins", "mint", "currency", "exchange", "rate", "foreign"],
            "IT / Finance": ["network", "software", "hardware", "technology", "it", "digital", "system"],
            "Legal & Compliance": ["regulation", "law", "compliance", "legal", "policy", "framework"],
            "Monetary Policy & Banking": ["policy", "banking", "supervision", "stability", "monetary"]
        }

    def tag(self, text: str) -> List[str]:
        """Tag document with relevant departments"""
        if not text:
            return []
            
        txt = text.lower()
        departments = []
        
        for dept, keywords in self.keywords.items():
            if any(keyword in txt for keyword in keywords):
                departments.append(dept)
                
        return departments if departments else ["General"]

def get_llm():
    """Initialize and return the language model"""
    try:
        model_name = "tiiuae/Falcon3-1B-Base"
        logger.info(f"Initializing LLM model: {model_name}")
        
        # Check if transformers and torch are available
        import torch
        from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
        
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        
        # Use startup device check
        import os
        device = 0 if os.environ.get('WHISPER_DEVICE', 'cpu') == 'cuda' else -1
        
        pipe = pipeline(
            "text2text-generation", 
            model=model, 
            tokenizer=tokenizer, 
            max_length=512, 
            device=device
        )
        
        logger.info("GPU detected." if device == 0 else "GPU not detected. Using CPU.")
        return HuggingFacePipeline(pipeline=pipe)
    except ImportError as e:
        logger.error(f"Required packages not installed for LLM: {str(e)}")
        logger.info("Install transformers and torch: pip install transformers torch")
        return None
    except Exception as e:
        logger.error(f"Error initializing LLM: {str(e)}")
        return None

# Prompt template for RAG system
prompt_template = """You are a helpful assistant for the Oman Central Bank.
Use the context to answer the question accurately and concisely.
If you don't know the answer, say you don't know.

Context: {context}

Question: {question}

Answer:"""

prompt = PromptTemplate(input_variables=["context", "question"], template=prompt_template)

class OmanCBRAG:
    """Oman Central Bank RAG System for Flask Integration"""
    
    def __init__(self, documents_folder: str = None):
        self.processor = DocumentProcessor()
        self.tagger = DepartmentTagger()
        self.embeddings = None
        self.vector_store = None
        self.qa_chain = None
        self.llm = None
        self.documents_folder = documents_folder
        self.is_initialized = False
        
        # Initialize components
        self._initialize_components()

    def _initialize_components(self):
        """Initialize RAG components"""
        try:
            # Initialize embeddings
            logger.info("Initializing embeddings...")
            import os
            device = os.environ.get('WHISPER_DEVICE', 'cpu')
            
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                model_kwargs={'device': device}
            )
            logger.info(f"Embeddings initialized successfully on {device}")
            
            # Initialize LLM
            self.llm = get_llm()
            
            if self.llm and self.embeddings:
                logger.info("RAG components initialized successfully")
            else:
                logger.warning("Some RAG components failed to initialize")
                if not self.llm:
                    logger.warning("LLM not available - RAG queries will not work")
                if not self.embeddings:
                    logger.warning("Embeddings not available - RAG indexing will not work")
                
        except ImportError as e:
            logger.error(f"Required packages not installed: {str(e)}")
            logger.info("Install required packages: pip install langchain transformers torch sentence-transformers faiss-cpu")
        except Exception as e:
            logger.error(f"Error initializing RAG components: {str(e)}")

    def ingest_documents_from_folder(self, folder_path: str) -> bool:
        """Ingest documents from a folder"""
        try:
            if not os.path.exists(folder_path):
                logger.error(f"Folder path does not exist: {folder_path}")
                return False
                
            documents = []
            
            for file in os.listdir(folder_path):
                if file.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg', '.tiff')):
                    file_path = os.path.join(folder_path, file)
                    file_type = 'pdf' if file.lower().endswith('.pdf') else 'image'
                    
                    text_orig, text_en, sum_en, sum_ar = self.processor.process_document(file_path, file_type)
                    
                    if not text_en or not text_en.strip():
                        logger.warning(f"No text extracted from {file}")
                        continue
                    
                    depts = self.tagger.tag(text_en)
                    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
                    chunks = splitter.split_text(text_en)
                    
                    for chunk in chunks:
                        if chunk.strip():
                            doc = Document(
                                page_content=chunk,
                                metadata={
                                    "filename": file,
                                    "summary_en": sum_en,
                                    "summary_ar": sum_ar,
                                    "departments": depts,
                                    "file_type": file_type
                                }
                            )
                            documents.append(doc)

            if not documents:
                logger.warning(f"No documents processed from folder: {folder_path}")
                return False

            # Create vector store
            self.vector_store = FAISS.from_documents(documents, self.embeddings)
            
            # Create QA chain
            retriever = self.vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 3})
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": prompt}
            )
            
            self.is_initialized = True
            logger.info(f"Successfully ingested and indexed {len(documents)} chunks from folder {folder_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error ingesting documents: {str(e)}")
            return False

    def ingest_single_document(self, file_path: str, filename: str, department: str) -> bool:
        """Ingest a single document into the RAG system"""
        logger.info(f"📄 RAG: Ingesting document: {filename}")
        logger.info(f"📁 RAG: Processing file: {file_path}")
        
        try:
            if not self.embeddings or not self.llm:
                logger.error(f"❌ RAG: Components not initialized for {filename}")
                return False
                
            file_type = 'pdf' if filename.lower().endswith('.pdf') else 'image'
            logger.info(f"📋 RAG: File type detected: {file_type}")
            
            logger.info(f"🔄 RAG: Processing document with processor...")
            text_orig, text_en, sum_en, sum_ar = self.processor.process_document(file_path, file_type)
            logger.info(f"📊 RAG: Document processing completed")
            logger.info(f"📏 RAG: Original text length: {len(text_orig) if text_orig else 0} chars")
            logger.info(f"📏 RAG: English text length: {len(text_en) if text_en else 0} chars")
            logger.info(f"📝 RAG: Summary EN length: {len(sum_en) if sum_en else 0} chars")
            logger.info(f"📝 RAG: Summary AR length: {len(sum_ar) if sum_ar else 0} chars")
            
            if not text_en or not text_en.strip():
                logger.warning(f"⚠️ RAG: No text extracted from {filename}")
                return False
            
            # Use provided department or auto-detect
            depts = [department] if department else self.tagger.tag(text_en)
            logger.info(f"🏢 RAG: Departments assigned: {depts}")
            
            logger.info(f"✂️ RAG: Splitting text into chunks...")
            splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
            chunks = splitter.split_text(text_en)
            logger.info(f"📦 RAG: Created {len(chunks)} text chunks")
            
            documents = []
            for i, chunk in enumerate(chunks):
                if chunk.strip():
                    doc = Document(
                        page_content=chunk,
                        metadata={
                            "filename": filename,
                            "summary_en": sum_en,
                            "summary_ar": sum_ar,
                            "departments": depts,
                            "file_type": file_type
                        }
                    )
                    documents.append(doc)
                    logger.debug(f"📄 RAG: Created document chunk {i+1}/{len(chunks)} for {filename}")

            if not documents:
                logger.error(f"❌ RAG: No valid documents created from {filename}")
                return False

            logger.info(f"🔍 RAG: Creating vector embeddings for {len(documents)} documents...")
            # Add to existing vector store or create new one
            if self.vector_store:
                logger.info(f"🔄 RAG: Merging with existing vector store...")
                # Add to existing vector store
                new_vector_store = FAISS.from_documents(documents, self.embeddings)
                self.vector_store.merge_from(new_vector_store)
                logger.info(f"✅ RAG: Successfully merged {len(documents)} documents with existing vector store")
            else:
                logger.info(f"🆕 RAG: Creating new vector store...")
                # Create new vector store
                self.vector_store = FAISS.from_documents(documents, self.embeddings)
                logger.info(f"✅ RAG: Successfully created new vector store with {len(documents)} documents")

            logger.info(f"🔗 RAG: Recreating QA chain with updated vector store...")
            # Recreate QA chain with updated vector store
            retriever = self.vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 3})
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": prompt}
            )
            
            self.is_initialized = True
            logger.info(f"🎉 RAG: SUCCESS - Document {filename} fully ingested into RAG system")
            logger.info(f"📊 RAG: Final result - {len(documents)} chunks indexed, system ready for queries")
            return True
            
        except Exception as e:
            logger.error(f"❌ RAG: Error ingesting single document {filename}: {str(e)}")
            logger.error(f"🔍 RAG: Full error details: {str(e)}")
            return False

    def query(self, question: str, language: str = 'en') -> Tuple[str, str]:
        """Query the RAG system"""
        logger.info(f"🔍 RAG: Starting query processing")
        logger.info(f"❓ RAG: Question: {question[:100]}{'...' if len(question) > 100 else ''}")
        logger.info(f"🌐 RAG: Language: {language}")
        
        try:
            if not self.qa_chain or not self.is_initialized:
                logger.warning(f"⚠️ RAG: System not initialized for query")
                return "RAG system not initialized. Please ensure documents are ingested first.", ""

            logger.info(f"🔍 RAG: Executing query against vector store...")
            result = self.qa_chain({"query": question})
            answer_en = result["result"]
            logger.info(f"📤 RAG: Query completed, response length: {len(answer_en)} chars")

            if language == 'ar':
                logger.info(f"🌐 RAG: Translating response to Arabic...")
                answer_ar = self.processor.translate_text_in_chunks(answer_en, dest='ar')
                logger.info(f"✅ RAG: Arabic translation completed")
                return answer_ar, answer_en
            else:
                logger.info(f"✅ RAG: Query completed successfully")
                return answer_en, answer_en
                
        except Exception as e:
            logger.error(f"Error querying RAG system: {str(e)}")
            return f"Error processing query: {str(e)}", ""

    def is_ready(self) -> bool:
        """Check if RAG system is ready for queries"""
        return self.is_initialized and self.qa_chain is not None

    def get_stats(self) -> Dict:
        """Get RAG system statistics"""
        try:
            if self.vector_store:
                # Get approximate document count
                doc_count = len(self.vector_store.index_to_docstore_id)
                return {
                    "initialized": self.is_initialized,
                    "document_count": doc_count,
                    "embeddings_ready": self.embeddings is not None,
                    "llm_ready": self.llm is not None,
                    "qa_chain_ready": self.qa_chain is not None
                }
            else:
                return {
                    "initialized": False,
                    "document_count": 0,
                    "embeddings_ready": self.embeddings is not None,
                    "llm_ready": self.llm is not None,
                    "qa_chain_ready": False
                }
        except Exception as e:
            logger.error(f"Error getting RAG stats: {str(e)}")
            return {"error": str(e)}

# Global RAG instance
rag_system = None

def initialize_rag_system(documents_folder: str = None) -> OmanCBRAG:
    """Initialize the global RAG system"""
    global rag_system
    try:
        rag_system = OmanCBRAG(documents_folder)
        if documents_folder and os.path.exists(documents_folder):
            rag_system.ingest_documents_from_folder(documents_folder)
        return rag_system
    except Exception as e:
        logger.error(f"Error initializing RAG system: {str(e)}")
        return None

def get_rag_system() -> Optional[OmanCBRAG]:
    """Get the global RAG system instance"""
    return rag_system

def add_document_to_rag(file_path: str, filename: str, department: str) -> bool:
    """Add a document to the RAG system"""
    logger.info(f"🔧 RAG: Starting document ingestion for: {filename}")
    logger.info(f"📁 RAG: File path: {file_path}")
    logger.info(f"🏢 RAG: Department: {department}")
    
    global rag_system
    if not rag_system:
        logger.info(f"🔄 RAG: System not initialized, initializing...")
        rag_system = initialize_rag_system()
    
    if rag_system:
        logger.info(f"✅ RAG: System ready, calling ingest_single_document")
        result = rag_system.ingest_single_document(file_path, filename, department)
        if result:
            logger.info(f"🎉 RAG: SUCCESS - Document {filename} successfully ingested into RAG system")
        else:
            logger.error(f"❌ RAG: FAILED - Document {filename} could not be ingested into RAG system")
        return result
    else:
        logger.error(f"❌ RAG: System initialization failed, cannot ingest document {filename}")
        return False

def query_rag(question: str, language: str = 'en') -> Tuple[str, str]:
    """Query the RAG system"""
    logger.info(f"🔍 RAG: Query request received")
    logger.info(f"❓ RAG: Question: {question[:100]}{'...' if len(question) > 100 else ''}")
    logger.info(f"🌐 RAG: Language: {language}")
    
    global rag_system
    if not rag_system:
        logger.warning(f"⚠️ RAG: System not available for query")
        return "RAG system not available", ""
    
    logger.info(f"✅ RAG: System available, processing query...")
    result = rag_system.query(question, language)
    logger.info(f"📤 RAG: Query result returned")
    return result