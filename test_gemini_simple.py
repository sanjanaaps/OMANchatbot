import os
import google.generativeai as genai
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configure Gemini
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

def test_simple_query():
    model = genai.GenerativeModel('gemini-pro')
    
    # Simple test prompt
    prompt = "What is 2+2? Just give me the number."
    
    try:
        response = model.generate_content(prompt)
        print(f"\nQuery: {prompt}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_simple_query()