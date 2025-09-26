#!/usr/bin/env python3
"""
FAQ Service for Central Bank of Oman
Parses and provides access to the comprehensive FAQ knowledge base
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class CBOFAQService:
    """Service to handle CBO FAQ knowledge base"""
    
    def __init__(self, faq_file_path: str = "uploads/cbo_faq_mapping.md"):
        self.faq_file_path = faq_file_path
        self.faq_data: Dict[str, str] = {}
        self.categories: Dict[str, List[str]] = {}
        self.load_faq_data()
    
    def load_faq_data(self):
        """Load and parse FAQ data from markdown file"""
        try:
            with open(self.faq_file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            self._parse_faq_content(content)
            logger.info(f"Loaded {len(self.faq_data)} FAQ entries from {self.faq_file_path}")
            
        except Exception as e:
            logger.error(f"Failed to load FAQ data: {str(e)}")
            self.faq_data = {}
            self.categories = {}
    
    def _parse_faq_content(self, content: str):
        """Parse FAQ content from markdown format"""
        # Split content into sections
        sections = re.split(r'^## ', content, flags=re.MULTILINE)
        
        current_category = "General"
        
        for section in sections:
            if not section.strip():
                continue
                
            lines = section.strip().split('\n')
            if not lines:
                continue
                
            # First line is the category title
            if lines[0].strip():
                current_category = lines[0].strip()
                if current_category not in self.categories:
                    self.categories[current_category] = []
            
            # Parse Q&A pairs in this section
            section_content = '\n'.join(lines[1:])
            qa_pairs = self._extract_qa_pairs(section_content)
            
            for question, answer in qa_pairs:
                self.faq_data[question] = answer
                self.categories[current_category].append(question)
    
    def _extract_qa_pairs(self, content: str) -> List[Tuple[str, str]]:
        """Extract Q&A pairs from content"""
        qa_pairs = []
        
        # Pattern to match Q: and A: pairs
        pattern = r'\*\*Q:\s*(.*?)\*\*\s*A:\s*(.*?)(?=\*\*Q:|$)'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for question, answer in matches:
            # Clean up the question and answer
            question = question.strip()
            answer = answer.strip()
            
            if question and answer:
                qa_pairs.append((question, answer))
        
        return qa_pairs
    
    def find_best_match(self, user_question: str, threshold: float = 0.3) -> Optional[Tuple[str, str]]:
        """Find the best matching FAQ entry for a user question"""
        if not self.faq_data:
            return None
        
        user_question_lower = user_question.lower().strip()
        best_match = None
        best_score = 0
        
        for faq_question, faq_answer in self.faq_data.items():
            # Calculate similarity score with improved matching
            score = self._calculate_improved_similarity(user_question_lower, faq_question.lower())
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = (faq_question, faq_answer)
        
        return best_match
    
    def _calculate_improved_similarity(self, user_question: str, faq_question: str) -> float:
        """Calculate improved similarity between user question and FAQ question"""
        # Extract key terms from both questions
        user_words = set(user_question.split())
        faq_words = set(faq_question.split())
        
        # Define important keywords that should match exactly
        important_keywords = {
            'central', 'bank', 'currency', 'rial', 'omr', 'oman', 'cbo',
            'governor', 'established', 'mission', 'headquarters', 'policy',
            'monetary', 'supervision', 'regulation', 'payment', 'system',
            'rtgs', 'ach', 'wps', 'maal', 'fintech', 'islamic', 'sharia'
        }
        
        # Check for exact keyword matches (higher weight)
        user_important = user_words.intersection(important_keywords)
        faq_important = faq_words.intersection(important_keywords)
        
        # If both have important keywords, check if they match
        if user_important and faq_important:
            important_match = len(user_important.intersection(faq_important)) / max(len(user_important), len(faq_important))
        else:
            important_match = 0
        
        # Check for conflicting keywords (should reduce score)
        conflicting_pairs = [
            (['central', 'bank'], ['currency', 'rial']),
            (['currency', 'rial'], ['central', 'bank']),
            (['governor'], ['currency', 'rial']),
            (['currency', 'rial'], ['governor']),
            (['established'], ['currency', 'rial']),
            (['currency', 'rial'], ['established']),
            (['currency'], ['auction', 'cd', 'deposit']),  # Currency vs CD auctions
            (['auction', 'cd', 'deposit'], ['currency'])   # CD auctions vs Currency
        ]
        
        conflict_penalty = 0
        for user_conflict, faq_conflict in conflicting_pairs:
            if (any(word in user_words for word in user_conflict) and 
                any(word in faq_words for word in faq_conflict)):
                conflict_penalty = 0.4  # Increased penalty for conflicting concepts
                break
        
        # Basic similarity using SequenceMatcher
        basic_similarity = SequenceMatcher(None, user_question, faq_question).ratio()
        
        # Word overlap similarity
        common_words = user_words.intersection(faq_words)
        if user_words or faq_words:
            word_overlap = len(common_words) / max(len(user_words), len(faq_words))
        else:
            word_overlap = 0
        
        # Calculate final score with weights
        # Important keyword matches get high weight
        # Basic similarity gets medium weight
        # Word overlap gets low weight
        # Conflict penalty reduces the score
        final_score = (
            important_match * 0.4 +           # 40% weight for important keyword matches
            basic_similarity * 0.4 +          # 40% weight for basic similarity
            word_overlap * 0.2                # 20% weight for general word overlap
        ) - conflict_penalty                  # Subtract conflict penalty
        
        return max(0, final_score)  # Ensure score is not negative
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts (legacy method)"""
        # Use SequenceMatcher for basic similarity
        basic_similarity = SequenceMatcher(None, text1, text2).ratio()
        
        # Check for keyword matches
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return basic_similarity
        
        # Calculate keyword overlap
        common_words = words1.intersection(words2)
        keyword_similarity = len(common_words) / max(len(words1), len(words2))
        
        # Combine both scores
        combined_score = (basic_similarity * 0.6) + (keyword_similarity * 0.4)
        
        return combined_score
    
    def search_by_keywords(self, keywords: List[str]) -> List[Tuple[str, str]]:
        """Search FAQ by keywords"""
        if not self.faq_data:
            return []
        
        results = []
        keywords_lower = [kw.lower() for kw in keywords]
        
        for question, answer in self.faq_data.items():
            question_lower = question.lower()
            answer_lower = answer.lower()
            
            # Check if any keyword appears in question or answer
            for keyword in keywords_lower:
                if keyword in question_lower or keyword in answer_lower:
                    results.append((question, answer))
                    break
        
        return results
    
    def get_category_questions(self, category: str) -> List[str]:
        """Get all questions in a specific category"""
        return self.categories.get(category, [])
    
    def get_all_categories(self) -> List[str]:
        """Get all available categories"""
        return list(self.categories.keys())
    
    def get_random_question(self) -> Optional[Tuple[str, str]]:
        """Get a random FAQ question and answer"""
        if not self.faq_data:
            return None
        
        import random
        question = random.choice(list(self.faq_data.keys()))
        return question, self.faq_data[question]
    
    def get_faq_count(self) -> int:
        """Get total number of FAQ entries"""
        return len(self.faq_data)
    
    def is_loaded(self) -> bool:
        """Check if FAQ data is loaded"""
        return len(self.faq_data) > 0

# Global FAQ service instance
faq_service = None

def get_faq_service() -> CBOFAQService:
    """Get the global FAQ service instance"""
    global faq_service
    if faq_service is None:
        faq_service = CBOFAQService()
    return faq_service

def initialize_faq_service():
    """Initialize the FAQ service"""
    global faq_service
    faq_service = CBOFAQService()
    return faq_service
