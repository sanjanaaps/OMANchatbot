from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
import os
import sys
from datetime import datetime, timedelta
import markdown

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
# RAG Integration - conditionally loaded based on user choice
# Check environment variable set by startup scripts
RAG_ENABLED = os.getenv('RAG_ENABLED', '1') == '1'  # Default to enabled if not set
RAG_AVAILABLE = False
rag_system = None

# Log RAG status at startup
print(f"[App] RAG_ENABLED={RAG_ENABLED} (from env: {os.getenv('RAG_ENABLED', 'not set')})")

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

# Add markdown filter
@app.template_filter('markdown')
def markdown_filter(text):
    """Convert markdown text to HTML or return HTML as-is"""
    if not text:
        return ""
    
    # Check if text already contains HTML tags
    if '<p>' in text or '<div>' in text or '<br>' in text or '<h1>' in text:
        # Text is already HTML, return as-is
        return text
    
    # Convert markdown to HTML
    md = markdown.Markdown(extensions=['nl2br', 'fenced_code', 'tables', 'codehilite'])
    html = md.convert(text)
    return html

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

# Initialize RAG Integration based on user choice (set by startup_config.py)
def initialize_rag_if_enabled():
    """Initialize RAG Integration system if it was enabled during startup"""
    global RAG_ENABLED, RAG_AVAILABLE, rag_system
    
    print(f"[App] initialize_rag_if_enabled called - RAG_ENABLED={RAG_ENABLED}")
    
    if RAG_ENABLED:
        try:
            from app_lib.rag_integration import (
                initialize_rag_system as _init_rag, 
                get_rag_system as _get_rag, 
                add_document_to_rag as _add_doc, 
                query_rag as _query_rag
            )
            
            # Replace dummy functions with real ones
            globals()['initialize_rag_system'] = _init_rag
            globals()['get_rag_system'] = _get_rag
            globals()['add_document_to_rag'] = _add_doc
            globals()['query_rag'] = _query_rag
            
            RAG_AVAILABLE = True
            logger.info("RAG Integration enabled - initializing...")
            
            # Initialize RAG system without document ingestion (documents will be indexed individually)
            rag_system = initialize_rag_system(app.config['UPLOAD_FOLDER'])
            if rag_system:
                if rag_system.is_ready():
                    logger.info("✅ RAG Integration system initialized successfully")
                else:
                    logger.warning("⚠️ RAG Integration system initialized but not ready - will use Gemini fallback")
            else:
                logger.warning("⚠️ RAG Integration system failed to initialize - will use Gemini fallback")
                
        except Exception as e:
            logger.error(f"Failed to initialize RAG Integration system: {str(e)}")
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
        
        logger.info(f"🔐 Login: {user.username} ({user.department}) - Session started")
        
        flash(f'Welcome back, {user.username}!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    # Log logout information
    username = session.get('username', 'Unknown')
    department = session.get('department', 'Unknown')
    chat_messages_count = len(session.get('chat_messages', []))
    chat_history_count = len(session.get('chat_history', []))
    
    # Clear all session data including chat history
    session.clear()
    
    logger.info(f"🚪 Logout: {username} ({department}) - Cleared {chat_messages_count} messages and {chat_history_count} chat histories")
    
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
                        logger.info(f"🔧 RAG: Attempting to ingest document into RAG system: {filename}")
                        success = add_document_to_rag(filepath, filename, user.department)
                        if success:
                            logger.info(f"✅ RAG: Document {filename} successfully added to RAG system")
                        else:
                            logger.warning(f"❌ RAG: Failed to add document {filename} to RAG system")
                    else:
                        logger.info(f"⚠️ RAG: System not ready, document {filename} saved but not indexed")
                except Exception as e:
                    logger.warning(f"❌ RAG: System error (non-critical): {str(e)}")
                
                # Generate appropriate analysis based on detected document type
                summary_ar = None  # Initialize Arabic summary
                
                # Use RAG system for document summarization (primary method)
                summary = None
                summary_ar = None
                
                logger.info(f"📄 Starting document analysis for: {filename}")
                logger.info(f"📊 Document type: {financial_doc_type}")
                logger.info(f"📏 Document size: {len(extracted_text)} characters")
                logger.info(f"🏢 Department: {user.department}")
                
                if rag_system and rag_system.is_ready():
                    extracted_text = None
                    uploaded_file = None
                    try:
                        # Use RAG system to generate summary using the appropriate prompt template
                        logger.info(f"🤖 RAG system is ready, generating summary...")
                        
                        if is_financial_document_type(financial_doc_type):
                            # Use financial document analysis prompt
                            prompt_template = get_prompt_template(financial_doc_type, "financial")
                            logger.info(f"📋 Using financial document prompt template for: {financial_doc_type}")
                            prompt = format_prompt_template(
                                prompt_template,
                                document_content=extracted_text[:2000]
                            )
                        else:
                            # Use general document analysis prompt
                            prompt_template = get_prompt_template(financial_doc_type, "general")
                            logger.info(f"📋 Using general document prompt template for: {financial_doc_type}")
                            prompt = format_prompt_template(
                                prompt_template,
                                document_content=extracted_text[:2000]
                            )
                        
                        logger.info(f"🔍 Sending prompt to RAG system (length: {len(prompt)} chars)")
                        logger.debug(f"📝 Prompt preview: {prompt[:200]}...")
                        
                        rag_summary, rag_summary_en = query_rag(prompt, 'en', user.department)
                        logger.info(f"📤 RAG system response received (length: {len(rag_summary) if rag_summary else 0} chars)")
                        if not response:
                            logger.info(f"🌐 Trying Gemini API fallback for: '{message[:50]}{'...' if len(message) > 50 else ''}'")
                        # Use Gemini fallback for general questions
                        try:
                            response = query_gemini(message, user.department, language, extracted_text if extracted_text else "")
                            # Check if we got a generic response from Gemini
                            if "Hello! I'm your AI assistant" in response or "How can I assist you today" in response:
                                raise Exception("Got generic response from Gemini")
                            response_source = "Gemini API"
                            logger.info(f"🤖 Gemini Response: Generated AI response for query")
                            logger.debug(f"Gemini Response length: {len(response)} characters")
                        except Exception as e:
                            logger.error(f"❌ Gemini API error: {str(e)}")
                            logger.info(f"⚠️ Gemini failed, trying difflib fallback...")
                            # Use difflib as fallback for simple questions
                            try:
                                response = get_difflib_response(message, user.department, language)
                                response_source = "Difflib Fallback"
                                logger.info(f"🔤 Difflib Response: Pattern matching fallback for query")
                            except Exception as difflib_error:
                                logger.error(f"❌ Difflib fallback error: {str(difflib_error)}")
                                logger.info(f"⚠️ All AI services failed, using hardcoded fallback...")
                                # Final fallback - provide department-specific helpful responses
                                response_source = "Hardcoded Fallback"
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
                                logger.info(f"🔧 Hardcoded Fallback Response: Department-specific template response")
                        
                        # Translate English summary to Arabic instead of generating separately
                        logger.info(f"🌐 Translating summary to Arabic...")
                        rag_summary_ar = translate_text(rag_summary, 'ar')
                        logger.info(f"✅ Arabic translation completed")
                        
                        if rag_summary and not rag_summary.startswith("RAG system not") and len(rag_summary.strip()) > 50:
                            summary = rag_summary
                            summary_ar = rag_summary_ar
                            logger.info(f"✅ SUCCESS: Generated RAG-based summary for: {filename} (type: {financial_doc_type})")
                            logger.info(f"📊 Summary length: EN={len(summary)} chars, AR={len(summary_ar)} chars")
                            logger.debug(f"📝 Summary preview: {summary[:150]}...")
                        else:
                            raise Exception("RAG system returned invalid response")
                    except Exception as e:
                        logger.error(f"❌ RAG summarization failed: {str(e)}")
                        logger.warning(f"⚠️ Structured analysis is disabled, using basic fallback")
                        summary = None
                        summary_ar = None
                else:
                    logger.warning(f"⚠️ RAG system not ready")
                    logger.warning(f"⚠️ Structured analysis is disabled, using basic fallback")
                    summary = None
                    summary_ar = None
                
                # RAG-only mode - no fallback summaries
                if not summary:
                    logger.error(f"❌ RAG system failed to generate summary for: {filename}")
                    logger.warning(f"⚠️ Basic summary fallback is disabled - only RAG summaries are allowed")
                    
                    # Set minimal summary indicating RAG failure
                    summary = f"Document uploaded successfully but RAG summary generation failed. Document type: {financial_doc_type}"
                    summary_ar = f"تم رفع المستند بنجاح ولكن فشل في إنشاء ملخص RAG. نوع المستند: {financial_doc_type}"
                
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
        
        logger.info(f"🔄 Starting document re-ingestion for: {document.filename}")
        logger.info(f"📊 Document type: {financial_doc_type}")
        logger.info(f"📏 Document size: {len(extracted_text)} characters")
        logger.info(f"🏢 Department: {user.department}")
        
        # Try RAG system first for document summarization
        if rag_system and rag_system.is_ready():
            try:
                # Use RAG system to generate summary using the appropriate prompt template
                logger.info(f"🤖 RAG system is ready for re-ingestion, generating summary...")
                
                if is_financial_document_type(financial_doc_type):
                    # Use financial document analysis prompt
                    prompt_template = get_prompt_template(financial_doc_type, "financial")
                    logger.info(f"📋 Using financial document prompt template for re-ingestion: {financial_doc_type}")
                    prompt = format_prompt_template(
                        prompt_template,
                        document_content=extracted_text[:2000]
                    )
                else:
                    # Use general document analysis prompt
                    prompt_template = get_prompt_template(financial_doc_type, "general")
                    logger.info(f"📋 Using general document prompt template for re-ingestion: {financial_doc_type}")
                    prompt = format_prompt_template(
                        prompt_template,
                        document_content=extracted_text[:2000]
                    )
                
                logger.info(f"🔍 Sending prompt to RAG system for re-ingestion (length: {len(prompt)} chars)")
                logger.debug(f"📝 Re-ingestion prompt preview: {prompt[:200]}...")
                
                rag_summary, rag_summary_en = query_rag(prompt, 'en', user.department)
                logger.info(f"📤 RAG system response received for re-ingestion (length: {len(rag_summary) if rag_summary else 0} chars)")
                
                # Translate English summary to Arabic instead of generating separately
                logger.info(f"🌐 Translating re-ingestion summary to Arabic...")
                rag_summary_ar = translate_text(rag_summary, 'ar')
                logger.info(f"✅ Arabic translation completed for re-ingestion")
                
                if rag_summary and not rag_summary.startswith("RAG system not") and len(rag_summary.strip()) > 50:
                    summary_en = rag_summary
                    summary_ar = rag_summary_ar
                    logger.info(f"✅ SUCCESS: Re-generated RAG-based summary for: {document.filename} (type: {financial_doc_type})")
                    logger.info(f"📊 Re-ingestion summary length: EN={len(summary_en)} chars, AR={len(summary_ar)} chars")
                    logger.debug(f"📝 Re-ingestion summary preview: {summary_en[:150]}...")
                else:
                    raise Exception("RAG system returned invalid response")
            except Exception as e:
                logger.error(f"❌ RAG summarization failed during re-ingestion: {str(e)}")
                logger.warning(f"⚠️ Structured analysis is disabled, using basic fallback for re-ingestion")
                # Fallback to basic summary
                summary_en = None
                summary_ar = None
        else:
            logger.warning(f"⚠️ RAG system not ready during re-ingestion")
            logger.warning(f"⚠️ Structured analysis is disabled, using basic fallback for re-ingestion")
            summary_en = None
            summary_ar = None
        
        # RAG-only mode - no fallback summaries
        if not summary_en:
            logger.error(f"❌ RAG system failed to generate summary for re-ingestion: {document.filename}")
            logger.warning(f"⚠️ Basic summary fallback is disabled - only RAG summaries are allowed")
            
            # Set minimal summary indicating RAG failure
            summary_en = f"Document re-ingested successfully but RAG summary generation failed. Document type: {financial_doc_type}"
            summary_ar = f"تم إعادة معالجة المستند بنجاح ولكن فشل في إنشاء ملخص RAG. نوع المستند: {financial_doc_type}"
        # All other cases are handled by the basic fallback above
        
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
    response = None
    response_source = None
    uploaded_file = None
    extracted_text = None

    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        language = request.form.get('language', 'en')
        
        # Save user message to session
        user_message_data = {
            'id': f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            'chat_id': session.get('current_chat_id'),
            'type': 'user',
            'content': message,
            'language': language,
            'timestamp': datetime.now().isoformat()
        }
        
        # Initialize chat messages list if not exists
        if 'chat_messages' not in session:
            session['chat_messages'] = []
        
        # Add user message to session
        session['chat_messages'].append(user_message_data)
        session.modified = True
        
        # Handle file upload if present
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Update user message with file information
                session['chat_messages'][-1]['content'] = f"Question: {message}\n\nAttached document: {filename}"
                session.modified = True
                # Extract text from uploaded file
                try:
                    extracted_text = extract_text_from_file(filepath)
                    if extracted_text.strip():
                        uploaded_file = filename
                    else:
                        flash('No text could be extracted from the uploaded file', 'error')
                        os.remove(filepath)
                        extracted_text = None
                except Exception as e:
                    logger.error(f"Error processing uploaded file {filename}: {str(e)}")
                    flash(f'Error processing uploaded file: {str(e)}', 'error')
                    os.remove(filepath)
                    extracted_text = None
            elif file and file.filename:
                flash('Invalid file type. Allowed types: PDF, DOCX, DOC, PNG, JPG, JPEG, TIFF', 'error')

        # ...existing code...

        # If we have extracted text, try Gemini first with the document context
        if extracted_text and not response:
            logger.info(f"🌐 Trying Gemini API with document context for: '{message[:50]}{'...' if len(message) > 50 else ''}'")
            try:
                response = query_gemini(message, user.department, language, extracted_text)
                if "Hello! I'm your AI assistant" in response or "How can I assist you today" in response:
                    raise Exception("Got generic response from Gemini")
                response_source = "Gemini API with Document"
                logger.info(f"🤖 Gemini Response: Generated AI response with document context")
                logger.debug(f"Gemini Response length: {len(response)} characters")
            except Exception as e:
                logger.error(f"❌ Gemini API error: {str(e)}")
                logger.info(f"⚠️ Gemini failed, trying difflib fallback...")
                try:
                    response = get_difflib_response(message, user.department, language)
                    response_source = "Difflib Fallback"
                    logger.info(f"🔤 Difflib Response: Pattern matching fallback for query")
                except Exception as difflib_error:
                    logger.error(f"❌ Difflib fallback error: {str(difflib_error)}")
                    logger.info(f"⚠️ All AI services failed, using hardcoded fallback...")
                    response_source = "Hardcoded Fallback"
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
                    logger.info(f"🔧 Hardcoded Fallback Response: Department-specific template response")
            
            # Add to chat history if this is a new conversation
            # Ensure chat_id is defined and consistent
            if 'current_chat_id' not in session or not session['current_chat_id']:
                session['current_chat_id'] = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user.id}"
            chat_id = session['current_chat_id']
            chat_exists = any(chat['id'] == chat_id for chat in session.get('chat_history', []))
            if not chat_exists:
                chat_summary = message[:50] + "..." if len(message) > 50 else message
                session.setdefault('chat_history', []).append({
                    'id': chat_id,
                    'summary': chat_summary,
                    'timestamp': datetime.now().isoformat(),
                    'language': language
                })
            
            # Try FAQ service first, then RAG system, then local search, then fallbacks
            response = None
            response_source = None
            
            # Log the incoming question
            logger.info(f"📝 Question from {user.username} ({user.department}): '{message[:100]}{'...' if len(message) > 100 else ''}'")
            if uploaded_file:
                logger.info(f"📎 File attached: {uploaded_file}")
            
            # Try FAQ service first - highest priority for CBO-specific questions
            try:
                faq_service = get_faq_service()
                if faq_service.is_loaded():
                    faq_match = faq_service.find_best_match(message, threshold=0.5)
                    if faq_match:
                        faq_question, faq_answer = faq_match
                        response = faq_answer
                        response_source = "FAQ Service"
                        logger.info(f"✅ FAQ Response: '{message[:50]}{'...' if len(message) > 50 else ''}' -> '{faq_question[:50]}{'...' if len(faq_question) > 50 else ''}'")
            except Exception as e:
                logger.error(f"❌ FAQ service error: {str(e)}")
            
            # Try RAG system if FAQ didn't provide a response
            if not response and rag_system and rag_system.is_ready():
                try:
                    # Use the RAG prompt template for context-based answers
                    rag_response, rag_response_en = query_rag(message, language, user.department)
                    if rag_response and rag_response.strip() and not rag_response.startswith("RAG system not"):
                        response = rag_response
                        response_source = "RAG System (Integration)"
                        logger.info(f"🤖 RAG Response: '{message[:50]}{'...' if len(message) > 50 else ''}' -> Generated from document context")
                        logger.debug(f"RAG Response length: {len(rag_response)} characters")
                except Exception as e:
                    logger.error(f"❌ RAG query error: {str(e)}")
                    logger.info(f"⚠️ RAG system failed, trying local search...")
            
            # If RAG didn't provide a good response, try local search
            if not response:
                logger.info(f"🔍 Trying local search for: '{message[:50]}{'...' if len(message) > 50 else ''}'")
                local_results = search_documents(message, user.department)
                if local_results and local_results[0]['score'] >= 0.3:
                    response = format_local_response(local_results)
                    response_source = "Local Document Search"
                    logger.info(f"📄 Local Search Response: Found {len(local_results)} relevant documents (top score: {local_results[0]['score']:.2f})")
                    logger.debug(f"Top result: {local_results[0]['filename']} - {local_results[0]['excerpt'][:100]}...")
                else:
                    logger.info(f"⚠️ Local search found no relevant documents (threshold: 0.3)")
            
            # If still no response and no extracted text was already tried, try Gemini without document context
            if not response and not extracted_text:
                logger.info(f"🌐 Trying Gemini API fallback for: '{message[:50]}{'...' if len(message) > 50 else ''}'")
                try:
                    response = query_gemini(message, user.department, language, "")
                    if "Hello! I'm your AI assistant" in response or "How can I assist you today" in response:
                        raise Exception("Got generic response from Gemini")
                    response_source = "Gemini API"
                    logger.info(f"🤖 Gemini Response: Generated AI response without document context")
                    logger.debug(f"Gemini Response length: {len(response)} characters")
                except Exception as e:
                    logger.error(f"❌ Gemini API error: {str(e)}")
                    logger.info(f"⚠️ Gemini failed, trying next fallback...")
            
            # If still no response, use difflib fallback
            if not response:
                logger.info(f"🌐 Trying Gemini API fallback for: '{message[:50]}{'...' if len(message) > 50 else ''}'")
                # Use Gemini fallback for general questions
                try:
                    response = query_gemini(message, user.department, language)
                    # Check if we got a generic response from Gemini
                    if "Hello! I'm your AI assistant" in response or "How can I assist you today" in response:
                        raise Exception("Got generic response from Gemini")
                    response_source = "Gemini API"
                    logger.info(f"🤖 Gemini Response: Generated AI response for query")
                    logger.debug(f"Gemini Response length: {len(response)} characters")
                except Exception as e:
                    logger.error(f"❌ Gemini API error: {str(e)}")
                    logger.info(f"⚠️ Gemini failed, trying difflib fallback...")
                    # Use difflib as fallback for simple questions
                    try:
                        response = get_difflib_response(message, user.department, language)
                        response_source = "Difflib Fallback"
                        logger.info(f"🔤 Difflib Response: Pattern matching fallback for query")
                    except Exception as difflib_error:
                        logger.error(f"❌ Difflib fallback error: {str(difflib_error)}")
                        logger.info(f"⚠️ All AI services failed, using hardcoded fallback...")
                        # Final fallback - provide department-specific helpful responses
                        response_source = "Hardcoded Fallback"
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
                        
                        logger.info(f"🔧 Hardcoded Fallback Response: Department-specific template response")
            
            # Log final response summary
            if response:
                logger.info(f"✅ FINAL RESPONSE from {response_source}: {len(response)} characters")
                logger.info(f"📊 Response Source: {response_source}")
                logger.debug(f"Response preview: {response[:200]}{'...' if len(response) > 200 else ''}")
            else:
                logger.error(f"❌ NO RESPONSE GENERATED - All systems failed")
                response = "I apologize, but I'm unable to process your request at the moment. Please try again later."
                response_source = "Error Fallback"
            
            # Save assistant response to session
            assistant_message_data = {
                'id': f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                'chat_id': chat_id,
                'type': 'assistant',
                'content': response,
                'language': language,
                'timestamp': datetime.now().isoformat(),
                'response_source': response_source  # Store response source in session
            }
            session['chat_messages'].append(assistant_message_data)
            
            # Mark session as modified to save changes
            session.modified = True
    
    # Get session-based messages for this user
    session_messages = session.get('chat_messages', [])

    # Fetch available chat days for user's department from DB to show as tabs
    try:
        # Query distinct dates (days) that have chat messages for this department
        user_department = user.department
        days_query = (
            db.session.query(db.func.date(ChatMessage.timestamp).label('day'))
            .filter(ChatMessage.department == user_department)
            .group_by('day')
            .order_by(db.desc('day'))
        )
        chat_days = [r.day.isoformat() for r in days_query.all()]
        logger.info(f"Chat days for department {user_department}: {chat_days}")
    except Exception as e:
        logger.error(f"Error fetching chat days for department {user.department}: {e}")
        chat_days = []
    
    # Convert session messages to the format expected by template
    messages = []
    for msg in session_messages:
        # Create a mock message object with the required attributes
        class SessionMessage:
            def __init__(self, data):
                self.id = data.get('id', '')
                self.type = data.get('type', 'user')
                self.content = data.get('content', '')
                self.timestamp = data.get('timestamp', datetime.now())
                self.language = data.get('language', 'en')
        
        messages.append(SessionMessage(msg))
    
    return render_template('chat.html', messages=messages, chat_days=chat_days)

@app.route('/api/chat-history')
@login_required
def get_chat_history():
    """Get session-based chat history for the current user"""
    user = get_current_user()
    try:
        # Get session-based chat history
        session_chats = session.get('chat_history', [])
        
        logger.info(f"📋 Chat History Request from {user.username} ({user.department}): {len(session_chats)} chats found")
        
        chat_summaries = []
        for chat in session_chats:
            # Create a summary from the first part of the message
            summary = chat['content'][:50] + "..." if len(chat['content']) > 50 else chat['content']
            
            chat_summaries.append({
                'id': chat['id'],
                'summary': summary,
                'timestamp': chat['timestamp'],
                'language': chat.get('language', 'en')
            })
        
        logger.debug(f"Returning {len(chat_summaries)} chat summaries")
        return jsonify({
            'success': True,
            'chats': chat_summaries
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting session chat history for {user.username}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/chat-days')
@login_required
def api_chat_days():
    """Return list of ISO dates (YYYY-MM-DD) that have chat messages for the current user's department."""
    # get_current_user() may raise RuntimeError if called outside of an application
    # context during some tests. Try to call it but fall back to session values when
    # necessary so tests that monkeypatch or set session entries work reliably.
    try:
        user = get_current_user()
    except RuntimeError as e:
        logger.warning(f"get_current_user() raised RuntimeError: {e}; falling back to session")
        user = None

    # Prefer department from user object, fall back to session if available
    user_department = None
    if user and getattr(user, 'department', None):
        user_department = user.department
    else:
        user_department = session.get('department')

    if not user_department:
        logger.warning("API: could not determine user department (no user/session). Returning empty days list")
        return jsonify({'success': True, 'days': []})

    try:
        days_query = (
            db.session.query(db.func.date(ChatMessage.timestamp).label('day'))
            .filter(ChatMessage.department == user_department)
            .group_by('day')
            .order_by(db.desc('day'))
        )
        days = [r.day.isoformat() for r in days_query.all()]
        logger.info(f"API: returning {len(days)} chat days for department {user_department}")
        return jsonify({'success': True, 'days': days})
    except Exception as e:
        # Log the username if available, otherwise log user_department
        uname = getattr(user, 'username', 'unknown') if user else 'unknown'
        logger.error(f"API: error fetching chat days for {uname} (department={user_department}): {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/chat-day/<day>')
@login_required
def api_chat_day_messages(day):
    """Return messages for a given ISO date (YYYY-MM-DD) filtered by current user's department."""
    try:
        user = get_current_user()
    except RuntimeError as e:
        logger.warning(f"get_current_user() raised RuntimeError: {e}; falling back to session")
        user = None

    # Determine department
    if user and getattr(user, 'department', None):
        user_department = user.department
    else:
        user_department = session.get('department')

    if not user_department:
        logger.warning(f"API: could not determine department for day {day}; returning empty message list")
        return jsonify({'success': True, 'messages': []})

    try:
        # Parse day and build datetime range
        day_start = datetime.fromisoformat(day)
        day_end = day_start + timedelta(days=1)

        msgs = (
            ChatMessage.query
            .filter(ChatMessage.department == user_department)
            .filter(ChatMessage.timestamp >= day_start)
            .filter(ChatMessage.timestamp < day_end)
            .order_by(ChatMessage.timestamp.asc())
            .all()
        )

        result = []
        for m in msgs:
            # Normalize user field to a JSON-serializable value.
            user_field = None
            try:
                u = getattr(m, 'user', None)
                # If the stored user is a string (username), use it. If it's a User object, prefer username then id.
                if isinstance(u, str):
                    user_field = u
                elif u is not None:
                    user_field = getattr(u, 'username', None) or getattr(u, 'id', None) or str(u)
            except Exception:
                user_field = None

            result.append({
                'id': m.id,
                # Some ChatMessage models don't have a chat_id field; fall back to message id
                'chat_id': getattr(m, 'chat_id', m.id),
                'type': m.type,
                'content': m.content,
                'timestamp': m.timestamp.isoformat(),
                'user': user_field
            })

        logger.info(f"API: returning {len(result)} messages for {day} (department={user_department})")
        return jsonify({'success': True, 'messages': result})
    except Exception as e:
        uname = getattr(user, 'username', 'unknown') if user else 'unknown'
        logger.error(f"API: error fetching messages for day {day} for {uname} (department={user_department}): {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chat-history/<chat_id>')
@login_required
def get_chat_messages(chat_id):
    """Get messages for a specific session-based chat"""
    try:
        # Get session-based chat history
        session_chats = session.get('chat_history', [])
        
        # Find the specific chat
        target_chat = None
        for chat in session_chats:
            if chat['id'] == chat_id:
                target_chat = chat
                break
        
        if not target_chat:
            return jsonify({
                'success': False,
                'error': 'Chat not found'
            }), 404
        
        # Get session-based messages for this chat
        session_messages = session.get('chat_messages', [])
        message_list = []
        
        for msg in session_messages:
            # Find messages that belong to this chat session
            if msg.get('chat_id') == chat_id:
                message_list.append({
                    'id': msg['id'],
                    'type': msg['type'],
                    'content': msg['content'],
                    'timestamp': msg['timestamp'],
                    'language': msg.get('language', 'en')
                })
        
        return jsonify({
            'success': True,
            'messages': message_list
        })
        
    except Exception as e:
        logger.error(f"Error getting session chat messages: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/chat-history/current')
@login_required
def get_current_chat_messages():
    """Get messages for the current session-based chat"""
    try:
        chat_id = session.get('current_chat_id')
        if not chat_id:
            return jsonify({
                'success': False,
                'error': 'No current chat session'
            }), 404
        session_messages = session.get('chat_messages', [])
        message_list = []
        for msg in session_messages:
            if msg.get('chat_id') == chat_id:
                message_list.append({
                    'id': msg['id'],
                    'type': msg['type'],
                    'content': msg['content'],
                    'timestamp': msg['timestamp'],
                    'language': msg.get('language', 'en')
                })
        return jsonify({
            'success': True,
            'messages': message_list
        })
    except Exception as e:
        logger.error(f"Error getting current session chat messages: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/new-chat', methods=['POST'])
@login_required
def new_chat():
    """Start a new chat session"""
    user = get_current_user()
    try:
        # Clear current chat messages but keep chat history
        previous_messages_count = len(session.get('chat_messages', []))
        if 'chat_messages' in session:
            session['chat_messages'] = []
        
        # Generate new chat ID
        new_chat_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user.id}"
        session['current_chat_id'] = new_chat_id
        
        session.modified = True
        
        logger.info(f"🆕 New Chat Session created for {user.username} ({user.department}): {new_chat_id}")
        logger.info(f"📊 Cleared {previous_messages_count} previous messages")
        
        return jsonify({
            'success': True,
            'message': 'New chat session started',
            'chat_id': new_chat_id
        })
        
    except Exception as e:
        logger.error(f"❌ Error starting new chat for {user.username}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
        logger.info(f"🔧 RAG: Starting bulk ingestion of {len(docs)} documents for department: {user.department}")
        for doc in docs:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], doc.filename)
            if os.path.exists(file_path):
                logger.info(f"🔧 RAG: Ingesting document {doc.filename} from bulk operation")
                success = add_document_to_rag(file_path, doc.filename, doc.department)
                if success:
                    ingested_count += 1
                    logger.info(f"✅ RAG: Successfully ingested {doc.filename} in bulk operation")
                else:
                    logger.warning(f"❌ RAG: Failed to ingest {doc.filename} in bulk operation")
            else:
                logger.warning(f"⚠️ RAG: File not found for bulk ingestion: {doc.filename}")
        
        logger.info(f"📊 RAG: Bulk ingestion completed: {ingested_count}/{len(docs)} documents ingested")
        
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
                # Log transcript and performance (minimal logging)
                _t = meta.get('transcript', '')
                if _t:
                    logger.debug(f"Whisper transcription completed: {len(_t)} chars")
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
            if _t:
                logger.debug(f"Whisper full transcription completed: {len(_t)} chars")
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
        print("🤖 RAG features: Advanced document-based Q&A (Integration)")
    print("="*60 + "\n")
    
    # Initialize RAG if enabled
    if RAG_ENABLED:
        initialize_rag_if_enabled()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
