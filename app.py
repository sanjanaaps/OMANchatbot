from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
import os
import sys
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_lib.db import init_db, get_user_by_username, get_user_by_id, save_document, get_recent_documents_by_department, get_document_count_by_department, get_chat_messages_by_user, save_chat_message, search_documents_in_db, create_or_replace_otp, verify_and_delete_otp
from app_lib.auth import login_required, get_current_user, check_password_hash
from app_lib.extract import extract_text_from_file
from app_lib.search import search_documents, get_document_summary
from app_lib.gemini import query_gemini, translate_text, get_department_focus, get_department_focus_arabic
from app_lib.difflib_responses import get_difflib_response
from app_lib.structured_analysis import generate_structured_summary, is_pdf_document
from app_lib.voice_service import VoiceRecordingService
# RAG integration - conditionally loaded based on user choice
RAG_ENABLED = False
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
from app_lib.whisper_service import WhisperService, is_gpu_available
import logging

app = Flask(__name__)

# Load configuration
config_class = get_config()
app.config.from_object(config_class)

# Initialize database (MongoDB)
init_db(app)

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Whisper at startup (ignore UI/testing integrations)
WHISPER_SERVICE = None
try:
    gpu = is_gpu_available()
    logger.info(f"GPU available for Whisper: {gpu}")
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

# Initialize RAG based on user choice (set by startup_config.py)
def initialize_rag_if_enabled():
    """Initialize RAG system if it was enabled during startup"""
    global RAG_ENABLED, RAG_AVAILABLE, rag_system
    
    if RAG_ENABLED:
        try:
            from app_lib.rag_integration import initialize_rag_system as _init_rag, get_rag_system as _get_rag, add_document_to_rag as _add_doc, query_rag as _query_rag
            
            # Replace dummy functions with real ones
            globals()['initialize_rag_system'] = _init_rag
            globals()['get_rag_system'] = _get_rag
            globals()['add_document_to_rag'] = _add_doc
            globals()['query_rag'] = _query_rag
            
            RAG_AVAILABLE = True
            logger.info("RAG integration enabled - initializing...")
            
            # Initialize RAG system
            rag_system = initialize_rag_system(app.config['UPLOAD_FOLDER'])
            if rag_system and rag_system.is_ready():
                logger.info("✅ RAG system initialized successfully")
            else:
                logger.warning("⚠️ RAG system initialized but not ready")
                
        except Exception as e:
            logger.error(f"Failed to initialize RAG system: {str(e)}")
            RAG_AVAILABLE = False
    else:
        logger.info("📝 RAG functionality disabled - running without RAG")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

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
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    login_type = request.form.get('login_type', 'staff')
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    selected_department = request.form.get('department', '')

    user = get_user_by_username(username)
    if not user or not check_password_hash(user['password_hash'], password):
        flash('Invalid username or password', 'error')
        return render_template('login.html')

    if login_type == 'staff':
        if not selected_department:
            flash('Please select a department', 'error')
            return render_template('login.html')
        if user.get('role', 'staff') == 'staff' and user['department'] != selected_department:
            flash('Access Denied: You are not authorized to log in to this department.', 'error')
            return render_template('login.html')
        # Direct login for staff (no OTP)
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['department'] = selected_department
        session['role'] = user.get('role', 'staff')
        flash('Login successful!', 'success')
        return redirect(url_for('dashboard'))

    # Higher authority: start OTP flow
    session['pending_ha_user'] = user['username']
    session['pending_ha_user_id'] = user['id']
    # Generate dummy OTP and "send" via log/console
    import random
    code = f"{random.randint(100000, 999999)}"
    create_or_replace_otp(user['username'], code)
    # Attempt to send via Gmail SMTP if configured; fallback to log
    try:
        from smtplib import SMTP
        from email.mime.text import MIMEText
        subject = 'Your Verification Code'
        body = f'Your one-time verification code is: {code}\nIt expires in 5 minutes.'
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = app.config.get('SMTP_FROM')
        msg['To'] = user.get('email') or app.config.get('SMTP_FROM')

        smtp_user = app.config.get('SMTP_USERNAME')
        smtp_pass = app.config.get('SMTP_PASSWORD')
        smtp_host = app.config.get('SMTP_HOST', 'smtp.gmail.com')
        smtp_port = int(app.config.get('SMTP_PORT', 587))

        if smtp_user and smtp_pass:
            with SMTP(smtp_host, smtp_port) as smtp:
                smtp.starttls()
                smtp.login(smtp_user, smtp_pass)
                smtp.send_message(msg)
            app.logger.info(f"[OTP] Email sent to {msg['To']}")
        else:
            app.logger.info(f"[OTP] SMTP not configured. Code for {user['username']} ({user.get('email')}): {code}")
    except Exception as e:
        app.logger.warning(f"[OTP] Email send failed, falling back to log. Error: {e}")
        app.logger.info(f"[OTP] Higher Authority code for {user['username']} ({user.get('email')}): {code}")
    flash('Verification code sent to your registered email.', 'info')
    return render_template('login.html', show_otp=True, active_tab='ha')

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    username = session.get('pending_ha_user')
    user_id = session.get('pending_ha_user_id')
    code = request.form.get('otp_code', '')
    if not username or not user_id:
        flash('Session expired. Please login again.', 'error')
        return render_template('login.html')
    if verify_and_delete_otp(username, code):
        session.pop('pending_ha_user', None)
        session.pop('pending_ha_user_id', None)
        user = get_user_by_id(user_id)
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['department'] = 'All'
        session['role'] = 'higher'
        flash('Higher Authority login successful.', 'success')
        return redirect(url_for('dashboard'))
    flash('Invalid or expired verification code.', 'error')
    return render_template('login.html', show_otp=True)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    department = session.get('department') if session.get('role') == 'higher' else user.department
    recent_docs = get_recent_documents_by_department(department if department != 'All' else user.department, limit=10)
    doc_count = get_document_count_by_department(department if department != 'All' else user.department)
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
            
            try:
                # Extract text from file
                extracted_text = extract_text_from_file(filepath)
                
                if not extracted_text.strip():
                    flash('No text could be extracted from the file', 'error')
                    os.remove(filepath)
                    return redirect(request.url)
                
                # Save document to database
                user = get_current_user()
                
                document_id = save_document({
                    'filename': filename,
                    'department': user.department,
                    'uploaded_by': user.username,
                    'content': extracted_text,
                    'file_type': filename.rsplit('.', 1)[1].lower()
                })
                class _Result:
                    def __init__(self, id):
                        self.id = id
                result = _Result(document_id)
                
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
                
                # Generate summary - use structured analysis for PDFs, regular summary for other files
                if is_pdf_document(filename):
                    # Use structured analysis for PDF documents
                    try:
                        summary = generate_structured_summary(extracted_text, user.department, 'en')
                        logger.info(f"Generated structured summary for PDF: {filename}")
                    except Exception as e:
                        logger.error(f"Structured analysis error: {str(e)}")
                        # Fallback to regular summary
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
                else:
                    # Use regular summary for non-PDF documents
                    try:
                        summary = query_gemini(f"Please provide a concise summary of this {user.department} department document:\n\n{extracted_text[:2000]}", user.department, 'en')
                        # Check if we got a generic response
                        if "Hello! I'm your AI assistant" in summary or "How can I assist you today" in summary:
                            raise Exception("Got generic response from Gemini")
                    except Exception as e:
                        logger.error(f"Gemini summary error: {str(e)}")
                        # Fallback to local summary
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
                
                flash(f'File uploaded successfully! Document ID: {result.id}', 'success')
                return render_template('upload_success.html', 
                                     document_id=result.id,
                                     summary=summary,
                                     filename=filename)
                
            except Exception as e:
                logger.error(f"Error processing file {filename}: {str(e)}")
                flash(f'Error processing file: {str(e)}', 'error')
                os.remove(filepath)
                return redirect(request.url)
        else:
            flash('Invalid file type. Allowed types: PDF, DOCX, DOC, PNG, JPG, JPEG, TIFF', 'error')
    
    return render_template('upload.html')


@app.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    user = get_current_user()
    
    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        language = request.form.get('language', 'en')
        
        if message:
            # Save user message to database
            save_chat_message({
                'user_id': user.id,
                'type': 'user',
                'content': message,
                'language': language,
                'department': user.department
            })
            
            # Try RAG system first, then local search, then fallbacks
            response = None
            
            # Try RAG system first
            if rag_system and rag_system.is_ready():
                try:
                    rag_response, rag_response_en = query_rag(message, language)
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
            
            # Save assistant response to database
            save_chat_message({
                'user_id': user.id,
                'type': 'assistant',
                'content': response,
                'language': language,
                'department': user.department
            })
    
    # Get recent messages for this user
    recent_messages = list(reversed(get_chat_messages_by_user(user.id, limit=20)))
    messages = recent_messages
    
    return render_template('chat.html', messages=messages)

@app.route('/documents')
@login_required
def documents():
    user = get_current_user()
    
    # Get all documents for user's department
    docs = get_documents_by_department(user.department)
    
    return render_template('documents.html', documents=docs, user=user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    flash('Account creation is not enabled yet. Please contact the administrator.', 'info')
    return redirect(url_for('login'))

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
        
        # Get all documents for user's department
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
        # Finalize and then try to run Whisper on best-effort audio
        meta = voice_service.finalize_session(session_id)
        audio_bytes = b""
        try:
            audio_bytes = voice_service.get_best_effort_audio(session_id)
        except Exception:
            audio_bytes = b""
        if audio_bytes and 'WHISPER_SERVICE' in globals() and WHISPER_SERVICE is not None:
            try:
                result = WHISPER_SERVICE.transcribe_bytes(audio_bytes, file_suffix='.webm')
                meta['transcript'] = result.get('text', '') or meta.get('transcript', '')
                meta['whisper_language'] = result.get('language', '')
                meta['whisper_load_time_s'] = result.get('load_time_s', '')
                meta['whisper_infer_time_s'] = result.get('infer_time_s', '')
            except Exception as e:
                logger.warning(f"Whisper transcription failed: {e}")
        return jsonify(meta)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


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
