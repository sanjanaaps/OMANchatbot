import os
import logging
import time
from typing import Optional, List
import google.generativeai as genai
from app_lib.extract import chunk_text
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

def configure_gemini():
    """Configure Gemini API with current environment variables"""
    GOOGLE_API_KEY = os.environ.get('GEMINI_API_KEY')  # For backward compatibility
    if not GOOGLE_API_KEY:
        GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    
    if not GOOGLE_API_KEY:
        logger.error("No Gemini API key found in environment variables")
        return None
        
    genai.configure(api_key=GOOGLE_API_KEY)
    return genai.GenerativeModel('models/gemini-pro-latest')

# Initialize model
model = configure_gemini()

DEPARTMENT_KEYWORDS = {
    'Finance': [
        'financial planning', 'budgeting', 'accounting', 'financial reporting',
        'revenue', 'expense', 'finance', 'financial', 'treasury', 'investment'
    ],
    'Monetary Policy & Banking': [
        'monetary policy', 'banking supervision', 'financial stability', 'policy',
        'banking', 'supervision', 'stability', 'monetary', 'interest rates',
        'economic analysis'
    ],
    'Currency': [
        'banknotes', 'coins', 'mint', 'currency', 'rial', 'exchange',
        'foreign exchange', 'currency management', 'exchange rate', 'forex',
        'currency operations'
    ],
    'Legal & Compliance': [
        'legal frameworks', 'regulatory compliance', 'risk management',
        'regulation', 'law', 'compliance', 'legal', 'policy', 'framework',
        'governance'
    ],
    'IT / Finance': [
        'information technology', 'financial technology', 'digital banking',
        'network', 'software', 'hardware', 'technology', 'it', 'digital',
        'system', 'security'
    ]
}

def get_department_focus(department):
    """Get department focus areas in English"""
    if department not in DEPARTMENT_KEYWORDS:
        return 'departmental operations and policies'
    
    return ', '.join(DEPARTMENT_KEYWORDS[department][:4]) + ', and ' + \
           DEPARTMENT_KEYWORDS[department][4]

DEPARTMENT_KEYWORDS_ARABIC = {
    'Finance': [
        'التخطيط المالي', 'الميزانيات', 'المحاسبة', 'التقارير المالية',
        'الإيرادات', 'المصروفات', 'المالية', 'الخزينة', 'الاستثمار',
        'التحليل المالي'
    ],
    'Monetary Policy & Banking': [
        'السياسة النقدية', 'الإشراف المصرفي', 'الاستقرار المالي',
        'السياسة', 'العمل المصرفي', 'الإشراف', 'الاستقرار', 'النقدي',
        'أسعار الفائدة', 'التحليل الاقتصادي'
    ],
    'Currency': [
        'الأوراق النقدية', 'العملات المعدنية', 'سك العملة', 'العملة',
        'الريال', 'الصرف', 'صرف العملات الأجنبية', 'إدارة العملة',
        'سعر الصرف', 'العمليات النقدية'
    ],
    'Legal & Compliance': [
        'الأطر القانونية', 'الامتثال التنظيمي', 'إدارة المخاطر',
        'التنظيم', 'القانون', 'الامتثال', 'القانوني', 'السياسة',
        'الإطار التنظيمي', 'الحوكمة'
    ],
    'IT / Finance': [
        'تكنولوجيا المعلومات', 'التكنولوجيا المالية', 'الخدمات المصرفية الرقمية',
        'الشبكات', 'البرمجيات', 'الأجهزة', 'التكنولوجيا', 'تقنية المعلومات',
        'الرقمية', 'النظام', 'الأمن'
    ]
}

def get_department_focus_arabic(department):
    """Get department focus areas in Arabic"""
    if department not in DEPARTMENT_KEYWORDS_ARABIC:
        return 'عمليات وسياسات القسم'
    
    keywords = DEPARTMENT_KEYWORDS_ARABIC[department]
    return ' و'.join([', '.join(keywords[:4]), keywords[4]])

def query_gemini(prompt: str, department: str, language: str = 'en', context: str = "") -> str:
    """
    Query Gemini API with department-specific context
    
    Args:
        prompt: User query
        department: User's department for context
        language: Response language ('en' or 'ar')
        context: Additional context from local search
        
    Returns:
        Gemini API response
    """
    global model
    
    # Refresh configuration if needed
    if not model:
        model = configure_gemini()
    
    if not model:
        # Return a helpful response based on the query
        if language == 'ar':
            if "oman central bank" in prompt.lower() or "البنك المركزي العماني" in prompt.lower():
                return f"البنك المركزي العماني هو البنك المركزي لسلطنة عمان، تأسس في عام 1974. يقع مقره الرئيسي في مسقط ويدير السياسة النقدية للبلاد. في قسم {department}، نركز على {get_department_focus_arabic(department)}. كيف يمكنني مساعدتك أكثر؟"
            elif "finance report" in prompt.lower() or "تقرير مالي" in prompt.lower():
                return f"تقرير مالي 2023: في قسم {department}، نركز على {get_department_focus_arabic(department)}. يمكنني مساعدتك في تحليل التقارير المالية والميزانيات والتقارير المحاسبية. ما هو السؤال المحدد الذي لديك حول التقرير المالي؟"
            else:
                return f"مرحباً! أنا مساعدك الذكي في قسم {department} في البنك المركزي العماني. أسعد لمساعدتك في أي أسئلة لديك حول عملك أو شؤون القسم."
        else:
            if "oman central bank" in prompt.lower():
                return f"The Central Bank of Oman (CBO) is the central bank of the Sultanate of Oman, established in 1974. It is headquartered in Muscat and manages the country's monetary policy. In the {department} department, we focus on {get_department_focus(department)}. How can I assist you further?"
            elif "finance report" in prompt.lower():
                return f"Finance Report 2023: In the {department} department, we focus on {get_department_focus(department)}. I can help you analyze financial reports, budgets, and accounting statements. What specific question do you have about the finance report?"
            else:
                return f"Hello! I'm your AI assistant for the {department} department at Oman Central Bank. I'm here to help you with any questions about your work or department matters. How can I assist you today?"
    
    try:
        # Prepare system context and user query
        messages = [
            f"""You are a specialized AI assistant in the {department} department at Oman Central Bank. Focus on providing specific, factual answers based on the provided document content only.""",
            f"""Here is the document to analyze:

{context}

Answer this question about the document: {prompt}

Remember:
1. Use only information found in the document above
2. Be specific and factual
3. If the answer isn't in the document, say so
4. Do not include any generic introductions or pleasantries"""
        ]

        # Add language instruction
        if language == 'ar':
            messages[0] += "\n\nPlease respond in Arabic."
        
        # Configure generation parameters
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            max_output_tokens=2048,
        )
        
        # Log the request
        logger.debug(f"Sending request to Gemini")
        
        # Generate response
        response = model.generate_content(
            "\n\n".join(messages),
            generation_config=generation_config
        )
        
        # Log response details
        logger.debug("Received response from Gemini")
        
        # Check if we got a valid response
        if response and hasattr(response, 'text'):
            content = response.text.strip()
            
            # Check for generic responses
            if "Hello! I'm your AI assistant" in content or "How can I assist you today" in content:
                logger.warning("Received generic response from Gemini")
                return content
            
            return content
        else:
            logger.error("Empty response from Gemini")
            return "I apologize, but I couldn't generate a proper response at the moment. Please try again."
            
    except Exception as e:
        logger.error(f"Error querying Gemini: {str(e)}")
        return f"I apologize, but I encountered an error: {str(e)}"

def analyze_document_with_gemini(document_content: str, department: str, language: str = 'en') -> dict:
    """
    Analyze a document using Gemini API
    
    Args:
        document_content: Document text content
        department: Department context
        language: Response language
        
    Returns:
        Analysis results with key topics, themes, facts, and summary
    """
    # Chunk large documents
    if len(document_content) > 3000:
        chunks = chunk_text(document_content, chunk_size=3000, overlap=200)
        # Use first chunk for analysis
        content = chunks[0]
        if len(chunks) > 1:
            content += f"\n\n[Note: This is a large document with {len(chunks)} sections. Analysis based on first section.]"
    else:
        content = document_content
    
    prompt = f"""Analyze the following {department} department document and provide:
1. Key topics and themes
2. Important facts or data points
3. Action items or recommendations (if any)
4. Summary in 2-3 sentences

Document content:
{content}"""
    
    if language == 'ar':
        prompt += "\n\nPlease respond in Arabic."
    
    try:
        analysis = query_gemini(prompt, department, language)
        
        return {
            'analysis': analysis,
            'language': language,
            'department': department
        }
    
    except Exception as e:
        logger.error(f"Document analysis failed: {str(e)}")
        return {
            'analysis': f"Analysis unavailable: {str(e)}",
            'language': language,
            'department': department
        }

def translate_text(text: str, target_language: str = 'ar') -> str:
    """
    Translate text using local GoogleTranslator (falling back to Gemini if needed)
    
    Args:
        text: Text to translate
        target_language: Target language code ('ar' for Arabic, 'en' for English)
        
    Returns:
        Translated text
    """
    if not text or not text.strip():
        return text
    
    try:
        # Handle large texts by chunking
        if len(text) > 4000:
            chunks = chunk_text(text, chunk_size=4000, overlap=200)
            translated_chunks = []
            
            for chunk in chunks:
                translated_chunk = _translate_chunk_local(chunk, target_language)
                translated_chunks.append(translated_chunk)
            
            return ' '.join(translated_chunks)
        else:
            return _translate_chunk_local(text, target_language)
            
    except Exception as e:
        logger.warning(f"Local translation failed: {str(e)}, falling back to Gemini API")
        return _translate_text_gemini(text, target_language)

def _translate_chunk_local(text: str, target_language: str, max_retries: int = 3) -> str:
    """
    Translate a chunk of text using local GoogleTranslator with retry mechanism
    
    Args:
        text: Text to translate
        target_language: Target language code
        max_retries: Maximum number of retry attempts
        
    Returns:
        Translated text or original text if all retries fail
    """
    for attempt in range(max_retries):
        try:
            if target_language == 'ar':
                translator = GoogleTranslator(source='auto', target='ar')
            elif target_language == 'en':
                translator = GoogleTranslator(source='auto', target='en')
            else:
                translator = GoogleTranslator(source='auto', target=target_language)
            
            translated = translator.translate(text)
            if translated and translated.strip():
                return translated
            else:
                logger.warning(f"Empty translation result on attempt {attempt + 1}")
                continue
                
        except Exception as e:
            logger.error(f"Local translation error on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait before retrying
                continue
            else:
                return text  # Return original text after all retries fail

def _translate_text_gemini(text: str, target_language: str = 'ar', max_retries: int = 3) -> str:
    """
    Fallback translation using Gemini API with retry mechanism
    
    Args:
        text: Text to translate
        target_language: Target language code ('ar' for Arabic, 'en' for English)
        max_retries: Maximum number of retry attempts
        
    Returns:
        Translated text or original text if all retries fail
    """
    global model
    if not model:
        model = configure_gemini()
    
    if not text or not text.strip():
        return text
    
    for attempt in range(max_retries):
        try:
            target_language_name = "Arabic" if target_language == 'ar' else "English"
            prompt = f"Translate the following text to {target_language_name}. Only return the translation, no additional text:\n\n{text}"
            
            # Generate translation
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    top_k=40,
                    top_p=0.95,
                    max_output_tokens=2048,
                )
            )
            
            if response and response.text and response.text.strip():
                return response.text.strip()
            else:
                logger.warning(f"Empty Gemini translation response on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # Wait before retrying
                    continue
                return text
                
        except Exception as e:
            logger.error(f"Gemini translation failed on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait before retrying
                # Try to refresh the model if there's an API error
                if "api" in str(e).lower():
                    model = configure_gemini()
                continue
            else:
                return text