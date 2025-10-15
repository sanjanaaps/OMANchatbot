import os
import sys
from app_lib.gemini import query_gemini
from app_lib.extract import extract_text_from_file
import logging

# Set Gemini API key
os.environ['GEMINI_API_KEY'] = 'AIzaSyBX5T_0LqeeVa6Bu5y7MOAHSKngF547920'

# Set up logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_gemini_with_pdf():
    """Test Gemini API response with PDF context"""
    # Check for Gemini API key
    if not os.environ.get('GEMINI_API_KEY'):
        logger.error("❌ GEMINI_API_KEY environment variable is not set")
        logger.info("Please set the GEMINI_API_KEY environment variable and try again")
        return
    # Test parameters
    test_query = "What are the key financial metrics mentioned in the document and what is the budget increase percentage for FY2025?"
    department = "Finance"
    language = "en"
    
    # Test file path - using text file for testing
    test_file = "uploads/test_document.txt"
    
    if not os.path.exists(test_file):
        logger.error(f"Test file not found: {test_file}")
        logger.info("Please place a test PDF file in the uploads directory")
        return
    
    logger.info(f"Testing with file: {test_file}")
    
    # Extract text from PDF
    try:
        extracted_text = extract_text_from_file(test_file)
        if not extracted_text.strip():
            logger.error("No text extracted from PDF")
            return
        logger.info(f"Successfully extracted {len(extracted_text)} characters from PDF")
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return
        
    # Test Gemini API with extracted text
    logger.info("Testing Gemini API with PDF context...")
    logger.info("\nDocument Content Preview:")
    logger.info("-" * 50)
    logger.info(extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text)
    logger.info("-" * 50)
    try:
        response = query_gemini(test_query, department, language, extracted_text)
        logger.info("\nTest Results:")
        logger.info("-" * 50)
        logger.info(f"Query: {test_query}")
        logger.info(f"Department: {department}")
        logger.info(f"Context length: {len(extracted_text)} characters")
        logger.info(f"Response length: {len(response)} characters")
        logger.info("-" * 50)
        logger.info("Gemini Response:")
        logger.info(response)
        
        # Verify response quality
        if "Hello! I'm your AI assistant" in response or "How can I assist you today" in response:
            logger.warning("⚠️ Got generic response from Gemini - context may not be properly used")
        else:
            logger.info("✅ Received specific response from Gemini")
        
    except Exception as e:
        logger.error(f"Error querying Gemini API: {str(e)}")
        return

if __name__ == "__main__":
    test_gemini_with_pdf()