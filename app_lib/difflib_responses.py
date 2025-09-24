import difflib
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class DifflibResponseGenerator:
    """Generate responses using difflib for simple Q&A matching"""
    
    def __init__(self):
        # Knowledge base for simple questions and answers
        self.knowledge_base = {
            # English Q&A pairs
            'en': {
                'greetings': {
                    'questions': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'how are you'],
                    'responses': [
                        "Hello! I'm your AI assistant for the {department} department at Oman Central Bank. How can I help you today?",
                        "Hi there! I'm here to assist you with any questions about your work in the {department} department. What would you like to know?",
                        "Good day! I'm your AI assistant. How can I help you with {department} department matters today?"
                    ]
                },
                'finance': {
                    'questions': ['what is finance', 'what is financial', 'finance definition', 'financial planning', 'budgeting', 'accounting'],
                    'responses': [
                        "Finance is the management of money and investments. In the {department} department, we focus on financial planning, budgeting, accounting, and financial reporting. We ensure proper financial controls and compliance with banking regulations.",
                        "Financial management involves planning, organizing, directing, and controlling financial activities. At the Central Bank of Oman, our {department} department handles financial analysis, risk assessment, and regulatory compliance.",
                        "Finance encompasses all activities related to money management, including budgeting, investing, lending, and financial reporting. In our {department} department, we maintain financial stability and ensure regulatory compliance."
                    ]
                },
                'banking': {
                    'questions': ['what is banking', 'banking system', 'central bank', 'monetary policy', 'banking regulations'],
                    'responses': [
                        "Banking is the business of accepting deposits and lending money. The Central Bank of Oman (CBO) is responsible for monetary policy, banking supervision, and maintaining financial stability. Our {department} department plays a crucial role in these operations.",
                        "A central bank manages a country's currency, money supply, and interest rates. The CBO, established in 1974, oversees Oman's banking system and ensures financial stability. The {department} department contributes to these critical functions.",
                        "Banking involves financial intermediation between savers and borrowers. The Central Bank of Oman regulates the banking sector and implements monetary policy. Our {department} department supports these regulatory and operational functions."
                    ]
                },
                'oman_central_bank': {
                    'questions': ['oman central bank', 'cbo', 'central bank of oman', 'muscat bank', 'oman bank'],
                    'responses': [
                        "The Central Bank of Oman (CBO) is the central bank of the Sultanate of Oman, established in 1974. It is headquartered in Muscat and manages the country's monetary policy. In the {department} department, we focus on {focus_area}. How can I assist you further?",
                        "CBO is Oman's central bank responsible for monetary policy, banking supervision, and financial stability. Located in Muscat, it was established in 1974. Our {department} department specializes in {focus_area}. What specific information do you need?",
                        "The Central Bank of Oman serves as the country's monetary authority, regulating banks and managing currency. The {department} department at CBO focuses on {focus_area}. How can I help you today?"
                    ]
                },
                'general_help': {
                    'questions': ['help', 'what can you do', 'how can you help', 'what do you do', 'assistance'],
                    'responses': [
                        "I'm your AI assistant for the {department} department at Oman Central Bank. I can help you with questions about banking, finance, regulations, and department-specific matters. I can also search through uploaded documents and provide translations.",
                        "I can assist you with various tasks including answering questions about banking and finance, searching through department documents, translating text, and providing information about Central Bank operations. What would you like help with?",
                        "As your AI assistant, I can help with financial analysis, document search, translation services, and answering questions about banking regulations and Central Bank policies. How can I assist you today?"
                    ]
                }
            },
            # Arabic Q&A pairs
            'ar': {
                'greetings': {
                    'questions': ['مرحبا', 'السلام عليكم', 'أهلا', 'صباح الخير', 'مساء الخير', 'كيف حالك', 'مرحبا بك'],
                    'responses': [
                        "مرحباً! أنا مساعدك الذكي في قسم {department} في البنك المركزي العماني. كيف يمكنني مساعدتك اليوم؟",
                        "أهلاً وسهلاً! أنا هنا لمساعدتك في أي أسئلة حول عملك في قسم {department}. ماذا تريد أن تعرف؟",
                        "السلام عليكم! أنا مساعدك الذكي. كيف يمكنني مساعدتك في شؤون قسم {department} اليوم؟"
                    ]
                },
                'finance': {
                    'questions': ['ما هو المال', 'ما هو المالي', 'تعريف المال', 'التخطيط المالي', 'الميزانية', 'المحاسبة'],
                    'responses': [
                        "المال هو إدارة الأموال والاستثمارات. في قسم {department}، نركز على التخطيط المالي والميزانيات والمحاسبة والتقارير المالية. نحن نضمن الضوابط المالية المناسبة والامتثال للوائح المصرفية.",
                        "الإدارة المالية تشمل التخطيط والتنظيم والتوجيه والتحكم في الأنشطة المالية. في البنك المركزي العماني، يتعامل قسم {department} مع التحليل المالي وتقييم المخاطر والامتثال التنظيمي.",
                        "المال يشمل جميع الأنشطة المتعلقة بإدارة الأموال، بما في ذلك الميزانيات والاستثمار والإقراض والتقارير المالية. في قسم {department}، نحافظ على الاستقرار المالي وضمان الامتثال التنظيمي."
                    ]
                },
                'banking': {
                    'questions': ['ما هو المصرف', 'النظام المصرفي', 'البنك المركزي', 'السياسة النقدية', 'اللوائح المصرفية'],
                    'responses': [
                        "المصرف هو عمل قبول الودائع وإقراض الأموال. البنك المركزي العماني مسؤول عن السياسة النقدية والإشراف المصرفي والحفاظ على الاستقرار المالي. قسم {department} يلعب دوراً حاسماً في هذه العمليات.",
                        "البنك المركزي يدير عملة البلاد والمعروض النقدي وأسعار الفائدة. البنك المركزي العماني، الذي تأسس في عام 1974، يشرف على النظام المصرفي في عمان ويضمن الاستقرار المالي. قسم {department} يساهم في هذه الوظائف الحيوية.",
                        "المصرفية تشمل الوساطة المالية بين المدخرين والمقترضين. البنك المركزي العماني ينظم القطاع المصرفي وينفذ السياسة النقدية. قسم {department} يدعم هذه الوظائف التنظيمية والتشغيلية."
                    ]
                },
                'oman_central_bank': {
                    'questions': ['البنك المركزي العماني', 'البنك المركزي', 'بنك عمان المركزي', 'بنك مسقط', 'بنك عمان'],
                    'responses': [
                        "البنك المركزي العماني هو البنك المركزي لسلطنة عمان، تأسس في عام 1974. يقع مقره الرئيسي في مسقط ويدير السياسة النقدية للبلاد. في قسم {department}، نركز على {focus_area}. كيف يمكنني مساعدتك أكثر؟",
                        "البنك المركزي العماني مسؤول عن السياسة النقدية والإشراف المصرفي والاستقرار المالي. يقع في مسقط وتأسس في عام 1974. قسم {department} متخصص في {focus_area}. ما هي المعلومات المحددة التي تحتاجها؟",
                        "البنك المركزي العماني يخدم كسلطة نقدية للبلاد، ينظم البنوك ويدير العملة. قسم {department} في البنك المركزي العماني يركز على {focus_area}. كيف يمكنني مساعدتك اليوم؟"
                    ]
                },
                'general_help': {
                    'questions': ['مساعدة', 'ماذا يمكنك أن تفعل', 'كيف يمكنك المساعدة', 'ماذا تفعل', 'المساعدة'],
                    'responses': [
                        "أنا مساعدك الذكي في قسم {department} في البنك المركزي العماني. يمكنني مساعدتك في الأسئلة حول المصرفية والمالية واللوائح والمسائل الخاصة بالقسم. يمكنني أيضاً البحث في المستندات المرفوعة وتقديم الترجمات.",
                        "يمكنني مساعدتك في مهام مختلفة تشمل الإجابة على الأسئلة حول المصرفية والمالية والبحث في مستندات القسم وترجمة النصوص وتقديم معلومات حول عمليات البنك المركزي. ماذا تريد المساعدة فيه؟",
                        "بصفتي مساعدك الذكي، يمكنني المساعدة في التحليل المالي والبحث في المستندات وخدمات الترجمة والإجابة على الأسئلة حول اللوائح المصرفية وسياسات البنك المركزي. كيف يمكنني مساعدتك اليوم؟"
                    ]
                }
            }
        }
    
    def get_department_focus(self, department: str, language: str = 'en') -> str:
        """Get department focus areas for template formatting"""
        if language == 'ar':
            focus_areas = {
                'Finance': 'التخطيط المالي والميزانيات والمحاسبة والتقارير المالية',
                'Monetary Policy & Banking': 'صياغة السياسة النقدية والإشراف المصرفي والاستقرار المالي',
                'Currency': 'إدارة العملة وسياسات سعر الصرف وعمليات العملة',
                'Legal & Compliance': 'الأطر القانونية والامتثال التنظيمي وإدارة المخاطر',
                'IT / Finance': 'أنظمة تكنولوجيا المعلومات والتكنولوجيا المالية والخدمات المصرفية الرقمية'
            }
        else:
            focus_areas = {
                'Finance': 'financial planning, budgeting, accounting, and financial reporting',
                'Monetary Policy & Banking': 'monetary policy formulation, banking supervision, and financial stability',
                'Currency': 'currency management, exchange rate policies, and currency operations',
                'Legal & Compliance': 'legal frameworks, regulatory compliance, and risk management',
                'IT / Finance': 'information technology systems, financial technology, and digital banking'
            }
        
        return focus_areas.get(department, 'departmental operations and policies' if language == 'en' else 'عمليات وسياسات القسم')
    
    def find_best_match(self, query: str, language: str = 'en') -> Optional[Dict]:
        """
        Find the best matching category and response for a query
        
        Args:
            query: User query
            language: Language code ('en' or 'ar')
            
        Returns:
            Dictionary with category, confidence, and response template, or None if no good match
        """
        if language not in self.knowledge_base:
            language = 'en'
        
        query_lower = query.lower().strip()
        best_match = None
        best_confidence = 0.0
        
        for category, data in self.knowledge_base[language].items():
            questions = data['questions']
            
            # Use difflib to find the best match
            matches = difflib.get_close_matches(
                query_lower, 
                questions, 
                n=1, 
                cutoff=0.6
            )
            
            if matches:
                # Calculate confidence based on similarity
                similarity = difflib.SequenceMatcher(None, query_lower, matches[0]).ratio()
                
                if similarity > best_confidence:
                    best_confidence = similarity
                    best_match = {
                        'category': category,
                        'confidence': similarity,
                        'response_template': data['responses']
                    }
        
        # Only return if confidence is high enough
        if best_confidence >= 0.6:
            return best_match
        
        return None
    
    def generate_response(self, query: str, department: str, language: str = 'en') -> str:
        """
        Generate a response using difflib matching
        
        Args:
            query: User query
            department: User's department
            language: Response language
            
        Returns:
            Generated response string
        """
        try:
            match = self.find_best_match(query, language)
            
            if match:
                # Select a random response from the category
                import random
                response_template = random.choice(match['response_template'])
                
                # Format the response with department and focus area
                focus_area = self.get_department_focus(department, language)
                response = response_template.format(
                    department=department,
                    focus_area=focus_area
                )
                
                logger.info(f"Generated difflib response for query: '{query}' with confidence: {match['confidence']:.2f}")
                return response
            
            # Fallback response if no good match found
            if language == 'ar':
                return f"مرحباً! أنا مساعدك الذكي في قسم {department} في البنك المركزي العماني. أسعد لمساعدتك في أي أسئلة لديك حول عملك أو شؤون القسم. كيف يمكنني مساعدتك اليوم؟"
            else:
                return f"Hello! I'm your AI assistant for the {department} department at Oman Central Bank. I'm here to help you with any questions about your work or department matters. How can I assist you today?"
                
        except Exception as e:
            logger.error(f"Error generating difflib response: {str(e)}")
            # Return a safe fallback
            if language == 'ar':
                return f"مرحباً! أنا مساعدك الذكي في قسم {department} في البنك المركزي العماني. كيف يمكنني مساعدتك اليوم؟"
            else:
                return f"Hello! I'm your AI assistant for the {department} department at Oman Central Bank. How can I assist you today?"

# Global instance
difflib_generator = DifflibResponseGenerator()

def get_difflib_response(query: str, department: str, language: str = 'en') -> str:
    """
    Get a response using difflib matching
    
    Args:
        query: User query
        department: User's department
        language: Response language
        
    Returns:
        Generated response string
    """
    return difflib_generator.generate_response(query, department, language)

