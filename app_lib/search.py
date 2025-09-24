import re
import math
from collections import Counter
from typing import List, Dict, Tuple
import logging
from app_lib.db import get_db

logger = logging.getLogger(__name__)

class TFIDFSearch:
    """TF-IDF based document search with cosine similarity"""
    
    def __init__(self):
        self.documents = []
        self.vocabulary = set()
        self.tf_matrix = []
        self.idf_scores = {}
        self.document_vectors = []
    
    def build_index(self, documents: List[Dict]):
        """Build TF-IDF index from documents"""
        self.documents = documents
        
        if not documents:
            return
        
        # Extract text and build vocabulary
        texts = []
        for doc in documents:
            text = doc.get('content', '')
            # Simple tokenization and cleaning
            tokens = self._tokenize(text)
            texts.append(tokens)
            self.vocabulary.update(tokens)
        
        self.vocabulary = list(self.vocabulary)
        
        # Calculate TF matrix
        self.tf_matrix = []
        for tokens in texts:
            tf_vector = [0] * len(self.vocabulary)
            token_count = Counter(tokens)
            total_tokens = len(tokens)
            
            for i, term in enumerate(self.vocabulary):
                tf_vector[i] = token_count.get(term, 0) / total_tokens
            
            self.tf_matrix.append(tf_vector)
        
        # Calculate IDF scores
        total_docs = len(documents)
        for i, term in enumerate(self.vocabulary):
            docs_with_term = sum(1 for tf_vector in self.tf_matrix if tf_vector[i] > 0)
            self.idf_scores[term] = math.log(total_docs / docs_with_term) if docs_with_term > 0 else 0
        
        # Calculate document vectors (TF-IDF)
        self.document_vectors = []
        for tf_vector in self.tf_matrix:
            doc_vector = []
            for i, term in enumerate(self.vocabulary):
                tf_idf = tf_vector[i] * self.idf_scores[term]
                doc_vector.append(tf_idf)
            self.document_vectors.append(doc_vector)
    
    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """Search documents using TF-IDF and cosine similarity"""
        if not self.documents or not self.vocabulary:
            return []
        
        # Tokenize query
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        
        # Calculate query vector
        query_vector = [0] * len(self.vocabulary)
        query_count = Counter(query_tokens)
        total_query_tokens = len(query_tokens)
        
        for i, term in enumerate(self.vocabulary):
            if term in query_count:
                tf = query_count[term] / total_query_tokens
                idf = self.idf_scores.get(term, 0)
                query_vector[i] = tf * idf
        
        # Calculate cosine similarity
        similarities = []
        for i, doc_vector in enumerate(self.document_vectors):
            similarity = self._cosine_similarity(query_vector, doc_vector)
            if similarity > 0:
                similarities.append((i, similarity))
        
        # Sort by similarity and return top results
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_idx, score in similarities[:top_k]:
            doc = self.documents[doc_idx]
            # Create excerpt from content
            excerpt = self._create_excerpt(doc.get('content', ''), query_tokens)
            
            results.append({
                'document_id': str(doc.get('_id', '')),
                'filename': doc.get('filename', ''),
                'content': doc.get('content', ''),
                'excerpt': excerpt,
                'score': score,
                'upload_date': doc.get('upload_date'),
                'uploaded_by': doc.get('uploaded_by', '')
            })
        
        return results
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization and cleaning"""
        if not text:
            return []
        
        # Convert to lowercase and remove special characters
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Split into tokens and remove empty strings
        tokens = [token for token in text.split() if len(token) > 2]
        
        return tokens
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not vec1 or not vec2:
            return 0.0
        
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # Calculate magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _create_excerpt(self, content: str, query_tokens: List[str], max_length: int = 200) -> str:
        """Create an excerpt highlighting query terms"""
        if not content or not query_tokens:
            return content[:max_length] + "..." if len(content) > max_length else content
        
        content_lower = content.lower()
        
        # Find the best position to start the excerpt
        best_position = 0
        max_matches = 0
        
        for i in range(len(content) - max_length + 1):
            excerpt = content_lower[i:i + max_length]
            matches = sum(1 for token in query_tokens if token in excerpt)
            if matches > max_matches:
                max_matches = matches
                best_position = i
        
        excerpt = content[best_position:best_position + max_length]
        
        # Add ellipsis if needed
        if best_position > 0:
            excerpt = "..." + excerpt
        if best_position + max_length < len(content):
            excerpt = excerpt + "..."
        
        return excerpt

def search_documents(query: str, department: str, top_k: int = 10) -> List[Dict]:
    """
    Search documents in a specific department
    
    Args:
        query: Search query
        department: Department to search in
        top_k: Number of top results to return
        
    Returns:
        List of search results
    """
    try:
        db = get_db()
        
        # Get documents for the department
        documents = list(db.documents.find({'department': department}))
        
        if not documents:
            return []
        
        # Build search index
        searcher = TFIDFSearch()
        searcher.build_index(documents)
        
        # Perform search
        results = searcher.search(query, top_k)
        
        return results
    
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        return []

def get_document_summary(text: str, max_sentences: int = 3) -> str:
    """
    Generate extractive summary using TextRank algorithm
    
    Args:
        text: Text to summarize
        max_sentences: Maximum number of sentences in summary
        
    Returns:
        Summary text
    """
    try:
        from sumy.parsers.plaintext import PlaintextParser
        from sumy.nlp.tokenizers import Tokenizer
        from sumy.summarizers.text_rank import TextRankSummarizer
        
        if not text or len(text.strip()) < 100:
            return text
        
        # Parse text
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        
        # Create summarizer
        summarizer = TextRankSummarizer()
        
        # Generate summary
        summary_sentences = summarizer(parser.document, max_sentences)
        
        # Join sentences
        summary = ' '.join(str(sentence) for sentence in summary_sentences)
        
        return summary if summary.strip() else text[:500] + "..."
    
    except ImportError:
        logger.warning("sumy library not available, using simple extractive summary")
        return _simple_extractive_summary(text, max_sentences)
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return _simple_extractive_summary(text, max_sentences)

def _simple_extractive_summary(text: str, max_sentences: int = 3) -> str:
    """Simple extractive summary as fallback"""
    if not text:
        return ""
    
    # Split into sentences
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if len(sentences) <= max_sentences:
        return text
    
    # Simple scoring based on length and position
    scored_sentences = []
    for i, sentence in enumerate(sentences):
        score = len(sentence.split())  # Word count
        if i < len(sentences) * 0.1:  # Boost first 10%
            score *= 1.2
        scored_sentences.append((score, sentence))
    
    # Sort by score and take top sentences
    scored_sentences.sort(key=lambda x: x[0], reverse=True)
    top_sentences = [s[1] for s in scored_sentences[:max_sentences]]
    
    return '. '.join(top_sentences) + '.'