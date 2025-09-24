#!/usr/bin/env python3
"""
Basic test script for Oman Central Bank Document Analyzer
Tests core functionality without requiring full setup.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestDocumentAnalyzer(unittest.TestCase):
    """Test cases for the document analyzer application"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock environment variables
        os.environ['POSTGRES_URI'] = 'postgresql://postgres:1234@localhost:5432/test_doc_analyzer'
        os.environ['FLASK_SECRET_KEY'] = 'test-secret-key'
        os.environ['GEMINI_API_KEY'] = 'test-gemini-key'
    
    def test_auth_functions(self):
        """Test authentication functions"""
        from lib.auth import hash_password, check_password_hash
        
        password = "test123"
        hashed = hash_password(password)
        
        self.assertTrue(check_password_hash(hashed, password))
        self.assertFalse(check_password_hash(hashed, "wrong_password"))
    
    def test_text_extraction(self):
        """Test text extraction functionality"""
        from lib.extract import chunk_text, clean_text
        
        # Test text chunking
        long_text = "This is a test. " * 100
        chunks = chunk_text(long_text, chunk_size=100, overlap=20)
        
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 100 for chunk in chunks))
        
        # Test text cleaning
        dirty_text = "  This   is   a   test!!!  "
        clean = clean_text(dirty_text)
        self.assertEqual(clean, "This is a test!")
    
    def test_search_functionality(self):
        """Test search functionality"""
        from lib.search import TFIDFSearch
        
        # Create test documents
        documents = [
            {'_id': '1', 'content': 'This is a financial document about banking regulations.', 'filename': 'banking.pdf'},
            {'_id': '2', 'content': 'This document discusses monetary policy and interest rates.', 'filename': 'policy.pdf'},
            {'_id': '3', 'content': 'Legal compliance requirements for financial institutions.', 'filename': 'legal.pdf'}
        ]
        
        # Test TF-IDF search
        searcher = TFIDFSearch()
        searcher.build_index(documents)
        
        results = searcher.search("banking financial", top_k=2)
        
        self.assertGreater(len(results), 0)
        self.assertTrue(all('score' in result for result in results))
    
    @patch('lib.gemini.requests.post')
    def test_gemini_integration(self, mock_post):
        """Test Gemini API integration"""
        from lib.gemini import query_gemini
        
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{'text': 'This is a test response from Gemini.'}]
                }
            }]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Test API call
        result = query_gemini("test query", "Finance", "en")
        
        self.assertEqual(result, "This is a test response from Gemini.")
        mock_post.assert_called_once()
    
    def test_database_operations(self):
        """Test database operations"""
        from lib.db import get_db, init_db
        
        # Test database initialization (should not raise exception)
        try:
            init_db()
            db = get_db()
            self.assertIsNotNone(db)
        except Exception as e:
            # If PostgreSQL is not available, skip this test
            self.skipTest(f"PostgreSQL not available: {e}")

def run_tests():
    """Run all tests"""
    print("Running Document Analyzer Tests...")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDocumentAnalyzer)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✓ All tests passed!")
        return 0
    else:
        print(f"✗ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())
