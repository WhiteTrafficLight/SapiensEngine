"""
RAG Retrieval Module

Contains components for retrieval-augmented generation including:
- RAGManager: Main interface for various search algorithms
- VectorStore: Vector database management
- WebRetriever: Web-based information retrieval
- SourceLoader: Document loading and processing
"""

from .rag_manager import RAGManager

__all__ = ["RAGManager"] 