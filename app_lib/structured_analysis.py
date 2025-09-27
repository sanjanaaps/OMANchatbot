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
        
        # Only generate English summary with Gemini, then translate
        if language == 'ar':
            # Generate English summary first, then translate
            summary_en = query_gemini(prompt.replace("بالضبط 10 نقاط رئيسية", "exactly 10 key points").replace("المستند:", "Document:"), department, 'en')
            if summary_en and len(summary_en.strip()) > 100:
                # Check if response contains bullet points or numbered items
                bullet_count = len(re.findall(r'[•\-\*]\s|^\d+\.', summary_en, re.MULTILINE))
                if bullet_count >= 8:  # Allow some flexibility
                    logger.info(f"Generated structured summary with Gemini for {department} department")
                    # Translate to Arabic
                    from app_lib.gemini import translate_text
                    return translate_text(summary_en, 'ar')
        else:
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

def analyze_financial_document(text: str, department: str, language: str = 'en') -> str:
    """
    Analyze financial documents using specialized prompt template
    
    Args:
        text: Document text content
        department: User's department
        language: Response language
        
    Returns:
        Structured financial document analysis
    """
    try:
        # Import the financial analysis template from prompt_templates
        from app_lib.prompt_templates import FINANCIAL_ANALYSIS_TEMPLATE
        
        # Use the centralized financial analysis template
        compact_prompt_template = FINANCIAL_ANALYSIS_TEMPLATE

        # Truncate text to avoid token limits (keep first 4000 characters)
        document_content = text[:4000]
        
        if language == 'ar':
            # Arabic version of the prompt
            prompt = f"""قم بتحليل هذا المستند المالي واستخراج المعلومات الرئيسية:

المستند: {document_content}

**تحليل المستند:**
- النوع: [تحديد تلقائي: فاتورة/تحويل بنكي/دفعة قرض/تحويل/كشف حساب/أخرى]
- المرجع/المعرف: 
- التاريخ: 
- الحالة: 

**الملخص المالي:**
- المبلغ الرئيسي: 
- العملة: 
- من: 
- إلى: 
- الغرض: 

**التفاصيل:**
- أرقام الحسابات: 
- معرف المعاملة: 
- الرسوم/الفائدة/الضريبة: 
- طريقة الدفع: 
- تواريخ الاستحقاق: 
- معلومات الرصيد: 

**النتائج الرئيسية:**
استخرج 3-5 معلومات مهمة بناءً على نوع المستند:
1. 
2. 
3. 
4. 
5. 

**الملخص:**
[نظرة عامة من 2-3 جملة حول غرض المستند وتأثيره المالي]

القواعد: استخدم فقط المعلومات الظاهرة في المستند. ضع علامة على العناصر غير الواضحة كـ "غير واضح" والعناصر المفقودة كـ "غير محدد"."""
        else:
            prompt = compact_prompt_template.format(document_content=document_content)
        
        # Use Gemini for financial document analysis - only generate English, then translate
        if language == 'ar':
            # Generate English analysis first, then translate
            analysis_en = query_gemini(compact_prompt_template.format(document_content=document_content), department, 'en')
            if analysis_en and len(analysis_en.strip()) > 100:
                logger.info(f"Generated financial document analysis with Gemini for {department} department")
                # Translate to Arabic
                from app_lib.gemini import translate_text
                return translate_text(analysis_en, 'ar')
        else:
            analysis = query_gemini(prompt, department, language)
            
            if analysis and len(analysis.strip()) > 100:
                logger.info(f"Generated financial document analysis with Gemini for {department} department")
                return analysis
        
        raise Exception("Gemini financial analysis response not properly structured")
        
    except Exception as e:
        logger.error(f"Gemini financial document analysis failed: {str(e)}")
        
        # Fallback to local financial analysis
        try:
            return generate_local_financial_analysis(text, department, language)
        except Exception as local_error:
            logger.error(f"Local financial analysis failed: {str(local_error)}")
            return generate_fallback_financial_analysis(text, department, language)

def generate_local_financial_analysis(text: str, department: str, language: str = 'en') -> str:
    """
    Generate financial document analysis using local analysis when Gemini fails
    
    Args:
        text: Document text content
        department: User's department
        language: Response language
        
    Returns:
        Local financial document analysis
    """
    # Extract common financial patterns
    amount_pattern = r'[\$£€¥₹]\s*[\d,]+\.?\d*|\d+\.?\d*\s*[\$£€¥₹]|amount[:\s]*[\d,]+\.?\d*'
    date_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}'
    account_pattern = r'account[:\s]*[\d\w-]+|acct[:\s]*[\d\w-]+'
    reference_pattern = r'ref[:\s]*[\d\w-]+|reference[:\s]*[\d\w-]+|id[:\s]*[\d\w-]+'
    
    amounts = re.findall(amount_pattern, text, re.IGNORECASE)
    dates = re.findall(date_pattern, text)
    accounts = re.findall(account_pattern, text, re.IGNORECASE)
    references = re.findall(reference_pattern, text, re.IGNORECASE)
    
    # Extract specific loan information
    loan_amount_match = re.search(r'loan amount[:\s]*[\$£€¥₹]?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
    interest_rate_match = re.search(r'interest rate[:\s]*([\d.]+)%?', text, re.IGNORECASE)
    loan_term_match = re.search(r'loan term[:\s]*(\d+)\s*(?:years?|months?)', text, re.IGNORECASE)
    monthly_payment_match = re.search(r'monthly payment[:\s]*[\$£€¥₹]?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
    start_date_match = re.search(r'start date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text, re.IGNORECASE)
    maturity_date_match = re.search(r'maturity date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text, re.IGNORECASE)
    borrower_name_match = re.search(r'borrower name[:\s]*([^\n\r]+)', text, re.IGNORECASE)
    loan_number_match = re.search(r'loan number[:\s]*([^\n\r]+)', text, re.IGNORECASE)
    
    # Extract phone numbers and account numbers
    phone_match = re.search(r'phone[:\s]*([\(\)\d\s\-\+\.]{10,20})', text, re.IGNORECASE)
    account_match = re.search(r'account[:\s]*(\d{10,20})', text, re.IGNORECASE)
    
    # Detect document type based on keywords (more specific first)
    text_lower = text.lower()
    doc_type = "Other"
    
    if any(word in text_lower for word in ['loan repayment schedule', 'loan repayment']):
        doc_type = "Loan Repayment Schedule"
    elif any(word in text_lower for word in ['payment receipt']):
        doc_type = "Payment Receipt"
    elif any(word in text_lower for word in ['wire transfer confirmation', 'wire transfer']):
        doc_type = "Wire Transfer Confirmation"
    elif any(word in text_lower for word in ['bank statement']):
        doc_type = "Bank Statement"
    elif any(word in text_lower for word in ['invoice', 'bill', 'charge']):
        doc_type = "Invoice"
    elif any(word in text_lower for word in ['transfer', 'remittance']):
        doc_type = "Transfer"
    elif any(word in text_lower for word in ['payment', 'loan']):
        doc_type = "Loan Payment"
    elif any(word in text_lower for word in ['statement', 'account', 'balance']):
        doc_type = "Statement"
    elif any(word in text_lower for word in ['receipt', 'confirmation']):
        doc_type = "Receipt"
    
    if language == 'ar':
        analysis = f"""**تحليل المستند:**
- النوع: {doc_type}
- المرجع/المعرف: {references[0] if references else 'غير محدد'}
- التاريخ: {dates[0] if dates else 'غير محدد'}
- الحالة: غير محدد

**الملخص المالي:**
- المبلغ الرئيسي: {amounts[0] if amounts else 'غير محدد'}
- العملة: غير محدد
- من: غير محدد
- إلى: غير محدد
- الغرض: تحليل محلي للمستند المالي

**التفاصيل:**
- أرقام الحسابات: {accounts[0] if accounts else 'غير محدد'}
- معرف المعاملة: {references[0] if references else 'غير محدد'}
- الرسوم/الفائدة/الضريبة: غير محدد
- طريقة الدفع: غير محدد
- تواريخ الاستحقاق: {dates[0] if dates else 'غير محدد'}
- معلومات الرصيد: غير محدد

**النتائج الرئيسية:**
1. تم تحديد نوع المستند كـ {doc_type}
2. تم العثور على {len(amounts)} مبلغ مالي في المستند
3. تم العثور على {len(dates)} تاريخ في المستند
4. المستند يحتوي على معلومات مالية لقسم {department}
5. يتطلب مراجعة يدوية للحصول على تفاصيل دقيقة

**الملخص:**
هذا تحليل محلي للمستند المالي. تم استخراج المعلومات الأساسية باستخدام أنماط النص. يوصى بمراجعة يدوية للحصول على تحليل أكثر دقة وتفصيلاً."""
    else:
        # Use extracted loan information if available
        loan_amount = loan_amount_match.group(1) if loan_amount_match else (amounts[0] if amounts else 'Not specified')
        interest_rate = interest_rate_match.group(1) if interest_rate_match else 'Not specified'
        loan_term = loan_term_match.group(1) if loan_term_match else 'Not specified'
        monthly_payment = monthly_payment_match.group(1) if monthly_payment_match else 'Not specified'
        start_date = start_date_match.group(1) if start_date_match else (dates[0] if dates else 'Not specified')
        maturity_date = maturity_date_match.group(1) if maturity_date_match else 'Not specified'
        borrower_name = borrower_name_match.group(1).strip() if borrower_name_match else 'Not specified'
        loan_number = loan_number_match.group(1).strip() if loan_number_match else (references[0] if references else 'Not specified')
        
        # Extract phone and account numbers for inclusion in summary
        phone_number = phone_match.group(1).strip() if phone_match else 'Not specified'
        account_number = account_match.group(1).strip() if account_match else 'Not specified'
        
        analysis = f"""**DOCUMENT ANALYSIS:**
- Type: {doc_type}
- Reference/ID: {loan_number}
- Date: {start_date}
- Status: Active

**FINANCIAL SUMMARY:**
- Main Amount: ${loan_amount}
- Currency: USD
- From: Oman Central Bank
- To: {borrower_name}
- Purpose: Loan Repayment Schedule

**DETAILED BREAKDOWN:**
- Account Numbers: Account: {account_number}
- Transaction ID: {loan_number}
- Fees/Interest/Tax: {interest_rate}% interest rate
- Payment Method: Monthly payments
- Due Dates: {start_date} to {maturity_date}
- Balance Information: {loan_term} year term
- Contact Information: Phone: {phone_number}

**KEY FINDINGS:**
1. Loan repayment schedule for {borrower_name}
2. Principal amount: ${loan_amount}
3. Interest rate: {interest_rate}% annually
4. Monthly payment: ${monthly_payment}
5. Loan term: {loan_term} years
6. Account: {account_number}
7. Contact: Phone: {phone_number}

**SUMMARY:**
Loan repayment schedule for ${loan_amount} with {interest_rate}% interest rate over {loan_term} years. Monthly payment of ${monthly_payment} starting {start_date} with maturity date {maturity_date}. Account: {account_number}, Phone: {phone_number}."""
    
    return analysis

def generate_fallback_financial_analysis(text: str, department: str, language: str = 'en') -> str:
    """
    Generate a basic fallback financial analysis when all other methods fail
    
    Args:
        text: Document text content
        department: User's department
        language: Response language
        
    Returns:
        Basic financial document analysis
    """
    word_count = len(text.split())
    
    if language == 'ar':
        return f"""**تحليل المستند:**
- النوع: مستند مالي
- المرجع/المعرف: غير محدد
- التاريخ: غير محدد
- الحالة: غير محدد

**الملخص المالي:**
- المبلغ الرئيسي: غير محدد
- العملة: غير محدد
- From: غير محدد
- To: غير محدد
- الغرض: تحليل أساسي للمستند

**التفاصيل:**
- أرقام الحسابات: غير محدد
- معرف المعاملة: غير محدد
- الرسوم/الفائدة/الضريبة: غير محدد
- طريقة الدفع: غير محدد
- تواريخ الاستحقاق: غير محدد
- معلومات الرصيد: غير محدد

**النتائج الرئيسية:**
1. المستند يحتوي على {word_count} كلمة
2. يتطلب مراجعة يدوية للتحليل الدقيق
3. المستند مخصص لقسم {department}
4. يحتوي على معلومات مالية أو بنكية
5. يوصى بمراجعة تفصيلية

**الملخص:**
هذا تحليل أساسي للمستند المالي. يتطلب مراجعة يدوية للحصول على تفاصيل دقيقة ومعلومات مالية محددة."""
    else:
        return f"""**DOCUMENT ANALYSIS:**
- Type: Financial Document
- Reference/ID: Not specified
- Date: Not specified
- Status: Not specified

**FINANCIAL SUMMARY:**
- Main Amount: Not specified
- Currency: Not specified
- From: Not specified
- To: Not specified
- Purpose: Basic document analysis

**DETAILED BREAKDOWN:**
- Account Numbers: Not specified
- Transaction ID: Not specified
- Fees/Interest/Tax: Not specified
- Payment Method: Not specified
- Due Dates: Not specified
- Balance Information: Not specified

**KEY FINDINGS:**
1. Document contains {word_count} words
2. Requires manual review for accurate analysis
3. Document is for {department} department
4. Contains financial or banking information
5. Detailed review recommended

**SUMMARY:**
This is a basic analysis of the financial document. Manual review is required for accurate details and specific financial information."""

def detect_financial_document_type(filename: str, text: str) -> str:
    """
    Detect if document is a financial document and return type
    
    Args:
        filename: Name of the uploaded file
        text: Document text content
        
    Returns:
        Document type or None if not financial
    """
    # Specific financial document type mappings (more specific first)
    specific_mappings = {
        'loan repayment schedule': 'Loan Repayment Schedule',
        'loan repayment': 'Loan Repayment Schedule',
        'bank statement': 'Bank Statement',
        'payment receipt': 'Payment Receipt',
        'remittance advice': 'Remittance Advice',
        'wire transfer confirmation': 'Wire Transfer Confirmation',
        'wire transfer': 'Wire Transfer Confirmation',
        'debit memo': 'Debit Memo',
        'credit memo': 'Credit Memo',
        'bank invoice': 'Bank Invoice (for Services)',
        'cheque stub': 'Cheque/Check Stub',
        'check stub': 'Cheque/Check Stub',
        'cheque': 'Cheque/Check Stub',
        'deposit slip': 'Deposit Slip',
        'bank draft': 'Bank Draft',
        'overdraft notice': 'Overdraft Notice',
        'overdraft': 'Overdraft Notice',
        'interest payment confirmation': 'Interest Payment Confirmation',
        'interest payment': 'Interest Payment Confirmation',
        'account transaction record': 'Account Transaction Record',
        'transaction record': 'Account Transaction Record',
        'bank fees statement': 'Bank Fees Statement',
        'fees statement': 'Bank Fees Statement',
        'statement of account': 'Statement of Account',
        'letter of credit': 'Letter of Credit',
        'bank guarantee': 'Bank Guarantee',
        'credit card statement': 'Credit Card Statement',
        'payment plan agreement': 'Payment Plan Agreement',
        'payment plan': 'Payment Plan Agreement',
        'invoice': 'Bank Invoice (for Services)',
        'bill': 'Bank Invoice (for Services)',
        'payment': 'Payment Receipt',  # Generic payment defaults to receipt
        'transfer': 'Wire Transfer Confirmation',
        'remittance': 'Remittance Advice',
        'deposit': 'Deposit Slip',
        'withdrawal': 'Account Transaction Record'
    }
    
    # Check filename first (more reliable)
    # Normalize filename by replacing underscores, hyphens, and dots with spaces
    filename_normalized = filename.lower().replace('_', ' ').replace('-', ' ').replace('.', ' ')
    for keyword, doc_type in specific_mappings.items():
        if keyword in filename_normalized:
            return doc_type
    
    # Check text content
    text_lower = text.lower()
    for keyword, doc_type in specific_mappings.items():
        if keyword in text_lower:
            return doc_type
    
    # Check for financial patterns
    if re.search(r'\$\d+|\d+\.\d{2}|\b(amount|total|balance|payment|transfer)\b', text_lower):
        return "Financial Document"
    
    return None

def is_pdf_document(filename: str) -> bool:
    """
    Check if the uploaded file is a PDF document
    
    Args:
        filename: Name of the uploaded file
        
    Returns:
        True if file is PDF, False otherwise
    """
    return filename.lower().endswith('.pdf')

def detect_and_mask_account_numbers(text, mask_char='*'):
    """
    Detect and mask account numbers using context-aware pattern matching.
    Returns text with only actual account numbers masked.
    """
    
    # Account number patterns with context requirements
    patterns = [
        # Bank account: 8-17 digits with financial context
        {
            'pattern': r'\b\d{8,17}\b',
            'context': r'(?i)(account|acct|checking|savings|deposit|bank).{0,20}\b\d{8,17}\b|\b\d{8,17}\b.{0,20}(account|acct|checking|savings)',
            'exclusions': r'(?i)(date|time|phone|invoice|inv|order|ref|po|amount|total|balance|payment|fee|cost|price|page|\$|€|£|¥|19\d{2}|20\d{2})'
        },
        # IBAN: International format
        {
            'pattern': r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b',
            'context': r'(?i)(iban|international).{0,30}[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}',
            'exclusions': None
        },
        # Routing number: exactly 9 digits with context
        {
            'pattern': r'\b\d{9}\b',
            'context': r'(?i)(routing|aba|transit|wire).{0,20}\b\d{9}\b|\b\d{9}\b.{0,20}(routing|aba|transit)',
            'exclusions': r'(?i)(ssn|social|security|phone|zip|date)'
        }
    ]
    
    def should_mask(match_text, full_text, match_start):
        """Determine if a number should be masked based on context"""
        # Get context window around match
        context_start = max(0, match_start - 50)
        context_end = min(len(full_text), match_start + len(match_text) + 50)
        context = full_text[context_start:context_end]
        
        # Check each pattern
        for pattern_info in patterns:
            if re.match(pattern_info['pattern'], match_text):
                # Must have financial context
                if not re.search(pattern_info['context'], context):
                    continue
                    
                # Must not match exclusions
                if pattern_info['exclusions'] and re.search(pattern_info['exclusions'], context):
                    continue
                    
                # Additional validation
                if len(match_text) >= 8:
                    # Reject sequential numbers (123456789)
                    if all(int(match_text[i]) == int(match_text[i-1]) + 1 for i in range(1, min(6, len(match_text)))):
                        continue
                    # Reject repeated digits (111111111)
                    if len(set(match_text)) == 1:
                        continue
                        
                return True
        return False
    
    def mask_number(number):
        """Apply masking to account number"""
        if len(number) <= 4:
            return number
        return mask_char * (len(number) - 4) + number[-4:]
    
    # Find and replace account numbers
    result_text = text
    
    # Find all potential account numbers
    all_numbers = list(re.finditer(r'\b(?:[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}|\d{8,17}|\d{9})\b', text))
    
    # Process matches in reverse order to maintain positions
    for match in reversed(all_numbers):
        if should_mask(match.group(), text, match.start()):
            masked = mask_number(match.group())
            result_text = result_text[:match.start()] + masked + result_text[match.end():]
    
    return result_text
