import os
import re
import logging
from typing import Dict, List, Optional, Tuple
import pdfminer.high_level as pdf_extract
from pdfminer.layout import LAParams

from src.core.config_loader import ConfigLoader

# Try to import VectorDB, but don't fail if not available
try:
    from src.utils.vector_db import VectorDB
    VECTOR_DB_AVAILABLE = True
except ImportError:
    logging.warning("VectorDB not available. Some features will be limited.")
    VECTOR_DB_AVAILABLE = False

logger = logging.getLogger(__name__)

class SourceLoader:
    """Loads and processes philosophical source materials"""
    
    def __init__(self, config_or_dir=None):
        """
        Initialize the source loader
        
        Args:
            config_or_dir: Configuration loader instance or path to sources directory
        """
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.sources_cache = {}
        
        # Handle different types of input
        if isinstance(config_or_dir, str):
            # If a string is provided, treat it as the sources directory
            self.config_loader = ConfigLoader()
            self.sources_dir = config_or_dir
        else:
            # Otherwise, treat it as a config loader
            self.config_loader = config_or_dir or ConfigLoader()
            self.sources_dir = "data/sources"  # Default directory
        
        # Initialize the vector database if available
        self.vector_db = None
        if VECTOR_DB_AVAILABLE:
            try:
                self.vector_db = VectorDB(db_path=os.path.join(self.base_dir, "data/vector_db"))
                self._load_sources_to_vector_db()
            except Exception as e:
                logger.warning(f"Failed to initialize VectorDB: {e}")
        
    def _load_sources_to_vector_db(self):
        """Load all sources into the vector database if not already loaded."""
        if not self.vector_db:
            logger.warning("Vector database not available. Skipping loading sources to vector db.")
            return
            
        # Check if the vector database already has documents
        stats = self.vector_db.get_stats()
        if stats.get('num_documents', 0) > 0:
            logger.info(f"Vector database already contains {stats['num_documents']} documents")
            return
            
        # Get all sources
        sources = self.get_all_sources(use_cache=False)
        if not sources:
            logger.warning("No sources found to load into vector database")
            return
            
        # Prepare documents for vector database
        logger.info(f"Loading {len(sources)} sources into vector database")
        
        # Split sources into paragraphs
        documents = []
        for source in sources:
            content = source["content"]
            paragraphs = re.split(r'\n\s*\n', content)
            
            for i, para in enumerate(paragraphs):
                para = para.strip()
                if len(para) < 50:  # Skip very short paragraphs
                    continue
                    
                documents.append({
                    'text': para,
                    'metadata': {
                        'source': source["name"],
                        'author': source["author"],
                        'paragraph_id': i,
                        'source_filename': source["source"]
                    }
                })
        
        # Add documents to vector database
        if documents:
            logger.info(f"Adding {len(documents)} paragraphs to vector database")
            self.vector_db.add_documents(documents)
            self.vector_db.save()
        else:
            logger.warning("No paragraphs found to add to vector database")
        
    def load_source(self, source_path: str) -> str:
        """
        Load source material from a file
        
        Args:
            source_path: Path to the source file
            
        Returns:
            String containing the source text
        """
        if source_path in self.sources_cache:
            return self.sources_cache[source_path]
            
        # Resolve the path (could be relative to the project)
        full_path = source_path
        if not os.path.isabs(source_path):
            full_path = os.path.join(self.base_dir, source_path)
            
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Source file not found: {full_path}")
            
        extension = os.path.splitext(full_path)[1].lower()
        
        if extension == '.pdf':
            text = self._extract_text_from_pdf(full_path)
        else:
            # Assume it's a text file
            with open(full_path, 'r', encoding='utf-8') as f:
                text = f.read()
                
        self.sources_cache[source_path] = text
        return text
        
    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from a PDF file"""
        with open(pdf_path, 'rb') as f:
            text = pdf_extract.extract_text(f, laparams=LAParams())
        return text
        
    def get_all_sources(self, use_cache=True) -> List[Dict[str, str]]:
        """
        Get all configured source materials
        
        Args:
            use_cache: Whether to use cached source content
            
        Returns:
            List of dicts with source info and content
        """
        sources = []
        
        # Get the sources directory path
        sources_path = self.sources_dir
        if not os.path.isabs(sources_path):
            sources_path = os.path.join(self.base_dir, sources_path)
        
        if not os.path.exists(sources_path):
            logger.warning(f"Sources directory not found: {sources_path}")
            return sources
        
        # Clear cache if not using it
        if not use_cache:
            self.sources_cache = {}
        
        # Read source files from the directory
        for filename in os.listdir(sources_path):
            file_path = os.path.join(sources_path, filename)
            
            # Skip directories
            if os.path.isdir(file_path):
                continue
                
            try:
                # Extract source name from the filename
                source_name = os.path.splitext(filename)[0].replace("_", " ").title()
                
                # Generate a unique ID for the source
                source_id = f"source_{len(sources)}"
                
                # Load source content
                source_text = self.load_source(file_path)
                
                sources.append({
                    "id": source_id,
                    "name": source_name,
                    "author": "Unknown",  # Default author
                    "content": source_text,
                    "weight": 1.0,  # Default weight
                    "source": filename
                })
            except Exception as e:
                logger.warning(f"Error loading source file {file_path}: {str(e)}")
                
        return sources
        
    def get_source_by_id(self, source_id: str) -> Optional[Dict[str, str]]:
        """Get a specific source by ID"""
        sources = self.get_all_sources()
        for source in sources:
            if source.get("id") == source_id:
                return source
        return None
        
    def get_source_by_name(self, name: str) -> Optional[Dict[str, str]]:
        """Get a specific source by name"""
        sources = self.get_all_sources()
        for source in sources:
            if source["name"].lower() == name.lower():
                return source
        return None
        
    def get_relevant_excerpts(self, query: str, max_excerpts: int = 3, 
                             excerpt_length: int = 500) -> List[Dict[str, str]]:
        """
        Get relevant excerpts from sources based on semantic search
        
        Args:
            query: The search query
            max_excerpts: Maximum number of excerpts to return
            excerpt_length: Approximate length of each excerpt
            
        Returns:
            List of relevant excerpts with source metadata
        """
        # Use vector DB if available
        if self.vector_db:
            try:
                logger.info(f"Performing semantic search for query: {query}")
                search_results = self.vector_db.search(query, top_k=max_excerpts)
                
                # Format results
                results = []
                for result in search_results:
                    para = result['text']
                    
                    # Trim to approximate length if needed
                    if len(para) > excerpt_length:
                        end_pos = para.rfind('. ', 0, excerpt_length) + 1
                        if end_pos <= 0:
                            end_pos = excerpt_length
                        para = para[:end_pos] + '...'
                    
                    results.append({
                        "text": para,
                        "source": result['metadata']['source'],
                        "author": result['metadata']['author'],
                        "relevance": result['score']
                    })
                
                # If we got enough results, return them
                if len(results) >= max_excerpts:
                    return results
                
                # Otherwise supplement with keyword search
                logger.info("Not enough results from semantic search, supplementing with keyword matching")
                keyword_results = self._get_relevant_excerpts_keyword(
                    query, 
                    max_excerpts - len(results), 
                    excerpt_length
                )
                
                # Filter out duplicates
                existing_texts = {r['text'][:100] for r in results}
                for result in keyword_results:
                    if result['text'][:100] not in existing_texts:
                        results.append(result)
                        if len(results) >= max_excerpts:
                            break
                
                return results
            except Exception as e:
                logger.error(f"Error using vector database for search: {e}")
                # Fall back to keyword search
                
        # Fallback to keyword search
        return self._get_relevant_excerpts_keyword(query, max_excerpts, excerpt_length)
        
    def _get_relevant_excerpts_keyword(self, query: str, max_excerpts: int = 3, 
                                     excerpt_length: int = 500) -> List[Dict[str, str]]:
        """
        Fallback method to get relevant excerpts based on keyword matching
        
        Args:
            query: The search query
            max_excerpts: Maximum number of excerpts to return
            excerpt_length: Approximate length of each excerpt
            
        Returns:
            List of relevant excerpts with source metadata
        """
        sources = self.get_all_sources()
        results = []
        
        # Simple approach: look for keyword matches
        keywords = set(re.findall(r'\w+', query.lower()))
        
        for source in sources:
            content = source["content"].lower()
            
            # Find paragraphs with the most keyword matches
            paragraphs = re.split(r'\n\s*\n', content)
            scored_paragraphs = []
            
            for para in paragraphs:
                if len(para.strip()) < 50:  # Skip very short paragraphs
                    continue
                    
                # Count keyword matches
                score = sum(1 for keyword in keywords if keyword in para)
                if score > 0:
                    scored_paragraphs.append((score, para))
                    
            # Sort by score and take top matches
            scored_paragraphs.sort(reverse=True)
            
            for score, para in scored_paragraphs[:2]:  # Take top 2 from each source
                if len(results) >= max_excerpts:
                    break
                    
                # Trim to approximate length
                if len(para) > excerpt_length:
                    # Try to find a good breaking point
                    end_pos = para.rfind('. ', 0, excerpt_length) + 1
                    if end_pos <= 0:
                        end_pos = excerpt_length
                    para = para[:end_pos] + '...'
                    
                results.append({
                    "text": para,
                    "source": source["name"],
                    "author": source["author"],
                    "relevance": score / len(keywords) if keywords else 0  # Normalize score
                })
                
            if len(results) >= max_excerpts:
                break
                
        return results
        
    def add_source(self, source_path: str, source_name: str = None, author: str = "Unknown") -> bool:
        """
        Add a new source file to the database and vector database
        
        Args:
            source_path: Path to the source file
            source_name: Name of the source (defaults to filename)
            author: Author of the source
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load the source
            source_text = self.load_source(source_path)
            
            # Extract filename
            filename = os.path.basename(source_path)
            
            # Use provided name or extract from filename
            if not source_name:
                source_name = os.path.splitext(filename)[0].replace("_", " ").title()
            
            # Prepare source document
            source_id = f"source_{len(self.get_all_sources())}"
            source = {
                "id": source_id,
                "name": source_name,
                "author": author,
                "content": source_text,
                "weight": 1.0,
                "source": filename
            }
            
            # Add to vector database if available
            if self.vector_db:
                content = source["content"]
                paragraphs = re.split(r'\n\s*\n', content)
                
                documents = []
                for i, para in enumerate(paragraphs):
                    para = para.strip()
                    if len(para) < 50:  # Skip very short paragraphs
                        continue
                        
                    documents.append({
                        'text': para,
                        'metadata': {
                            'source': source["name"],
                            'author': source["author"],
                            'paragraph_id': i,
                            'source_filename': source["source"]
                        }
                    })
                
                if documents:
                    logger.info(f"Adding {len(documents)} paragraphs from new source to vector database")
                    self.vector_db.add_documents(documents)
                    self.vector_db.save()
            
            return True
        except Exception as e:
            logger.error(f"Error adding source {source_path}: {str(e)}")
            return False 
 