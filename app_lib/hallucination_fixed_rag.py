# -*- coding: utf-8 -*-
"""
Hallucination Fixed RAG System for Oman Central Bank
Based on the hallucination_fixed.py implementation
"""

import os
import torch
import pdfplumber
import pytesseract
from PIL import Image
from deep_translator import GoogleTranslator
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_community.llms import HuggingFacePipeline
from langchain_huggingface import HuggingFaceEmbeddings
import logging
import warnings

# Suppress PDF processing warnings
warnings.filterwarnings('ignore', category=UserWarning, module='pdfminer')
warnings.filterwarnings('ignore', message='.*Cannot set gray stroke color.*')

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.ocr_lang = 'eng+ara'
        self.translator_en = GoogleTranslator(source='auto', target='en')
        self.translator_ar = GoogleTranslator(source='auto', target='ar')

    def extract_text_from_pdf(self, filepath):
        text = ""
        try:
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            logger.error(f"Error extracting text from PDF {filepath}: {str(e)}")
        return text

    def extract_text_from_image(self, filepath):
        try:
            return pytesseract.image_to_string(Image.open(filepath), lang=self.ocr_lang)
        except Exception as e:
            logger.error(f"Error extracting text from image {filepath}: {str(e)}")
            return ""

    def extract_text_from_txt(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error extracting text from TXT {filepath}: {str(e)}")
            return ""

    def extract_text_from_md(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error extracting text from MD {filepath}: {str(e)}")
            return ""

    def translate_text_in_chunks(self, text, dest='en', chunk_size=4000):
        translated_text = ""
        translator = self.translator_en if dest == 'en' else self.translator_ar
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            try:
                translated_text += translator.translate(chunk)
            except Exception as e:
                logger.warning(f"Error translating chunk: {e}")
                translated_text += chunk
        return translated_text

    def process_document(self, filepath, filetype='pdf'):
        try:
            text = ""
            if filetype == 'pdf':
                text = self.extract_text_from_pdf(filepath)
            elif filetype == 'txt':
                text = self.extract_text_from_txt(filepath)
            elif filetype == 'md':
                text = self.extract_text_from_md(filepath)
            else:
                raise ValueError(f"Unsupported file type: {filetype}")

            text_en = self.translate_text_in_chunks(text, dest='en')
            summary_en = "Summarization disabled"
            summary_ar = "Summarization disabled"
            return text, text_en, summary_en, summary_ar
        except Exception as e:
            logger.warning(f"Error processing document {filepath}: {str(e)}")
            return "", "", "Error processing document", "خطأ في معالجة المستند"


class DepartmentTagger:
    def __init__(self):
        self.keywords = {
            "Finance": ["budget", "revenue", "expense", "finance", "financial", "monetary", "banking"],
            "Currency": ["banknotes", "coins", "mint", "currency", "rial", "exchange", "foreign exchange"],
            "IT": ["network", "software", "hardware", "technology", "it", "digital", "cyber"],
            "Legal": ["regulation", "law", "compliance", "legal", "policy", "governance"],
            "Policy": ["policy", "regulation", "framework", "guidelines", "standards"],
            "Operations": ["operations", "process", "procedure", "workflow", "management"]
        }

    def tag(self, text):
        txt = text.lower()
        return [dept for dept, kws in self.keywords.items() if any(kw in txt for kw in kws)]


def get_llm():
    """Initialize the LLM with Falcon model - only if GPU is available"""
    try:
        # Check GPU availability first
        if not torch.cuda.is_available():
            logger.warning("⚠️ GPU not detected. Skipping Falcon model loading to avoid memory issues.")
            logger.info("💡 RAG system will use Gemini fallback for all queries.")
            return None, None
        
        logger.info("✅ GPU detected. Loading Falcon model...")
        model_name = "tiiuae/Falcon-H1-1B-Base"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",
            torch_dtype=torch.bfloat16
        )
        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=512,
            do_sample=False  # Deterministic output to reduce hallucination
        )
        logger.info("✅ Falcon model loaded successfully on GPU")
        return HuggingFacePipeline(pipeline=pipe), model
    except Exception as e:
        logger.error(f"Error initializing LLM: {str(e)}")
        logger.info("💡 RAG system will use Gemini fallback for all queries.")
        return None, None


# Import prompt template from the centralized module
from app_lib.prompt_templates import RAG_PROMPT_TEMPLATE

# Use the centralized prompt template
prompt = PromptTemplate(input_variables=["context", "question"], template=RAG_PROMPT_TEMPLATE)


class HallucinationFixedRAG:
    def __init__(self, upload_folder):
        self.upload_folder = upload_folder
        self.processor = DocumentProcessor()
        self.tagger = DepartmentTagger()
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
        self.vector_store = None
        self.llm, self.model = get_llm()
        self.qa_chain = None
        self.weights_path = os.path.join(upload_folder, "falcon_h1_weights.pth")
        self.is_ready_flag = False

    def is_ready(self):
        # System is ready if we have a vector store, even without the LLM model
        # The LLM model is optional - we can use Gemini fallback
        return self.is_ready_flag and self.vector_store is not None

    def get_stats(self):
        if self.vector_store:
            return {
                "documents_indexed": self.vector_store.index.ntotal if hasattr(self.vector_store, 'index') else 0,
                "model_loaded": self.llm is not None,
                "gpu_available": torch.cuda.is_available()
            }
        return {"documents_indexed": 0, "model_loaded": False, "gpu_available": False}

    def ingest_documents(self, folder_path=None):
        """Ingest documents from the upload folder and additional files"""
        documents = []
        
        # Process files in the upload folder
        if folder_path and os.path.exists(folder_path):
            for filename in os.listdir(folder_path):
                if filename.startswith('.'):
                    continue
                    
                file_path = os.path.join(folder_path, filename)
                if not os.path.isfile(file_path):
                    continue
                    
                file_extension = os.path.splitext(filename)[1].lower()
                
                try:
                    if file_extension == ".pdf":
                        _, text_en, sum_en, sum_ar = self.processor.process_document(file_path, 'pdf')
                    elif file_extension == ".txt":
                        _, text_en, sum_en, sum_ar = self.processor.process_document(file_path, 'txt')
                    elif file_extension == ".md":
                        _, text_en, sum_en, sum_ar = self.processor.process_document(file_path, 'md')
                    else:
                        logger.info(f"Skipping unsupported file type: {filename}")
                        continue

                    if not text_en.strip():
                        logger.warning(f"No text extracted from {filename}")
                        continue

                    departments = self.tagger.tag(text_en)
                    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
                    chunks = splitter.split_text(text_en)
                    
                    for chunk in chunks:
                        documents.append(Document(
                            page_content=chunk,
                            metadata={
                                "filename": filename,
                                "summary_en": sum_en,
                                "summary_ar": sum_ar,
                                "departments": departments
                            }
                        ))
                        
                except Exception as e:
                    logger.warning(f"Error processing file {filename}: {str(e)} - skipping this file")
                    continue

        # Process additional files outside the zip (Q&A format)
        additional_files = [
            os.path.join(self.upload_folder, "banking_knowledge.txt"),
            os.path.join(self.upload_folder, "cbo_faq_mapping.md")
        ]
        
        for file_path in additional_files:
            if os.path.exists(file_path):
                filename = os.path.basename(file_path)
                file_extension = os.path.splitext(filename)[1].lower()

                try:
                    if file_extension == ".txt":
                        _, text_en, sum_en, sum_ar = self.processor.process_document(file_path, 'txt')
                    elif file_extension == ".md":
                        _, text_en, sum_en, sum_ar = self.processor.process_document(file_path, 'md')
                    else:
                        logger.info(f"Skipping unsupported additional file type: {filename}")
                        continue

                    if not text_en.strip():
                        logger.warning(f"No text extracted from additional file {filename}")
                        continue

                    departments = self.tagger.tag(text_en)
                    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
                    chunks = splitter.split_text(text_en)
                    
                    for chunk in chunks:
                        documents.append(Document(
                            page_content=chunk,
                            metadata={
                                "filename": filename,
                                "summary_en": sum_en,
                                "summary_ar": sum_ar,
                                "departments": departments,
                                "source": "faq"  # Mark as FAQ source
                            }
                        ))
                        
                except Exception as e:
                    logger.error(f"Error processing additional file {filename}: {str(e)}")
                    continue

        if not documents:
            logger.warning("No documents processed from upload folder and additional files.")
            return False

        try:
            self.vector_store = FAISS.from_documents(documents, self.embeddings)
            if self.llm:
                self.qa_chain = RetrievalQA.from_chain_type(
                    llm=self.llm,
                    chain_type="stuff",
                    retriever=self.vector_store.as_retriever(),
                    chain_type_kwargs={"prompt": prompt},
                    return_source_documents=False,
                )
                logger.info(f"✅ Indexed {len(documents)} chunks and initialized QA chain with Falcon model")
            else:
                logger.info(f"✅ Indexed {len(documents)} chunks - will use Gemini fallback for queries")
            self.is_ready_flag = True
            return True
        except Exception as e:
            logger.error(f"Error creating vector store: {str(e)}")
            return False

    def save_weights(self, path=None):
        """Save model weights to file"""
        if not self.model:
            logger.warning("No model loaded (GPU not available). Skipping weights save.")
            return False
            
        try:
            weights_path = path or self.weights_path
            torch.save(self.model.state_dict(), weights_path)
            logger.info(f"✅ Model weights saved to {weights_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving weights: {str(e)}")
            return False

    def load_weights(self, path=None):
        """Load model weights from file"""
        if not self.model:
            logger.warning("No model loaded (GPU not available). Skipping weights load.")
            return False
            
        try:
            weights_path = path or self.weights_path
            if os.path.exists(weights_path):
                self.model.load_state_dict(torch.load(weights_path))
                logger.info(f"✅ Model weights loaded from {weights_path}")
                return True
            else:
                logger.warning(f"Weights file not found: {weights_path}")
                return False
        except Exception as e:
            logger.error(f"Error loading weights: {str(e)}")
            return False

    def query(self, question, language='en', department=None):
        """Query the RAG system with fallback to Gemini"""
        if not self.qa_chain:
            if not self.llm:
                logger.info("No Falcon model available (GPU not detected). Using Gemini fallback.")
            else:
                logger.warning("QA chain not initialized. Using Gemini fallback.")
            return self._fallback_to_gemini(question, language, department)

        logger.info(f"Received question in {language}: {question}")

        translated_question = question
        if language == 'ar':
            try:
                translated_question = self.processor.translate_text_in_chunks(question, dest='en')
                logger.info(f"Translated question to English: {translated_question}")
            except Exception as e:
                logger.error(f"Error translating question: {e}")
                return self._fallback_to_gemini(question, language, department)

        try:
            result = self.qa_chain.invoke({"query": translated_question})
            answer_en = result["result"]
            logger.info(f"Generated English answer: {answer_en}")
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return self._fallback_to_gemini(question, language, department)

        if language == 'ar':
            try:
                answer_ar = self.processor.translate_text_in_chunks(answer_en, dest='ar')
                logger.info(f"Translated answer to Arabic: {answer_ar}")
                return answer_ar, answer_en
            except Exception as e:
                logger.error(f"Error translating answer back to Arabic: {e}")
                return "Error translating the answer.", answer_en
        else:
            return answer_en, answer_en

    def _fallback_to_gemini(self, question, language, department):
        """Fallback to Gemini when RAG system is not available"""
        try:
            from app_lib.gemini import query_gemini
            answer = query_gemini(question, department or "General", language)
            return answer, answer
        except Exception as e:
            logger.error(f"Gemini fallback also failed: {str(e)}")
            if language == 'ar':
                return "عذراً، حدث خطأ في معالجة سؤالك. يرجى المحاولة مرة أخرى.", "Sorry, an error occurred processing your question. Please try again."
            else:
                return "Sorry, an error occurred processing your question. Please try again.", "Sorry, an error occurred processing your question. Please try again."


# Standalone document ingestion script for GPU processing
def create_standalone_ingestion_script():
    """Create a standalone Python script for document ingestion on GPU"""
    script_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone Document Ingestion Script for GPU Processing
Run this script on a GPU-enabled machine to process documents and save weights
"""

import os
import sys
import argparse
from app_lib.hallucination_fixed_rag import HallucinationFixedRAG

def main():
    parser = argparse.ArgumentParser(description='Ingest documents for Oman Central Bank RAG system')
    parser.add_argument('--upload_folder', required=True, help='Path to upload folder containing documents')
    parser.add_argument('--weights_path', help='Path to save model weights (optional)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.INFO)
    
    if not os.path.exists(args.upload_folder):
        print(f"Error: Upload folder {args.upload_folder} does not exist")
        sys.exit(1)
    
    print("Initializing Hallucination Fixed RAG system...")
    rag = HallucinationFixedRAG(args.upload_folder)
    
    print("Ingesting documents...")
    success = rag.ingest_documents(args.upload_folder)
    
    if success:
        print("✅ Document ingestion completed successfully")
        
        # Save weights if specified
        if args.weights_path:
            rag.save_weights(args.weights_path)
        else:
            rag.save_weights()
            
        print("✅ Model weights saved")
        print(f"📊 Stats: {rag.get_stats()}")
    else:
        print("❌ Document ingestion failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    
    script_path = os.path.join(os.path.dirname(__file__), "ingest_documents_gpu.py")
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    logger.info(f"Created standalone ingestion script: {script_path}")
    return script_path


# Initialize the RAG system
def initialize_hallucination_fixed_rag(upload_folder, ingest_documents=False):
    """Initialize the Hallucination Fixed RAG system"""
    try:
        rag = HallucinationFixedRAG(upload_folder)
        
        # Only ingest documents if explicitly requested
        if ingest_documents:
            success = rag.ingest_documents(upload_folder)
            if success:
                logger.info("✅ Hallucination Fixed RAG system initialized successfully with document ingestion")
            else:
                logger.warning("⚠️ Hallucination Fixed RAG system initialized but document ingestion failed")
        else:
            logger.info("✅ Hallucination Fixed RAG system initialized (documents not ingested - use ingest_documents_gpu.py for ingestion)")
        
        return rag
    except Exception as e:
        logger.error(f"Failed to initialize Hallucination Fixed RAG system: {str(e)}")
        return None


def get_hallucination_fixed_rag():
    """Get the global RAG system instance"""
    return globals().get('_rag_instance', None)


def add_document_to_hallucination_fixed_rag(file_path, filename, department):
    """Add a single document to the RAG system"""
    rag = get_hallucination_fixed_rag()
    if not rag:
        return False
    
    try:
        # This would need to be implemented to add single documents
        # For now, we'll re-ingest all documents
        return rag.ingest_documents(rag.upload_folder)
    except Exception as e:
        logger.error(f"Error adding document to RAG: {str(e)}")
        return False


def query_hallucination_fixed_rag(question, language='en', department=None):
    """Query the Hallucination Fixed RAG system"""
    rag = get_hallucination_fixed_rag()
    if not rag:
        return "RAG system not available", ""
    
    return rag.query(question, language, department)

