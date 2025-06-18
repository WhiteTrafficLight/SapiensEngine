import os
import re
import requests
from typing import Dict, List, Any, Optional, Union
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class UserContextManager:
    """
    Manages user-provided context that can be used in philosophical dialogues.
    Handles text files, URLs, and direct text input.
    """
    
    def __init__(self, max_context_length: int = 4000):
        """
        Initialize the context manager.
        
        Args:
            max_context_length: Maximum length of context to be included in prompts
        """
        self.max_context_length = max_context_length
        self.user_contexts = {}  # Dictionary to store user contexts by ID
        self.active_contexts = []  # List of active context IDs for current simulation
    
    def add_text_context(self, text: str, title: str = "User Input") -> str:
        """
        Add directly provided text as context.
        
        Args:
            text: The text content to add
            title: A title for this context
            
        Returns:
            The ID of the added context
        """
        context_id = f"ctx_{len(self.user_contexts) + 1}"
        self.user_contexts[context_id] = {
            "title": title,
            "type": "text",
            "content": text,
            "source": "user_input",
            "excerpt_length": min(len(text), self.max_context_length)
        }
        
        if context_id not in self.active_contexts:
            self.active_contexts.append(context_id)
            
        return context_id
    
    def add_file_context(self, file_path: str) -> str:
        """
        Add context from a text file.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            The ID of the added context
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            file_name = os.path.basename(file_path)
            context_id = f"ctx_{len(self.user_contexts) + 1}"
            
            self.user_contexts[context_id] = {
                "title": file_name,
                "type": "file",
                "content": content,
                "source": file_path,
                "excerpt_length": min(len(content), self.max_context_length)
            }
            
            if context_id not in self.active_contexts:
                self.active_contexts.append(context_id)
                
            return context_id
            
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            raise
    
    def add_url_context(self, url: str) -> str:
        """
        Add context from a URL (extracts main text content).
        
        Args:
            url: URL to extract content from
            
        Returns:
            The ID of the added context
        """
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
                
            # Get main text content
            text = soup.get_text()
            
            # Break into lines and remove leading and trailing space
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            content = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Get page title
            title = soup.title.string if soup.title else url
            
            context_id = f"ctx_{len(self.user_contexts) + 1}"
            
            # Truncate content if needed
            truncated_content = content[:self.max_context_length]
            
            self.user_contexts[context_id] = {
                "title": title,
                "type": "url",
                "content": truncated_content,
                "source": url,
                "excerpt_length": min(len(content), self.max_context_length)
            }
            
            if context_id not in self.active_contexts:
                self.active_contexts.append(context_id)
                
            return context_id
            
        except Exception as e:
            logger.error(f"Error fetching URL {url}: {str(e)}")
            raise
    
    def set_active_contexts(self, context_ids: List[str]):
        """
        Set which contexts should be active for the current simulation.
        
        Args:
            context_ids: List of context IDs to activate
        """
        # Verify all IDs exist
        for ctx_id in context_ids:
            if ctx_id not in self.user_contexts:
                raise ValueError(f"Context ID {ctx_id} does not exist")
                
        self.active_contexts = context_ids.copy()
    
    def get_relevant_contexts(self, topic: str, max_contexts: int = 3) -> List[Dict[str, Any]]:
        """
        Get contexts most relevant to the given topic.
        
        Args:
            topic: The topic to find relevant contexts for
            max_contexts: Maximum number of contexts to return
            
        Returns:
            List of relevant context dictionaries
        """
        if not self.active_contexts:
            return []
            
        # Simple keyword matching for now - in the future this could use embeddings
        scored_contexts = []
        keywords = re.findall(r'\b\w+\b', topic.lower())
        
        for ctx_id in self.active_contexts:
            context = self.user_contexts.get(ctx_id)
            if not context:
                continue
                
            content = context["content"].lower()
            score = sum(1 for keyword in keywords if keyword in content)
            scored_contexts.append((score, ctx_id))
            
        # Sort by relevance (descending)
        scored_contexts.sort(reverse=True)
        
        # Return the most relevant contexts
        result = []
        for _, ctx_id in scored_contexts[:max_contexts]:
            context = self.user_contexts[ctx_id].copy()
            # Calculate a short excerpt for display
            excerpt = self._generate_excerpt(context["content"], topic)
            context["excerpt"] = excerpt
            result.append(context)
            
        return result
    
    def get_all_contexts(self) -> List[Dict[str, Any]]:
        """
        Get all stored contexts.
        
        Returns:
            List of all context dictionaries
        """
        result = []
        for ctx_id, context in self.user_contexts.items():
            ctx_copy = context.copy()
            ctx_copy["id"] = ctx_id
            ctx_copy["active"] = ctx_id in self.active_contexts
            result.append(ctx_copy)
            
        return result
    
    def clear_contexts(self):
        """Clear all stored contexts."""
        self.user_contexts = {}
        self.active_contexts = []
    
    def remove_context(self, context_id: str):
        """
        Remove a specific context.
        
        Args:
            context_id: ID of the context to remove
        """
        if context_id in self.user_contexts:
            del self.user_contexts[context_id]
            
        if context_id in self.active_contexts:
            self.active_contexts.remove(context_id)
    
    def _generate_excerpt(self, content: str, topic: str, length: int = 200) -> str:
        """
        Generate a relevant excerpt from content.
        
        Args:
            content: Full content text
            topic: Topic to find relevant parts for
            length: Target length of excerpt
            
        Returns:
            A relevant excerpt from the content
        """
        # Very simplified relevance-based excerpt:
        keywords = set(re.findall(r'\b\w+\b', topic.lower()))
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        # Score sentences by keyword matches
        scored_sentences = []
        for i, sentence in enumerate(sentences):
            matches = sum(1 for word in re.findall(r'\b\w+\b', sentence.lower()) if word in keywords)
            scored_sentences.append((matches, i, sentence))
            
        # Sort by most relevant
        scored_sentences.sort(reverse=True)
        
        # Take top sentences until we hit length limit
        excerpt = ""
        current_length = 0
        used_sentences = set()
        
        for _, i, sentence in scored_sentences:
            if i in used_sentences:
                continue
                
            if current_length + len(sentence) <= length or current_length == 0:
                excerpt += sentence + " "
                current_length += len(sentence) + 1
                used_sentences.add(i)
                
            if current_length >= length:
                break
                
        return excerpt.strip() 
 