from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
import os
import sys
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_lib.db import get_db, init_db
from app_lib.models import db, User, Document, ChatMessage
from app_lib.auth import login_required, get_current_user, check_password_hash
from app_lib.extract import extract_text_from_file
from app_lib.search import search_documents, get_document_summary
from app_lib.gemini import query_gemini, translate_text, get_department_focus, get_department_focus_arabic
from app_lib.difflib_responses import get_difflib_response
from app_lib.structured_analysis import (
    generate_structured_summary, 
    is_pdf_document, 
    analyze_financial_document, 
    detect_financial_document_type
)
from app_lib.prompt_templates import (
    get_prompt_template, 
    match_document_type, 
    is_financial_document_type,
    format_prompt_template,
    RAG_PROMPT_TEMPLATE
)
from app_lib.sensitive_data_masking import mask_sensitive_data, should_mask_for_user, get_masking_info
from app_lib.voice_service import VoiceRecordingService
from app_lib.faq_service import get_faq_service
# Hallucination Fixed RAG integration - conditionally loaded based on user choice
RAG_ENABLED = True  # Enable by default for hallucination-fixed RAG
RAG_AVAILABLE = False
rag_system = None

# Dummy functions for when RAG is disabled
def initialize_rag_system(*args, **kwargs):
    return None

def get_rag_system():
    return None

def add_document_to_rag(*args, **kwargs):
    return False

def query_rag(*args, **kwargs):
    return "RAG system not available", ""
from config import get_config
from app_lib.whisper_service import WhisperService, is_gpu_available, is_ffmpeg_available
import logging

app = Flask(__name__)

# Load configuration
config_class = get_config()
app.config.from_object(config_class)

# Initialize database
init_db(app)

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress PDF processing warnings
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='pdfminer')
warnings.filterwarnings('ignore', message='.*Cannot set gray stroke color.*')

# Initialize Whisper at startup (ignore UI/testing integrations)
WHISPER_SERVICE = None
try:
    gpu = is_gpu_available()
    ffmpeg = is_ffmpeg_available()
    logger.info(f"GPU available for Whisper: {gpu}; ffmpeg available: {ffmpeg}")
    t0 = None
    import time as _time
    t0 = _time.perf_counter()
    WHISPER_SERVICE = WhisperService(app.config['UPLOAD_FOLDER'], model_name='base')
    t1 = _time.perf_counter()
    logger.info(f"Whisper initialized in {t1 - t0:.2f}s; device: {WHISPER_SERVICE.device}")
except Exception as e:
    logger.warning(f"Whisper initialization failed: {e}")

# Voice recording service (singleton)
voice_service = VoiceRecordingService()

# Initialize Hallucination Fixed RAG based on user choice (set by startup_config.py)
def initialize_rag_if_enabled():
    """Initialize Hallucination Fixed RAG system if it was enabled during startup"""
    global RAG_ENABLED, RAG_AVAILABLE, rag_system
    
    if RAG_ENABLED:
        try:
            from app_lib.hallucination_fixed_rag import (
                initialize_hallucination_fixed_rag as _init_rag, 
                get_hallucination_fixed_rag as _get_rag, 
                add_document_to_hallucination_fixed_rag as _add_doc, 
                query_hallucination_fixed_rag as _query_rag
            )
            
            # Replace dummy functions with real ones
            globals()['initialize_rag_system'] = _init_rag
            globals()['get_rag_system'] = _get_rag
            globals()['add_document_to_rag'] = _add_doc
            globals()['query_rag'] = _query_rag
            
            RAG_AVAILABLE = True
            logger.info("Hallucination Fixed RAG integration enabled - initializing...")
            
            # Initialize RAG system without document ingestion (use ingest_documents_gpu.py for ingestion)
            rag_system = initialize_rag_system(app.config['UPLOAD_FOLDER'], ingest_documents=False)
            if rag_system:
                # Try to load existing weights if available and model is loaded
                weights_path = os.path.join(app.config['UPLOAD_FOLDER'], "falcon_h1_weights.pth")
                if os.path.exists(weights_path) and rag_system.model:
                    logger.info(f"Loading existing model weights from {weights_path}")
                    rag_system.load_weights(weights_path)
                elif os.path.exists(weights_path) and not rag_system.model:
                    logger.info(f"Weights file exists but no model loaded (GPU not available)")
                
                if rag_system.is_ready():
                    if rag_system.model:
                        logger.info("✅ Hallucination Fixed RAG system initialized successfully with Falcon model")
                    else:
                        logger.info("✅ Hallucination Fixed RAG system initialized successfully (Gemini fallback mode)")
                else:
                    logger.warning("⚠️ Hallucination Fixed RAG system initialized but not ready - will use Gemini fallback")
            else:
                logger.warning("⚠️ Hallucination Fixed RAG system failed to initialize - will use Gemini fallback")
                
        except Exception as e:
            logger.error(f"Failed to initialize Hallucination Fixed RAG system: {str(e)}")
            RAG_AVAILABLE = False
    else:
        logger.info("📝 RAG functionality disabled - running without RAG")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def apply_sensitive_data_masking(text: str, user_department: str) -> str:
    """
    Apply sensitive data masking to text based on user department
    
    Args:
        text: The text to mask
        user_department: The department of the logged-in user
        
    Returns:
        str: Text with sensitive information masked
    """
    if not text or not text.strip():
        return text
        
    try:
        masked_text = mask_sensitive_data(text, user_department)
        if masked_text != text:
            logger.info(f"Applied sensitive data masking for {user_department} department")
        return masked_text
    except Exception as e:
        logger.error(f"Error applying sensitive data masking: {str(e)}")
        return text


@app.route('/')
def index():
    # Initialize RAG on first request if enabled
    if RAG_ENABLED and not RAG_AVAILABLE:
        try:
            initialize_rag_if_enabled()
        except Exception as e:
            logger.warning(f"RAG initialization failed: {str(e)}")
    
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')
        
        # Get user from database
        user = User.query.filter_by(username=username).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid username or password.', 'error')
            return render_template('login.html')
        
        # Login successful
        session['user_id'] = user.id
        session['username'] = user.username
        session['department'] = user.department
        
        flash(f'Welcome back, {user.username}!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    if not user:
        flash('User session expired. Please login again.', 'error')
        return redirect(url_for('login'))
    
    # Get documents for user's department
    user_department = user.department
    recent_docs = Document.query.filter_by(department=user_department).order_by(Document.upload_date.desc()).limit(10).all()
    doc_count = Document.query.filter_by(department=user_department).count()
    
    return render_template('dashboard.html', 
                         user=user, 
                         recent_docs=recent_docs,
                         doc_count=doc_count)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Get user-specified document type
            user_document_type = request.form.get('document_type', '').strip()
            
            try:
                # Extract text from file
                extracted_text = extract_text_from_file(filepath)
                
                if not extracted_text.strip():
                    flash('No text could be extracted from the file', 'error')
                    os.remove(filepath)
                    return redirect(request.url)
                
                # Determine document type: user-specified > auto-detected
                if user_document_type:
                    # Try to match user input to financial document types
                    matched_type = match_document_type(user_document_type)
                    if matched_type:
                        financial_doc_type = matched_type
                        logger.info(f"User specified document type '{user_document_type}' matched to '{matched_type}'")
                    else:
                        # Use user input as-is if no match found
                        financial_doc_type = user_document_type
                        logger.info(f"User specified document type '{user_document_type}' (not in financial types)")
                else:
                    # Auto-detect document type
                    financial_doc_type = detect_financial_document_type(filename, extracted_text)
                    logger.info(f"Auto-detected document type: {financial_doc_type}")
                
                # Save document to database
                user = get_current_user()
                document = Document(
                    filename=filename,
                    department=user.department,
                    uploaded_by=user.username,
                    content=extracted_text,
                    file_type=filename.rsplit('.', 1)[1].lower(),
                    document_type=financial_doc_type  # Store detected document type
                )
                
                db.session.add(document)
                db.session.commit()
                result = document
                
                # Add document to RAG system (optional - won't break upload if RAG fails)
                try:
                    if rag_system and rag_system.is_ready():
                        success = add_document_to_rag(filepath, filename, user.department)
                        if success:
                            logger.info(f"Document {filename} added to RAG system")
                        else:
                            logger.warning(f"Failed to add document {filename} to RAG system")
                    else:
                        logger.info(f"RAG system not ready, document {filename} saved but not indexed")
                except Exception as e:
                    logger.warning(f"RAG system error (non-critical): {str(e)}")
                
                # Generate appropriate analysis based on detected document type
                summary_ar = None  # Initialize Arabic summary
                
                # Try RAG system first for document summarization
                if rag_system and rag_system.is_ready():
                    try:
                        # Use RAG system to generate summary using the appropriate prompt template
                        if is_financial_document_type(financial_doc_type):
                            # Use financial document analysis prompt
                            prompt = format_prompt_template(
                                get_prompt_template(financial_doc_type, "financial"),
                                document_content=extracted_text[:2000]
                            )
                        else:
                            # Use general document analysis prompt
                            prompt = format_prompt_template(
                                get_prompt_template(financial_doc_type, "general"),
                                document_content=extracted_text[:2000]
                            )
                        
                        rag_summary, rag_summary_en = query_rag(prompt, 'en', user.department)
                        # Translate English summary to Arabic instead of generating separately
                        rag_summary_ar = translate_text(rag_summary, 'ar')
                        
                        if rag_summary and not rag_summary.startswith("RAG system not") and len(rag_summary.strip()) > 50:
                            summary = rag_summary
                            summary_ar = rag_summary_ar
                            logger.info(f"Generated RAG-based summary for: {filename} (type: {financial_doc_type})")
                        else:
                            raise Exception("RAG system returned invalid response")
                    except Exception as e:
                        logger.warning(f"RAG summarization failed: {str(e)}, falling back to structured analysis")
                        # Fallback to structured analysis
                        summary = None
                        summary_ar = None
                else:
                    logger.info("RAG system not ready, using structured analysis")
                    summary = None
                    summary_ar = None
                
                # Fallback to structured analysis if RAG didn't work
                if not summary:
                    if is_financial_document_type(financial_doc_type):
                        # Use financial document analysis for financial documents
                        try:
                            summary = analyze_financial_document(extracted_text, user.department, 'en')
                            summary_ar = translate_text(summary, 'ar')
                            logger.info(f"Generated financial document analysis for {financial_doc_type}: {filename}")
                        except Exception as e:
                            logger.error(f"Financial document analysis error: {str(e)}")
                            # Fallback to structured analysis
                            try:
                                summary = generate_structured_summary(extracted_text, user.department, 'en')
                                summary_ar = translate_text(summary, 'ar')
                                logger.info(f"Fallback to structured summary for: {filename}")
                            except Exception as e2:
                                logger.error(f"Structured analysis fallback error: {str(e2)}")
                                summary = get_document_summary(extracted_text)
                                if not summary or "Hello! I'm your AI assistant" in summary or len(summary.strip()) < 50:
                                    words = extracted_text.split()
                                    word_count = len(words)
                                    sentences = extracted_text.split('.')[:3]
                                    key_sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
                                    key_content = '. '.join(key_sentences[:2])
                                    if key_content:
                                        summary = f"Financial Document Summary: This {user.department} department financial document ({word_count} words) contains information about: {key_content}..."
                                    else:
                                        summary = f"Financial Document Summary: This {user.department} department financial document contains {word_count} words of financial information. Key topics include: {', '.join(words[:15])}..."
                                
                                # Translate English summary to Arabic
                                try:
                                    summary_ar = translate_text(summary, 'ar')
                                except:
                                    summary_ar = f"ملخص المستند المالي: تم تحليل مستند مالي من قسم {user.department} بنجاح. يحتوي على معلومات مهمة حول العمليات المالية."
                    else:
                        # Use structured analysis for non-financial documents
                        try:
                            summary = generate_structured_summary(extracted_text, user.department, 'en')
                            summary_ar = translate_text(summary, 'ar')
                            logger.info(f"Generated structured summary for non-financial document: {filename}")
                        except Exception as e:
                            logger.error(f"Structured analysis error: {str(e)}")
                            # Fallback to regular summary
                            summary = get_document_summary(extracted_text)
                            if not summary or "Hello! I'm your AI assistant" in summary or len(summary.strip()) < 50:
                                words = extracted_text.split()
                                word_count = len(words)
                                sentences = extracted_text.split('.')[:3]
                                key_sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
                                key_content = '. '.join(key_sentences[:2])
                                if key_content:
                                    summary = f"Document Summary: This {user.department} department document ({word_count} words) contains information about: {key_content}..."
                                else:
                                    summary = f"Document Summary: This {user.department} department document contains {word_count} words of information. Key topics include: {', '.join(words[:15])}..."
                            
                            # Translate English summary to Arabic
                            try:
                                summary_ar = translate_text(summary, 'ar')
                            except:
                                summary_ar = f"ملخص المستند: تم تحليل مستند من قسم {user.department} بنجاح. يحتوي على معلومات مهمة."
                elif is_pdf_document(filename):
                    # Use structured analysis for non-financial PDF documents
                    try:
                        summary = generate_structured_summary(extracted_text, user.department, 'en')
                        summary_ar = translate_text(summary, 'ar')
                        logger.info(f"Generated structured summary for PDF: {filename}")
                    except Exception as e:
                        logger.error(f"Structured analysis error: {str(e)}")
                        # Fallback to regular summary with both languages
                        summary = get_document_summary(extracted_text)
                        if not summary or len(summary.strip()) < 50:
                            words = extracted_text.split()
                            word_count = len(words)
                            sentences = extracted_text.split('.')[:3]
                            key_sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
                            key_content = '. '.join(key_sentences[:2])
                            if key_content:
                                summary = f"Document Summary: This {user.department} department document ({word_count} words) contains information about: {key_content}..."
                            else:
                                summary = f"Document Summary: This {user.department} department document contains {word_count} words of financial and policy information. Key topics include: {', '.join(words[:15])}..."
                        
                        # Translate English summary to Arabic
                        try:
                            summary_ar = translate_text(summary, 'ar')
                        except:
                            summary_ar = f"ملخص المستند: تم تحليل مستند من قسم {user.department} بنجاح. يحتوي على معلومات مهمة حول العمليات المالية والسياسات."
                else:
                    # Use regular summary for non-PDF, non-financial documents
                    try:
                        summary = query_gemini(f"Please provide a concise summary of this {user.department} department document:\n\n{extracted_text[:2000]}", user.department, 'en')
                        summary_ar = translate_text(summary, 'ar')
                        # Check if we got a generic response
                        if "Hello! I'm your AI assistant" in summary or "How can I assist you today" in summary:
                            raise Exception("Got generic response from Gemini")
                    except Exception as e:
                        logger.error(f"Gemini summary error: {str(e)}")
                        # Fallback to local summary with both languages
                        summary = get_document_summary(extracted_text)
                        if not summary or "Hello! I'm your AI assistant" in summary or len(summary.strip()) < 50:
                            # Create a meaningful summary from the document content
                            words = extracted_text.split()
                            word_count = len(words)
                            # Get first few sentences or key phrases
                            sentences = extracted_text.split('.')[:3]
                            key_sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
                            key_content = '. '.join(key_sentences[:2])
                            if key_content:
                                summary = f"Document Summary: This {user.department} department document ({word_count} words) contains information about: {key_content}..."
                            else:
                                summary = f"Document Summary: This {user.department} department document contains {word_count} words of financial and policy information. Key topics include: {', '.join(words[:15])}..."
                        
                        # Translate English summary to Arabic
                        try:
                            summary_ar = translate_text(summary, 'ar')
                        except:
                            summary_ar = f"ملخص المستند: تم تحليل مستند من قسم {user.department} بنجاح. يحتوي على معلومات مهمة حول العمليات المالية والسياسات."
                
                # Update document with summaries
                result.summary = summary
                result.summary_ar = summary_ar
                db.session.commit()
                
                # Apply sensitive data masking only to document summaries (not chat)
                masked_summary = apply_sensitive_data_masking(summary, user.department) if summary else None
                masked_summary_ar = apply_sensitive_data_masking(summary_ar, user.department) if summary_ar else None
                
                # Debug logging
                logger.info(f"Summary generated - English: {bool(summary)}, Arabic: {bool(summary_ar)}")
                logger.info(f"English summary preview: {summary[:100] if summary else 'None'}...")
                logger.info(f"Arabic summary preview: {summary_ar[:100] if summary_ar else 'None'}...")
                logger.info(f"Arabic summary length: {len(summary_ar) if summary_ar else 0}")
                logger.info(f"Arabic summary type: {type(summary_ar)}")
                logger.info(f"Sensitive data masking applied to document summary: {should_mask_for_user(user.department)}")
                
                flash(f'File uploaded successfully! Document ID: {result.id}', 'success')
                return render_template('upload_success.html', 
                                     document_id=result.id,
                                     summary=masked_summary,
                                     summary_ar=masked_summary_ar,
                                     filename=filename,
                                     user_department=user.department,
                                     masking_info=get_masking_info(user.department))
                
            except Exception as e:
                logger.error(f"Error processing file {filename}: {str(e)}")
                flash(f'Error processing file: {str(e)}', 'error')
                os.remove(filepath)
                return redirect(request.url)
        else:
            flash('Invalid file type. Allowed types: PDF, DOCX, DOC, PNG, JPG, JPEG, TIFF', 'error')
    
    return render_template('upload.html')


@app.route('/reingest-document', methods=['POST'])
@login_required
def reingest_document():
    """Re-ingest a document that failed to generate summaries"""
    try:
        data = request.get_json()
        document_id = data.get('document_id')
        user_document_type = data.get('document_type', '').strip()
        
        if not document_id:
            return jsonify({"success": False, "error": "Document ID is required"}), 400
        
        # Get the document from database
        document = Document.query.get(document_id)
        if not document:
            return jsonify({"success": False, "error": "Document not found"}), 404
        
        # Check if user has permission to re-ingest this document
        user = get_current_user()
        if document.department != user.department:
            return jsonify({"success": False, "error": "Access denied"}), 403
        
        # Get the file path
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], document.filename)
        
        if not os.path.exists(filepath):
            return jsonify({"success": False, "error": "Document file not found"}), 404
        
        # Re-extract text from file
        extracted_text = extract_text_from_file(filepath)
        
        if not extracted_text.strip():
            return jsonify({"success": False, "error": "No text could be extracted from the file"}), 400
        
        # Determine document type: user-specified > existing > auto-detected
        if user_document_type:
            # Try to match user input to financial document types
            matched_type = match_document_type(user_document_type)
            if matched_type:
                financial_doc_type = matched_type
                logger.info(f"Re-ingestion: User specified document type '{user_document_type}' matched to '{matched_type}'")
            else:
                # Use user input as-is if no match found
                financial_doc_type = user_document_type
                logger.info(f"Re-ingestion: User specified document type '{user_document_type}' (not in financial types)")
        elif document.document_type:
            # Use existing document type
            financial_doc_type = document.document_type
            logger.info(f"Re-ingestion: Using existing document type '{financial_doc_type}'")
        else:
            # Auto-detect document type
            financial_doc_type = detect_financial_document_type(document.filename, extracted_text)
            logger.info(f"Re-ingestion: Auto-detected document type: {financial_doc_type}")
        
        # Generate summaries based on document type
        summary_en = None
        summary_ar = None
        
        # Try RAG system first for document summarization
        if rag_system and rag_system.is_ready():
            try:
                # Use RAG system to generate summary using the appropriate prompt template
                if is_financial_document_type(financial_doc_type):
                    # Use financial document analysis prompt
                    prompt = format_prompt_template(
                        get_prompt_template(financial_doc_type, "financial"),
                        document_content=extracted_text[:2000]
                    )
                else:
                    # Use general document analysis prompt
                    prompt = format_prompt_template(
                        get_prompt_template(financial_doc_type, "general"),
                        document_content=extracted_text[:2000]
                    )
                
                rag_summary, rag_summary_en = query_rag(prompt, 'en', user.department)
                # Translate English summary to Arabic instead of generating separately
                rag_summary_ar = translate_text(rag_summary, 'ar')
                
                if rag_summary and not rag_summary.startswith("RAG system not") and len(rag_summary.strip()) > 50:
                    summary_en = rag_summary
                    summary_ar = rag_summary_ar
                    logger.info(f"Re-generated RAG-based summary for: {document.filename} (type: {financial_doc_type})")
                else:
                    raise Exception("RAG system returned invalid response")
            except Exception as e:
                logger.warning(f"RAG summarization failed during re-ingestion: {str(e)}, falling back to structured analysis")
                # Fallback to structured analysis
                summary_en = None
                summary_ar = None
        else:
            logger.info("RAG system not ready during re-ingestion, using structured analysis")
            summary_en = None
            summary_ar = None
        
        # Fallback to structured analysis if RAG didn't work
        if not summary_en:
            if is_financial_document_type(financial_doc_type):
                # Use financial document analysis for financial documents
                try:
                    summary_en = analyze_financial_document(extracted_text, user.department, 'en')
                    summary_ar = translate_text(summary_en, 'ar')
                    logger.info(f"Re-generated financial document analysis for {financial_doc_type}: {document.filename}")
                except Exception as e:
                    logger.error(f"Financial document analysis error during re-ingestion: {str(e)}")
                    # Fallback to structured analysis
                    try:
                        summary_en = generate_structured_summary(extracted_text, user.department, 'en')
                        summary_ar = translate_text(summary_en, 'ar')
                        logger.info(f"Fallback to structured summary during re-ingestion: {document.filename}")
                    except Exception as e2:
                        logger.error(f"Structured analysis fallback error during re-ingestion: {str(e2)}")
                        summary_en = get_document_summary(extracted_text)
                        if not summary_en or "Hello! I'm your AI assistant" in summary_en or len(summary_en.strip()) < 50:
                            words = extracted_text.split()
                            word_count = len(words)
                            sentences = extracted_text.split('.')[:3]
                            key_sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
                            key_content = '. '.join(key_sentences[:2])
                            if key_content:
                                summary_en = f"Financial Document Summary: This {user.department} department financial document ({word_count} words) contains information about: {key_content}..."
                            else:
                                summary_en = f"Financial Document Summary: This {user.department} department financial document contains {word_count} words of financial information. Key topics include: {', '.join(words[:15])}..."
                        
                        # Translate English summary to Arabic
                        try:
                            summary_ar = translate_text(summary_en, 'ar')
                        except:
                            summary_ar = f"ملخص المستند المالي: تم تحليل مستند مالي من قسم {user.department} بنجاح. يحتوي على معلومات مهمة حول العمليات المالية."
            else:
                # Use structured analysis for non-financial documents
                try:
                    summary_en = generate_structured_summary(extracted_text, user.department, 'en')
                    summary_ar = translate_text(summary_en, 'ar')
                    logger.info(f"Re-generated structured summary for non-financial document: {document.filename}")
                except Exception as e:
                    logger.error(f"Structured analysis error during re-ingestion: {str(e)}")
                    # Fallback to regular summary
                    summary_en = get_document_summary(extracted_text)
                    if not summary_en or "Hello! I'm your AI assistant" in summary_en or len(summary_en.strip()) < 50:
                        words = extracted_text.split()
                        word_count = len(words)
                        sentences = extracted_text.split('.')[:3]
                        key_sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
                        key_content = '. '.join(key_sentences[:2])
                        if key_content:
                            summary_en = f"Document Summary: This {user.department} department document ({word_count} words) contains information about: {key_content}..."
                        else:
                            summary_en = f"Document Summary: This {user.department} department document contains {word_count} words of information. Key topics include: {', '.join(words[:15])}..."
                    
                    # Translate English summary to Arabic
                    try:
                        summary_ar = translate_text(summary_en, 'ar')
                    except:
                        summary_ar = f"ملخص المستند: تم تحليل مستند من قسم {user.department} بنجاح. يحتوي على معلومات مهمة."
        elif is_pdf_document(document.filename):
            # Use structured analysis for non-financial PDF documents
            try:
                summary_en = generate_structured_summary(extracted_text, user.department, 'en')
                summary_ar = translate_text(summary_en, 'ar')
                logger.info(f"Re-generated structured summary for PDF: {document.filename}")
            except Exception as e:
                logger.error(f"Structured analysis error during re-ingestion: {str(e)}")
                summary_en = get_document_summary(extracted_text)
                if not summary_en or len(summary_en.strip()) < 50:
                    words = extracted_text.split()
                    word_count = len(words)
                    sentences = extracted_text.split('.')[:3]
                    key_sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
                    key_content = '. '.join(key_sentences[:2])
                    if key_content:
                        summary_en = f"Document Summary: This {user.department} department document ({word_count} words) contains information about: {key_content}..."
                    else:
                        summary_en = f"Document Summary: This {user.department} department document contains {word_count} words of financial and policy information. Key topics include: {', '.join(words[:15])}..."
                
                # Translate English summary to Arabic
                try:
                    summary_ar = translate_text(summary_en, 'ar')
                except:
                    summary_ar = f"ملخص المستند: تم تحليل مستند من قسم {user.department} بنجاح. يحتوي على معلومات مهمة حول العمليات المالية والسياسات."
        else:
            # Use regular summary for non-PDF, non-financial documents
            try:
                summary_en = query_gemini(f"Please provide a concise summary of this {user.department} department document:\n\n{extracted_text[:2000]}", user.department, 'en')
                summary_ar = translate_text(summary_en, 'ar')
                # Check if we got a generic response
                if "Hello! I'm your AI assistant" in summary_en or "How can I assist you today" in summary_en:
                    raise Exception("Got generic response from Gemini")
                logger.info(f"Re-generated regular summary: {document.filename}")
            except Exception as e:
                logger.error(f"Gemini summary error during re-ingestion: {str(e)}")
                summary_en = get_document_summary(extracted_text)
                if not summary_en or "Hello! I'm your AI assistant" in summary_en or len(summary_en.strip()) < 50:
                    words = extracted_text.split()
                    word_count = len(words)
                    sentences = extracted_text.split('.')[:3]
                    key_sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
                    key_content = '. '.join(key_sentences[:2])
                    if key_content:
                        summary_en = f"Document Summary: This {user.department} department document ({word_count} words) contains information about: {key_content}..."
                    else:
                        summary_en = f"Document Summary: This {user.department} department document contains {word_count} words of financial and policy information. Key topics include: {', '.join(words[:15])}..."
                
                # Translate English summary to Arabic
                try:
                    summary_ar = translate_text(summary_en, 'ar')
                except:
                    summary_ar = f"ملخص المستند: تم تحليل مستند من قسم {user.department} بنجاح. يحتوي على معلومات مهمة حول العمليات المالية والسياسات."
        
        # Update document with new summaries
        document.summary = summary_en
        document.summary_ar = summary_ar
        document.document_type = financial_doc_type
        db.session.commit()
        
        logger.info(f"Successfully re-ingested document {document.filename} with ID {document_id}")
        
        return jsonify({
            "success": True, 
            "message": "Document re-ingested successfully",
            "has_summary": bool(summary_en),
            "has_summary_ar": bool(summary_ar)
        })
        
    except Exception as e:
        logger.error(f"Error re-ingesting document: {str(e)}")
        return jsonify({"success": False, "error": f"Internal server error: {str(e)}"}), 500


@app.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    user = get_current_user()
    
    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        language = request.form.get('language', 'en')
        
        if message:
            # Save user message to database
            user_message = ChatMessage(
                user_id=user.id,
                type='user',
                content=message,
                language=language,
                department=user.department
            )
            db.session.add(user_message)
            db.session.commit()
            
            # Try FAQ service first, then RAG system, then local search, then fallbacks
            response = None
            
            # Try FAQ service first - highest priority for CBO-specific questions
            try:
                faq_service = get_faq_service()
                if faq_service.is_loaded():
                    faq_match = faq_service.find_best_match(message, threshold=0.5)
                    if faq_match:
                        faq_question, faq_answer = faq_match
                        response = faq_answer
                        logger.info(f"Using FAQ response for query: '{message}' -> '{faq_question}'")
            except Exception as e:
                logger.error(f"FAQ service error: {str(e)}")
            
            # Try RAG system if FAQ didn't provide a response
            if not response and rag_system and rag_system.is_ready():
                try:
                    # Use the RAG prompt template for context-based answers
                    rag_response, rag_response_en = query_rag(message, language, user.department)
                    if rag_response and rag_response.strip() and not rag_response.startswith("RAG system not"):
                        response = rag_response
                        logger.info(f"Using RAG response for query: '{message}'")
                except Exception as e:
                    logger.error(f"RAG query error: {str(e)}")
            
            # If RAG didn't provide a good response, try local search
            if not response:
                local_results = search_documents(message, user.department)
                if local_results and local_results[0]['score'] >= 0.3:
                    response = format_local_response(local_results)
                    logger.info(f"Using local search results for query: '{message}'")
            
            # If still no response, use fallbacks
            if not response:
                # Use Gemini fallback for general questions
                try:
                    response = query_gemini(message, user.department, language)
                    # Check if we got a generic response from Gemini
                    if "Hello! I'm your AI assistant" in response or "How can I assist you today" in response:
                        raise Exception("Got generic response from Gemini")
                except Exception as e:
                    logger.error(f"Gemini API error: {str(e)}")
                    # Use difflib as fallback for simple questions
                    try:
                        response = get_difflib_response(message, user.department, language)
                        logger.info(f"Using difflib fallback for query: '{message}'")
                    except Exception as difflib_error:
                        logger.error(f"Difflib fallback error: {str(difflib_error)}")
                        # Final fallback - provide department-specific helpful responses
                        if language == 'ar':
                            if "oman central bank" in message.lower() or "البنك المركزي العماني" in message.lower():
                                response = f"البنك المركزي العماني هو البنك المركزي لسلطنة عمان، تأسس في عام 1974. يقع مقره الرئيسي في مسقط ويدير السياسة النقدية للبلاد. في قسم {user.department}، نركز على {get_department_focus_arabic(user.department)}. كيف يمكنني مساعدتك أكثر؟"
                            elif "finance report" in message.lower() or "تقرير مالي" in message.lower():
                                response = f"تقرير مالي 2023: في قسم {user.department}، نركز على {get_department_focus_arabic(user.department)}. يمكنني مساعدتك في تحليل التقارير المالية والميزانيات والتقارير المحاسبية. ما هو السؤال المحدد الذي لديك حول التقرير المالي؟"
                            else:
                                response = f"مرحباً! أنا مساعدك الذكي في قسم {user.department} في البنك المركزي العماني. أسعد لمساعدتك في أي أسئلة لديك حول عملك أو شؤون القسم. كيف يمكنني مساعدتك اليوم؟"
                        else:
                            if "oman central bank" in message.lower():
                                response = f"The Central Bank of Oman (CBO) is the central bank of the Sultanate of Oman, established in 1974. It is headquartered in Muscat and manages the country's monetary policy. In the {user.department} department, we focus on {get_department_focus(user.department)}. How can I assist you further?"
                            elif "finance report" in message.lower():
                                response = f"Finance Report 2023: In the {user.department} department, we focus on {get_department_focus(user.department)}. I can help you analyze financial reports, budgets, and accounting statements. What specific question do you have about the finance report?"
                            else:
                                response = f"Hello! I'm your AI assistant for the {user.department} department at Oman Central Bank. I'm here to help you with any questions about your work or department matters. How can I assist you today?"
            
            # Save assistant response to database (no masking for chat)
            assistant_message = ChatMessage(
                user_id=user.id,
                type='assistant',
                content=response,
                language=language,
                department=user.department
            )
            db.session.add(assistant_message)
            db.session.commit()
    
    # Get recent messages for this user
    recent_messages = ChatMessage.query.filter_by(user_id=user.id).order_by(ChatMessage.timestamp.desc()).limit(20).all()
    
    # Reverse to show oldest first
    messages = list(reversed(recent_messages))
    
    return render_template('chat.html', messages=messages)

@app.route('/documents')
@login_required
def documents():
    user = get_current_user()
    if not user:
        flash('User session expired. Please login again.', 'error')
        return redirect(url_for('login'))
    
    # Get all documents for user's department
    docs = Document.query.filter_by(department=user.department).order_by(Document.upload_date.desc()).all()
    
    return render_template('documents.html', documents=docs, user=user)

@app.route('/translate', methods=['POST'])
@login_required
def translate():
    data = request.get_json()
    text = data.get('text', '')
    target_language = data.get('language', 'ar')
    
    if text:
        try:
            translated = translate_text(text, target_language)
            return jsonify({'translated': translated})
        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return jsonify({'error': 'Translation failed'}), 500
    
    return jsonify({'error': 'No text provided'}), 400

@app.route('/rag/status')
@login_required
def rag_status():
    """Get RAG system status"""
    try:
        if rag_system:
            stats = rag_system.get_stats()
            return jsonify({
                'status': 'success',
                'rag_ready': rag_system.is_ready(),
                'stats': stats
            })
        else:
            return jsonify({
                'status': 'error',
                'rag_ready': False,
                'message': 'RAG system not initialized'
            })
    except Exception as e:
        logger.error(f"Error getting RAG status: {str(e)}")
        return jsonify({
            'status': 'error',
            'rag_ready': False,
            'message': str(e)
        }), 500

@app.route('/rag/init', methods=['POST'])
@login_required
def rag_init():
    """Manually initialize RAG system"""
    try:
        if not RAG_AVAILABLE:
            return jsonify({
                'status': 'error',
                'message': 'RAG integration not available - install required packages'
            }), 400
        
        # initialize_rag_background()  # removed: not defined; manual init via /rag/init if needed
        
        if rag_system and rag_system.is_ready():
            return jsonify({
                'status': 'success',
                'message': 'RAG system initialized successfully'
            })
        else:
            return jsonify({
                'status': 'warning',
                'message': 'RAG system initialization attempted but not ready'
            })
        
    except Exception as e:
        logger.error(f"Error initializing RAG system: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/rag/ingest', methods=['POST'])
@login_required
def rag_ingest():
    """Manually ingest documents into RAG system"""
    try:
        if not RAG_AVAILABLE:
            return jsonify({
                'status': 'error',
                'message': 'RAG integration not available'
            }), 400
        
        user = get_current_user()
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'User session expired'
            }), 401
        
        docs = Document.query.filter_by(department=user.department).all()
        
        if not docs:
            return jsonify({
                'status': 'error',
                'message': 'No documents found in your department'
            }), 400
        
        if not rag_system:
            return jsonify({
                'status': 'error',
                'message': 'RAG system not initialized. Try /rag/init first.'
            }), 500
        
        # Ingest each document
        ingested_count = 0
        for doc in docs:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], doc.filename)
            if os.path.exists(file_path):
                success = add_document_to_rag(file_path, doc.filename, doc.department)
                if success:
                    ingested_count += 1
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully ingested {ingested_count} documents into RAG system',
            'ingested_count': ingested_count,
            'total_documents': len(docs)
        })
        
    except Exception as e:
        logger.error(f"Error ingesting documents: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def is_department_query(query, department):
    """Check if query is related to the user's department"""
    # Always allow queries - let the search handle relevance
    return True

def format_local_response(results):
    """Format local search results into a readable response"""
    if not results:
        return "No relevant documents found in your department."
    
    response = "Based on your department documents:\n\n"
    for i, result in enumerate(results[:3], 1):  # Show top 3 results
        response += f"{i}. {result['filename']} (Relevance: {result['score']:.2f})\n"
        response += f"   {result['excerpt'][:200]}...\n\n"
    
    return response

# ---------------- Voice Recording API ----------------
@app.route('/voice/start', methods=['POST'])
@login_required
def voice_start():
    session_id = voice_service.begin_session(user_id=str(session['user_id']))
    return jsonify({'session_id': session_id})


@app.route('/voice/chunk', methods=['POST'])
@login_required
def voice_chunk():
    session_id = request.form.get('session_id')
    sample_rate = request.form.get('sample_rate_hz', type=int)
    blob = request.files.get('audio')
    if not session_id or not blob:
        return jsonify({'error': 'session_id and audio required'}), 400
    try:
        voice_service.accept_audio_chunk(session_id, blob.read(), sample_rate_hz=sample_rate)
        return jsonify({'ok': True})
    except Exception as e:
        logger.error(f"voice_chunk error: {e}")
        return jsonify({'error': str(e)}), 400


@app.route('/voice/transcript', methods=['GET'])
@login_required
def voice_transcript():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'error': 'session_id required'}), 400
    try:
        transcript = voice_service.get_live_transcript(session_id)
        return jsonify({'transcript': transcript})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/voice/waveform', methods=['GET'])
@login_required
def voice_waveform():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'error': 'session_id required'}), 400
    try:
        points = voice_service.get_waveform_points(session_id, max_points=200)
        return jsonify({'points': points})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/voice/finalize', methods=['POST'])
@login_required
def voice_finalize():
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({'error': 'session_id required'}), 400
    try:
        # IMPORTANT: capture audio BEFORE finalizing (finalize closes/removes session)
        try:
            audio_bytes = voice_service.get_best_effort_audio(session_id)
        except Exception:
            audio_bytes = b""

        # Now finalize to flush metadata and clean up
        meta = voice_service.finalize_session(session_id)
        if audio_bytes and 'WHISPER_SERVICE' in globals() and WHISPER_SERVICE is not None:
            try:
                result = WHISPER_SERVICE.transcribe_bytes(audio_bytes, file_suffix='.webm')
                meta['transcript'] = result.get('text', '') or meta.get('transcript', '')
                meta['whisper_language'] = result.get('language', '')
                meta['whisper_load_time_s'] = result.get('load_time_s', '')
                meta['whisper_infer_time_s'] = result.get('infer_time_s', '')
                # Log transcript and performance
                _t = meta.get('transcript', '')
                _preview = (_t[:200] + '...') if len(_t) > 200 else _t
                logger.info(f"Whisper transcript ({len(_t)} chars): {_preview}")
                logger.info(
                    f"Whisper perf load={meta.get('whisper_load_time_s','')}s infer={meta.get('whisper_infer_time_s','')}s lang={meta.get('whisper_language','')}"
                )
                meta['whisper_used'] = True
            except Exception as e:
                logger.warning(f"Whisper transcription failed: {e}")
                meta['whisper_used'] = False
        else:
            meta['whisper_used'] = False
            meta['whisper_reason'] = 'no_audio_bytes' if not audio_bytes else 'service_unavailable'
        return jsonify(meta)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/voice/transcribe', methods=['POST'])
@login_required
def voice_transcribe_full():
    """Accept a full audio blob and run Whisper once, no chunking."""
    blob = request.files.get('audio')
    sample_rate = request.form.get('sample_rate_hz', type=int)
    if not blob:
        return jsonify({'error': 'audio file required'}), 400
    audio_bytes = blob.read()
    resp = {
        'whisper_used': False,
        'transcript': '',
        'whisper_language': '',
        'whisper_load_time_s': '',
        'whisper_infer_time_s': '',
    }
    try:
        if 'WHISPER_SERVICE' in globals() and WHISPER_SERVICE is not None:
            # Infer file suffix from filename
            filename = getattr(blob, 'filename', '') or 'audio.webm'
            suffix = '.' + filename.split('.')[-1].lower() if '.' in filename else '.webm'
            result = WHISPER_SERVICE.transcribe_bytes(audio_bytes, file_suffix=suffix)
            resp['transcript'] = result.get('text', '')
            resp['whisper_language'] = result.get('language', '')
            resp['whisper_load_time_s'] = result.get('load_time_s', '')
            resp['whisper_infer_time_s'] = result.get('infer_time_s', '')
            resp['whisper_used'] = True
            _t = resp['transcript']
            _preview = (_t[:200] + '...') if len(_t) > 200 else _t
            logger.info(f"Whisper transcript (full upload, {len(_t)} chars): {_preview}")
        else:
            resp['whisper_reason'] = 'service_unavailable'
    except Exception as e:
        logger.warning(f"Whisper full transcription failed: {e}")
        resp['whisper_reason'] = str(e)
    return jsonify(resp)


@app.route('/voice/cancel', methods=['POST'])
@login_required
def voice_cancel():
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({'error': 'session_id required'}), 400
    try:
        voice_service.cancel_session(session_id)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Starting Oman Central Bank Document Analyzer")
    print("="*60)
    print(f"📁 Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"🔧 Debug mode: {app.debug}")
    print(f"🤖 RAG enabled: {RAG_ENABLED}")
    print("="*60)
    print("📝 Core app functionality: Document upload, search, and chat")
    print("📝 AI features: Gemini integration, local search, translation")
    if RAG_ENABLED:
        print("🤖 RAG features: Advanced document-based Q&A")
    print("="*60 + "\n")
    
    # Initialize RAG if enabled
    if RAG_ENABLED:
        initialize_rag_if_enabled()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
