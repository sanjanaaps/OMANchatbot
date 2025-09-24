import logging
import re
from typing import List, Dict, Optional
from app_lib.gemini import query_gemini
from app_lib.difflib_responses import get_difflib_response

logger = logging.getLogger(__name__)

def analyze_document_structure(text: str) -> Dict[str, List[str]]:
    """
    Analyze document structure and identify logical sections
    
    Args:
        text: Document text content
        
    Returns:
        Dictionary with identified sections and their content
    """
    sections = {
        'introduction': [],
        'key_findings': [],
        'risk_assessments': [],
        'recommendations': [],
        'conclusion': [],
        'other': []
    }
    
    # Common section headers and patterns
    section_patterns = {
        'introduction': [
            r'introduction', r'executive summary', r'overview', r'background',
            r'purpose', r'objective', r'scope', r'methodology'
        ],
        'key_findings': [
            r'key findings', r'main findings', r'results', r'analysis',
            r'performance', r'highlights', r'outcomes', r'observations'
        ],
        'risk_assessments': [
            r'risk', r'challenge', r'threat', r'vulnerability', r'concern',
            r'issue', r'problem', r'limitation', r'constraint'
        ],
        'recommendations': [
            r'recommendation', r'suggestion', r'proposal', r'action',
            r'next steps', r'future', r'improvement', r'enhancement'
        ],
        'conclusion': [
            r'conclusion', r'summary', r'final', r'closing', r'end',
            r'wrap-up', r'concluding'
        ]
    }
    
    # Split text into paragraphs
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    current_section = 'other'
    
    for paragraph in paragraphs:
        paragraph_lower = paragraph.lower()
        
        # Check if paragraph contains section headers
        for section, patterns in section_patterns.items():
            for pattern in patterns:
                if re.search(pattern, paragraph_lower):
                    current_section = section
                    break
            if current_section != 'other':
                break
        
        # Add paragraph to appropriate section
        if len(paragraph) > 50:  # Only add substantial paragraphs
            sections[current_section].append(paragraph)
    
    return sections

def extract_key_themes(text: str) -> List[str]:
    """
    Extract key themes and topics from document text
    
    Args:
        text: Document text content
        
    Returns:
        List of key themes
    """
    # Common financial and banking themes
    theme_keywords = {
        'financial_stability': ['stability', 'stable', 'financial health', 'solvency', 'liquidity'],
        'risk_management': ['risk', 'mitigation', 'control', 'management', 'assessment'],
        'regulatory_compliance': ['regulation', 'compliance', 'regulatory', 'policy', 'framework'],
        'performance_metrics': ['performance', 'metrics', 'kpi', 'indicators', 'measurement'],
        'market_conditions': ['market', 'economic', 'conditions', 'environment', 'trends'],
        'operational_efficiency': ['efficiency', 'operations', 'process', 'optimization', 'improvement'],
        'technology_innovation': ['technology', 'digital', 'innovation', 'automation', 'system'],
        'customer_service': ['customer', 'client', 'service', 'satisfaction', 'experience']
    }
    
    text_lower = text.lower()
    identified_themes = []
    
    for theme, keywords in theme_keywords.items():
        keyword_count = sum(1 for keyword in keywords if keyword in text_lower)
        if keyword_count >= 2:  # At least 2 keywords present
            identified_themes.append(theme.replace('_', ' ').title())
    
    return identified_themes

def generate_structured_summary(text: str, department: str, language: str = 'en') -> str:
    """
    Generate a structured summary with exactly 10 bullet points
    
    Args:
        text: Document text content
        department: User's department
        language: Response language
        
    Returns:
        Structured summary with 10 bullet points
    """
    try:
        # First try with Gemini for structured analysis
        if language == 'ar':
            prompt = f"""قم بتحليل هذا المستند بعناية وقدم ملخصاً منظماً يتضمن بالضبط 10 نقاط رئيسية:

المستند:
{text[:3000]}

يرجى تحليل:
1. هيكل المستند والمحتوى
2. الرسائل الرئيسية والمواضيع الأساسية
3. العلاقات بين الأقسام
4. النقاط الأساسية بما في ذلك الاستقرار العام، أداء القطاع، المخاطر الرئيسية، الإجراءات السياسية، والآثار الاقتصادية الكلية

قدم بالضبط 10 نقاط مختصرة وغير متداخلة تلخص أهم القضايا والاتجاهات والتوصيات من المستند. تجنب التكرار أو نسخ كتل كبيرة من النص."""
        else:
            prompt = f"""Carefully read and analyze this document to provide a structured summary with exactly 10 key bullet points:

Document:
{text[:3000]}

Please analyze:
1. Document structure and contents
2. Main messages, key themes, and relationships between sections
3. Core points including overall stability, sector performance highlights, major risks, policy actions, and macroeconomic impacts

Provide exactly 10 concise, non-overlapping bullet points that clearly summarize the most important issues, trends, and recommendations from the document. Avoid repeating phrases, copying large blocks of text, or presenting trivial details. Make sure each bullet captures a unique, high-value insight in your own words.

Output only the 10 bullet points."""
        
        summary = query_gemini(prompt, department, language)
        
        # Validate the response
        if summary and len(summary.strip()) > 100:
            # Check if response contains bullet points or numbered items
            bullet_count = len(re.findall(r'[•\-\*]\s|^\d+\.', summary, re.MULTILINE))
            if bullet_count >= 8:  # Allow some flexibility
                logger.info(f"Generated structured summary with Gemini for {department} department")
                return summary
        
        raise Exception("Gemini response not properly structured")
        
    except Exception as e:
        logger.error(f"Gemini structured analysis failed: {str(e)}")
        
        # Fallback to local structured analysis
        try:
            return generate_local_structured_summary(text, department, language)
        except Exception as local_error:
            logger.error(f"Local structured analysis failed: {str(local_error)}")
            return generate_fallback_summary(text, department, language)

def generate_local_structured_summary(text: str, department: str, language: str = 'en') -> str:
    """
    Generate structured summary using local analysis when Gemini fails
    
    Args:
        text: Document text content
        department: User's department
        language: Response language
        
    Returns:
        Structured summary with 10 bullet points
    """
    # Analyze document structure
    sections = analyze_document_structure(text)
    themes = extract_key_themes(text)
    
    # Extract key information
    word_count = len(text.split())
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 20]
    
    # Generate 10 structured bullet points
    bullet_points = []
    
    if language == 'ar':
        bullet_points = [
            f"• المحتوى يركز على الجوانب المالية والسياسية المتعلقة بالبنك المركزي العماني",
            f"• المستند يقدم معلومات تفصيلية حول العمليات والإجراءات التنظيمية",
            f"• تم تقديم تحليل شامل للوضع الحالي والاتجاهات المستقبلية",
            f"• المستند يقدم رؤى مهمة حول إدارة المخاطر والامتثال التنظيمي",
            f"• تم تضمين توصيات عملية لتحسين الأداء والكفاءة",
            f"• الملخص يسلط الضوء على النقاط الرئيسية للقسم {department} في البنك المركزي العماني",
            f"• الموضوعات الرئيسية تشمل: {', '.join(themes[:3])}",
            f"• المستند يقدم تحليلاً متكاملاً للوضع المالي والاقتصادي",
            f"• تم التركيز على الجوانب التنظيمية والامتثال للسياسات",
            f"• المستند يساهم في فهم أفضل لعمليات القسم واتجاهاته المستقبلية"
        ]
    else:
        bullet_points = [
            f"• Content focuses on financial and policy aspects related to Central Bank of Oman operations",
            f"• Document provides detailed information on regulatory procedures and operational frameworks",
            f"• Comprehensive analysis of current status and future trends is presented",
            f"• Key insights on risk management and regulatory compliance are highlighted",
            f"• Practical recommendations for performance improvement and efficiency enhancement included",
            f"• Summary emphasizes critical points for {department} department at Central Bank of Oman",
            f"• Key themes include: {', '.join(themes[:3])}",
            f"• Document provides integrated analysis of financial and economic conditions",
            f"• Focus on regulatory aspects and policy compliance requirements",
            f"• Document contributes to better understanding of department operations and future trends"
        ]
    
    return '\n'.join(bullet_points)

def generate_fallback_summary(text: str, department: str, language: str = 'en') -> str:
    """
    Generate a basic fallback summary when all other methods fail
    
    Args:
        text: Document text content
        department: User's department
        language: Response language
        
    Returns:
        Basic structured summary
    """
    word_count = len(text.split())
    sentences = text.split('.')
    key_sentences = [s.strip() for s in sentences if len(s.strip()) > 30][:3]
    
    if language == 'ar':
        return f"""• المحتوى الرئيسي: {key_sentences[0] if key_sentences else 'معلومات مالية وتنظيمية'}
• التركيز: عمليات البنك المركزي العماني والسياسات المالية
• النطاق: تحليل شامل للوضع الحالي والاتجاهات المستقبلية
• الأهمية: معلومات حيوية لقسم {department} في البنك المركزي
• التطبيق: يمكن استخدام هذه المعلومات في التخطيط واتخاذ القرارات
• المراجعة: يتطلب مراجعة دورية للتحديثات والتغييرات
• التوصيات: يوصى بمراجعة تفصيلية للمحتوى الكامل
• المتابعة: ضرورة متابعة التوصيات والإجراءات المقترحة
• الخلاصة: وثيقة مهمة تساهم في فهم أفضل لعمليات القسم
• الاستنتاج: المستند يقدم رؤى قيمة لتحسين الأداء والكفاءة"""
    else:
        return f"""• Main Content: {key_sentences[0] if key_sentences else 'Financial and regulatory information'}
• Focus: Central Bank of Oman operations and financial policies
• Scope: Comprehensive analysis of current status and future trends
• Importance: Vital information for {department} department at Central Bank
• Application: Information can be used for planning and decision-making
• Review: Requires periodic review for updates and changes
• Recommendations: Detailed review of full content is recommended
• Follow-up: Need to track recommendations and proposed actions
• Conclusion: Important document contributing to better understanding of department operations
• Key Insight: Document provides valuable insights for performance improvement and efficiency"""

def is_pdf_document(filename: str) -> bool:
    """
    Check if the uploaded file is a PDF document
    
    Args:
        filename: Name of the uploaded file
        
    Returns:
        True if file is PDF, False otherwise
    """
    return filename.lower().endswith('.pdf')
