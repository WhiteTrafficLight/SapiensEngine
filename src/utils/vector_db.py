"""
Vector Database Module for Sapiens Engine.

This module provides a vector database implementation using sentence-transformers
for embeddings and FAISS for efficient similarity search. It's designed to store
and retrieve philosophical text excerpts based on semantic similarity.
"""

import os
import json
import logging
import pickle
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Try to import sentence_transformers, but don't fail if not available
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("sentence_transformers not available. Vector DB will operate in limited mode.")
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# Try to import FAISS, but don't fail if not available
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    logger.warning("faiss-cpu not available. Vector DB will operate in limited mode.")
    FAISS_AVAILABLE = False

class VectorDB:
    """
    A vector database for efficient semantic search of philosophical texts.
    
    Attributes:
        model_name (str): The name of the sentence-transformers model to use.
        embedding_dim (int): The dimension of the embeddings.
        index (faiss.Index): The FAISS index for similarity search.
        documents (List[Dict]): The list of documents stored in the database.
        db_path (str): Path where the database is saved.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", db_path: str = "data/vector_db"):
        """
        Initialize the VectorDB.
        
        Args:
            model_name (str): The name of the sentence-transformers model to use.
            db_path (str): Path where the database will be saved.
        """
        self.model_name = model_name
        self.documents = []
        self.embeddings = None
        self.index = None
        self.model = None
        self.db_path = db_path
        
        # Create the directory if it doesn't exist
        os.makedirs(db_path, exist_ok=True)
        
        # Load existing database if available
        self._load()
        
        logger.info(f"Initialized VectorDB with model {model_name}")
    
    def _load(self):
        """Load an existing vector database from disk."""
        documents_path = os.path.join(self.db_path, "documents.json")
        embeddings_path = os.path.join(self.db_path, "embeddings.pkl")
        index_path = os.path.join(self.db_path, "faiss_index.bin")
        
        # Check if files exist
        if os.path.exists(documents_path) and os.path.exists(embeddings_path):
            try:
                # Load documents
                with open(documents_path, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
                
                # Load embeddings
                with open(embeddings_path, "rb") as f:
                    self.embeddings = pickle.load(f)
                
                # Load FAISS index if available
                if FAISS_AVAILABLE and os.path.exists(index_path):
                    self.index = faiss.read_index(index_path)
                    
                logger.info(f"Loaded vector database with {len(self.documents)} documents")
            except Exception as e:
                logger.error(f"Error loading vector database: {str(e)}")
                # Reset to empty state
                self.documents = []
                self.embeddings = None
                self.index = None
        else:
            logger.info("No existing vector database found. Starting with empty database.")
    
    def add_document(self, doc: Dict[str, Any]) -> int:
        """
        Add a document to the database.
        
        Args:
            doc (Dict): The document to add. Must contain at least 'text' and 'metadata' fields.
            
        Returns:
            int: The ID of the added document.
        """
        if 'text' not in doc:
            raise ValueError("Document must contain 'text' field")
        
        # Generate embedding
        embedding = self.model.encode([doc['text']])[0]
        
        # Add to FAISS index
        faiss.normalize_L2(np.array([embedding], dtype=np.float32))
        self.index.add(np.array([embedding], dtype=np.float32))
        
        # Store document
        doc_id = len(self.documents)
        self.documents.append({
            'id': doc_id,
            'text': doc['text'],
            'metadata': doc.get('metadata', {})
        })
        
        logger.debug(f"Added document with ID {doc_id} to VectorDB")
        return doc_id
    
    def add_documents(self, docs: List[Dict[str, Any]]) -> List[int]:
        """
        Add multiple documents to the database.
        
        Args:
            docs (List[Dict]): The documents to add.
            
        Returns:
            List[int]: The IDs of the added documents.
        """
        if not docs:
            return []
            
        # Validate documents
        for doc in docs:
            if 'text' not in doc:
                raise ValueError("All documents must contain 'text' field")
        
        # Generate embeddings for all documents
        texts = [doc['text'] for doc in docs]
        embeddings = self.model.encode(texts)
        faiss.normalize_L2(embeddings)
        
        # Add to FAISS index
        self.index.add(embeddings)
        
        # Store documents
        start_id = len(self.documents)
        doc_ids = []
        
        for i, doc in enumerate(docs):
            doc_id = start_id + i
            self.documents.append({
                'id': doc_id,
                'text': doc['text'],
                'metadata': doc.get('metadata', {})
            })
            doc_ids.append(doc_id)
        
        logger.info(f"Added {len(docs)} documents to VectorDB")
        return doc_ids
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for documents similar to the query.
        
        Args:
            query (str): The search query.
            top_k (int): The number of results to return.
            
        Returns:
            List[Dict]: The search results, each containing the document and its similarity score.
        """
        if not self.documents:
            logger.warning("VectorDB is empty. No results returned.")
            return []
            
        if not SENTENCE_TRANSFORMERS_AVAILABLE or self.model is None:
            logger.warning("Sentence transformers not available. Cannot perform semantic search.")
            # Fallback to keyword search
            return self._keyword_search(query, top_k)
            
        try:
            # Generate query embedding
            query_embedding = self.model.encode([query], convert_to_numpy=True)
            
            if FAISS_AVAILABLE and self.index is not None:
                # Use FAISS for search
                scores, indices = self.index.search(query_embedding, top_k)
                
                # Format results
                results = []
                for i, idx in enumerate(indices[0]):
                    if idx < 0 or idx >= len(self.documents):  # Skip invalid indices
                        continue
                        
                    doc = self.documents[idx]
                    results.append({
                        'id': doc['id'],
                        'text': doc['text'],
                        'metadata': doc['metadata'],
                        'score': float(scores[0][i])  # Convert distance to similarity score
                    })
                
                return results
            elif self.embeddings is not None:
                # Manual search with numpy
                # Compute dot product between query and documents
                scores = np.dot(query_embedding, self.embeddings.T)[0]
                
                # Get top k indices
                top_indices = np.argsort(scores)[::-1][:top_k]
                
                # Extract results
                results = []
                for idx in top_indices:
                    doc = self.documents[idx]
                    results.append({
                        'id': doc['id'],
                        'text': doc['text'],
                        'metadata': doc['metadata'],
                        'score': float(scores[idx])
                    })
                    
                return results
            else:
                logger.warning("No embeddings available. Falling back to keyword search.")
                return self._keyword_search(query, top_k)
                
        except Exception as e:
            logger.error(f"Error performing semantic search: {str(e)}")
            # Fallback to keyword search
            return self._keyword_search(query, top_k)
    
    def _keyword_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Simple keyword search as a fallback when embeddings are not available."""
        if not self.documents:
            return []
            
        # Simple approach: count matching words
        query_words = set(query.lower().split())
        
        # Score documents by matching words
        scored_docs = []
        for i, doc in enumerate(self.documents):
            text = doc["text"].lower()
            score = sum(word in text for word in query_words) / len(query_words)
            scored_docs.append((score, i))
            
        # Sort by score and take top_k
        scored_docs.sort(reverse=True)
        top_docs = scored_docs[:top_k]
        
        # Extract results
        results = []
        for score, idx in top_docs:
            if score > 0:  # Only include results with at least one matching word
                doc = self.documents[idx]
                results.append({
                    'id': doc['id'],
                    'text': doc['text'],
                    'metadata': doc['metadata'],
                    'score': score
                })
                
        return results
    
    def save(self) -> None:
        """Save the database to disk."""
        documents_path = os.path.join(self.db_path, "documents.json")
        embeddings_path = os.path.join(self.db_path, "embeddings.pkl")
        index_path = os.path.join(self.db_path, "faiss_index.bin")
        
        # Save documents
        with open(documents_path, 'w', encoding='utf-8') as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)
        
        # Save embeddings
        if self.embeddings is not None:
            with open(embeddings_path, 'wb') as f:
                pickle.dump(self.embeddings, f)
        
        # Save FAISS index
        if FAISS_AVAILABLE and self.index is not None:
            faiss.write_index(self.index, index_path)
        
        logger.info(f"VectorDB saved to {self.db_path}")
    
    def get_document(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID.
        
        Args:
            doc_id (int): The document ID.
            
        Returns:
            Dict or None: The document if found, None otherwise.
        """
        if 0 <= doc_id < len(self.documents):
            return self.documents[doc_id]
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dict: Statistics about the database.
        """
        return {
            'num_documents': len(self.documents),
            'has_embeddings': self.embeddings is not None,
            'has_index': self.index is not None,
            'embedding_dimension': self.embeddings.shape[1] if self.embeddings is not None else None,
            'model_name': self.model_name,
            'db_path': self.db_path
        } 
 