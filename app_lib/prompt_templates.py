# -*- coding: utf-8 -*-
"""
Prompt Templates for Document Analysis and Chat Responses
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Financial document types from FINANCIAL_DOCUMENT_ANALYSIS.md
FINANCIAL_DOCUMENT_TYPES = [
    "Bank Statement",
    "Payment Receipt", 
    "Remittance Advice",
    "Wire Transfer Confirmation",
    "Debit Memo",
    "Credit Memo",
    "Loan Repayment Schedule",
    "Bank Invoice (for Services)",
    "Cheque/Check Stub",
    "Deposit Slip",
    "Bank Draft",
    "Overdraft Notice",
    "Interest Payment Confirmation",
    "Account Transaction Record",
    "Bank Fees Statement",
    "Statement of Account",
    "Letter of Credit",
    "Bank Guarantee",
    "Credit Card Statement",
    "Payment Plan Agreement"
]

# RAG Prompt Template for Context-Based Answers
RAG_PROMPT_TEMPLATE = """You are an assistant for the Oman Central Bank. You must follow these rules strictly:

RULES:
1. Use ONLY the information provided in the Context section below
2. If the exact answer is not found in the Context, respond with "I don't have that specific information available"
3. Do NOT add any information from your general knowledge
4. Do NOT make assumptions or inferences beyond what is explicitly stated
5. Quote directly from the context when possible

Context: {context}

Question: {question}

Instructions: Read the context carefully and provide an answer using ONLY the information above. If you cannot find the answer in the context, say "I don't have that specific information available."

Answer:"""

# Financial Document Analysis Prompt Template
FINANCIAL_DOCUMENT_PROMPT_TEMPLATE = """Analyze this financial document and extract key information:

DOCUMENT: {document_content}

**DOCUMENT ANALYSIS:**
- Type: [Auto-detect: Invoice/Wire Transfer/Loan Payment/Remittance/Statement/Other]
- Reference/ID: 
- Date: 
- Status: 

**FINANCIAL SUMMARY:**
- Main Amount: 
- Currency: 
- From: 
- To: 
- Purpose: 

**DETAILED BREAKDOWN:**
- Account Numbers: 
- Transaction ID: 
- Fees/Interest/Tax: 
- Payment Method: 
- Due Dates: 
- Balance Information: 

**KEY FINDINGS:**
Extract 3-5 most important pieces of information based on document type:
1. 
2. 
3. 
4. 
5. 

**SUMMARY:**
[2-3 sentence overview of the document's purpose and financial impact]

RULES: Use only information visible in the document. Mark unclear items as "Unclear" and missing items as "Not specified"."""

# General Document Analysis Prompt Template
GENERAL_DOCUMENT_PROMPT_TEMPLATE = """Carefully read and analyze this document to provide a structured summary with exactly 10 key bullet points:

Document:
{document_content}

Please analyze:
1. Document structure and contents
2. Main messages, key themes, and relationships between sections
3. Core points including overall stability, sector performance highlights, major risks, policy actions, and macroeconomic impacts

Provide exactly 10 concise, non-overlapping bullet points that clearly summarize the most important issues, trends, and recommendations from the document. Avoid repeating phrases, copying large blocks of text, or presenting trivial details. Make sure each bullet captures a unique, high-value insight in your own words.

Output only the 10 bullet points."""

def get_financial_document_types() -> List[str]:
    """Get list of supported financial document types"""
    return FINANCIAL_DOCUMENT_TYPES.copy()

def is_financial_document_type(document_type: str) -> bool:
    """Check if the provided document type is a financial document type"""
    return document_type in FINANCIAL_DOCUMENT_TYPES

def match_document_type(user_input: str) -> Optional[str]:
    """
    Match user input to one of the 20 financial document types
    Uses fuzzy matching to handle variations in naming
    """
    if not user_input or not user_input.strip():
        return None
    
    user_input = user_input.strip().lower()
    
    # Direct matches
    for doc_type in FINANCIAL_DOCUMENT_TYPES:
        if user_input == doc_type.lower():
            return doc_type
    
    # Fuzzy matching for common variations
    fuzzy_matches = {
        # Bank Statement variations
        "bank statement": "Bank Statement",
        "statement": "Bank Statement",
        "account statement": "Bank Statement",
        "monthly statement": "Bank Statement",
        
        # Payment Receipt variations
        "payment receipt": "Payment Receipt",
        "receipt": "Payment Receipt",
        "payment confirmation": "Payment Receipt",
        
        # Wire Transfer variations
        "wire transfer": "Wire Transfer Confirmation",
        "wire transfer confirmation": "Wire Transfer Confirmation",
        "transfer confirmation": "Wire Transfer Confirmation",
        "bank transfer": "Wire Transfer Confirmation",
        
        # Remittance variations
        "remittance": "Remittance Advice",
        "remittance advice": "Remittance Advice",
        "money transfer": "Remittance Advice",
        
        # Invoice variations
        "invoice": "Bank Invoice (for Services)",
        "bank invoice": "Bank Invoice (for Services)",
        "service invoice": "Bank Invoice (for Services)",
        
        # Loan variations
        "loan": "Loan Repayment Schedule",
        "loan repayment": "Loan Repayment Schedule",
        "repayment schedule": "Loan Repayment Schedule",
        "loan payment": "Loan Repayment Schedule",
        
        # Cheque variations
        "cheque": "Cheque/Check Stub",
        "check": "Cheque/Check Stub",
        "check stub": "Cheque/Check Stub",
        "cheque stub": "Cheque/Check Stub",
        
        # Deposit variations
        "deposit": "Deposit Slip",
        "deposit slip": "Deposit Slip",
        "deposit receipt": "Deposit Slip",
        
        # Credit Card variations
        "credit card": "Credit Card Statement",
        "credit card statement": "Credit Card Statement",
        "card statement": "Credit Card Statement",
        
        # Memo variations
        "debit memo": "Debit Memo",
        "credit memo": "Credit Memo",
        "memo": "Debit Memo",  # Default to debit memo
        
        # Draft variations
        "draft": "Bank Draft",
        "bank draft": "Bank Draft",
        "money order": "Bank Draft",
        
        # Overdraft variations
        "overdraft": "Overdraft Notice",
        "overdraft notice": "Overdraft Notice",
        "overdraft notification": "Overdraft Notice",
        
        # Interest variations
        "interest": "Interest Payment Confirmation",
        "interest payment": "Interest Payment Confirmation",
        "interest confirmation": "Interest Payment Confirmation",
        
        # Transaction variations
        "transaction": "Account Transaction Record",
        "transaction record": "Account Transaction Record",
        "account transaction": "Account Transaction Record",
        
        # Fees variations
        "fees": "Bank Fees Statement",
        "bank fees": "Bank Fees Statement",
        "fee statement": "Bank Fees Statement",
        
        # Statement of Account variations
        "statement of account": "Statement of Account",
        "account summary": "Statement of Account",
        
        # Letter of Credit variations
        "letter of credit": "Letter of Credit",
        "lc": "Letter of Credit",
        "credit letter": "Letter of Credit",
        
        # Bank Guarantee variations
        "guarantee": "Bank Guarantee",
        "bank guarantee": "Bank Guarantee",
        "guarantee letter": "Bank Guarantee",
        
        # Payment Plan variations
        "payment plan": "Payment Plan Agreement",
        "installment": "Payment Plan Agreement",
        "payment agreement": "Payment Plan Agreement"
    }
    
    # Check for fuzzy matches
    for key, value in fuzzy_matches.items():
        if key in user_input:
            return value
    
    # If no match found, return None
    return None

def get_prompt_template(document_type: str, analysis_type: str = "general") -> str:
    """
    Get the appropriate prompt template based on document type and analysis type
    
    Args:
        document_type: The type of document (financial or general)
        analysis_type: Type of analysis ("general", "financial", "rag")
    
    Returns:
        The appropriate prompt template
    """
    if analysis_type == "rag":
        return RAG_PROMPT_TEMPLATE
    elif analysis_type == "financial" or is_financial_document_type(document_type):
        return FINANCIAL_DOCUMENT_PROMPT_TEMPLATE
    else:
        return GENERAL_DOCUMENT_PROMPT_TEMPLATE

def format_prompt_template(template: str, **kwargs) -> str:
    """
    Format a prompt template with provided variables
    
    Args:
        template: The prompt template string
        **kwargs: Variables to substitute in the template
    
    Returns:
        Formatted prompt string
    """
    try:
        return template.format(**kwargs)
    except KeyError as e:
        logger.error(f"Missing variable in prompt template: {e}")
        return template

def get_document_type_suggestions(partial_input: str) -> List[str]:
    """
    Get document type suggestions based on partial input
    
    Args:
        partial_input: Partial user input
    
    Returns:
        List of matching document types
    """
    if not partial_input or len(partial_input) < 2:
        return FINANCIAL_DOCUMENT_TYPES[:5]  # Return first 5 as suggestions
    
    partial_input = partial_input.lower()
    suggestions = []
    
    for doc_type in FINANCIAL_DOCUMENT_TYPES:
        if partial_input in doc_type.lower():
            suggestions.append(doc_type)
    
    # If no matches, return first 5
    if not suggestions:
        suggestions = FINANCIAL_DOCUMENT_TYPES[:5]
    
    return suggestions[:10]  # Limit to 10 suggestions
