import os
import json
import time
import logging
import re
from typing import Dict, Any, List, Optional, Union, Tuple
import openai
import anthropic
from dotenv import load_dotenv, dotenv_values
import chromadb
from chromadb.utils import embedding_functions

from sapiens_engine.core.config_loader import ConfigLoader
from sapiens_engine.utils.context_manager import UserContextManager

# Load environment variables
load_dotenv(override=True)  # Force override existing environment variables with .env values

logger = logging.getLogger(__name__)

class LLMManager:
    """
    Manages interactions with language models (OpenAI or Anthropic)
    for philosophical dialogue generation
    """
    
    def __init__(self, llm_config: Union[Dict[str, Any], ConfigLoader] = None):
        """
        Initialize the LLM manager
        
        Args:
            llm_config: LLM configuration dictionary or ConfigLoader instance
        """
        if isinstance(llm_config, ConfigLoader):
            # Handle case where a ConfigLoader is passed
            self.config_loader = llm_config
            self.llm_config = self.config_loader.get_main_config().get("llm", {})
        elif isinstance(llm_config, dict):
            # Handle case where a config dict is passed directly
            self.config_loader = None
            self.llm_config = llm_config
        else:
            # Default case
            self.config_loader = ConfigLoader()
            self.llm_config = self.config_loader.get_main_config().get("llm", {})
        
        # Get API keys from .env file directly to ensure we use the correct values
        env_values = dotenv_values()
        self.openai_api_key = env_values.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = env_values.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        
        # Set up clients
        self._setup_clients()
        
        # Initialize context manager
        self.context_manager = UserContextManager()
        
        # NPC cache for RAG data - key is NPC ID, value is a dict with RAG config
        self.npc_rag_cache = {}
        
        # RAG paths for philosophers - 클래스 변수로 이동
        self.rag_paths = {
            "kant": "rag_data/kant/vector_db",
            # Add more philosophers here as their RAG data becomes available
        }
        
        # Default collection names
        self.rag_collections = {
            "kant": "langchain", 
            # Add more as needed
        }
        
        logger.info(f"Initialized LLM Manager with provider: {self.llm_config.get('provider', 'openai')}, model: {self.llm_config.get('model', 'gpt-4')}")
        
        # Print a masked version of the API key for debugging
        if self.openai_api_key:
            masked_key = self.openai_api_key[:4] + '*' * (len(self.openai_api_key) - 8) + self.openai_api_key[-4:]
            logger.info(f"Using OpenAI API key: {masked_key}")
        elif self.anthropic_api_key:
            masked_key = self.anthropic_api_key[:4] + '*' * (len(self.anthropic_api_key) - 8) + self.anthropic_api_key[-4:]
            logger.info(f"Using Anthropic API key: {masked_key}")
        else:
            logger.warning(f"No API key found for provider: {self.llm_config.get('provider', 'openai')}")
        
    def _setup_clients(self):
        """Set up API clients based on configured provider"""
        provider = self.llm_config.get("provider", "openai").lower()
        
        if provider == "openai":
            if not self.openai_api_key:
                raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
            openai.api_key = self.openai_api_key
            self.client = openai.Client(api_key=self.openai_api_key)
            print(f"Using OpenAI with API key: {self.openai_api_key[:5]}...{self.openai_api_key[-5:]}")
        elif provider == "anthropic":
            if not self.anthropic_api_key:
                raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.")
            self.client = anthropic.Anthropic(api_key=self.anthropic_api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
            
    def generate_response(self, system_prompt: str, user_prompt: str, llm_provider: str = None, llm_model: str = None) -> str:
        """
        Generate a response from the LLM
        
        Args:
            system_prompt: The system prompt to use
            user_prompt: The user prompt to use
            llm_provider: Override default LLM provider (openai, anthropic, etc.)
            llm_model: Override default model for the provider
            
        Returns:
            String containing the LLM's response
        """
        provider = llm_provider or self.llm_config.get("provider", "openai").lower()
        
        # Update config if model is specified
        if llm_model:
            original_model = None
            if provider == "openai" and "model" in self.llm_config:
                original_model = self.llm_config["model"]
                self.llm_config["model"] = llm_model
            
            try:
                if provider == "openai":
                    return self._generate_openai_response(system_prompt, user_prompt)
                elif provider == "anthropic":
                    return self._generate_anthropic_response(system_prompt, user_prompt)
                else:
                    raise ValueError(f"Unsupported LLM provider: {provider}")
            finally:
                # Restore original model config
                if original_model:
                    self.llm_config["model"] = original_model
        else:
            # Use standard config
            if provider == "openai":
                return self._generate_openai_response(system_prompt, user_prompt)
            elif provider == "anthropic":
                return self._generate_anthropic_response(system_prompt, user_prompt)
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
            
    def _generate_openai_response(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a response using OpenAI"""
        model = self.llm_config.get("model", "gpt-4")
        temperature = self.llm_config.get("temperature", 0.7)
        max_tokens = self.llm_config.get("max_tokens", 1000)
        
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
        
    def _generate_anthropic_response(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a response using Anthropic"""
        model = self.llm_config.get("model", "claude-3-opus-20240229")
        temperature = self.llm_config.get("temperature", 0.7)
        max_tokens = self.llm_config.get("max_tokens", 1000)
        
        message = self.client.messages.create(
            model=model,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return message.content[0].text
        
    def generate_philosophical_response(self, 
                                      npc_description: str, 
                                      topic: str,
                                      context: str = "",
                                      previous_dialogue: str = "",
                                      source_materials: List[Dict[str, str]] = None,
                                      user_contexts: List[Dict[str, Any]] = None,
                                      references: List[Dict[str, Any]] = None,
                                      llm_provider: str = None,
                                      llm_model: str = None,
                                      use_rag: bool = False,
                                      npc_id: str = None) -> Tuple[str, Dict[str, Any]]:
        """
        Generate a philosophical response from a specific perspective
        
        Args:
            npc_description: Description of the philosophical character/perspective to simulate
            topic: The philosophical topic to discuss
            context: Additional context about the discussion
            previous_dialogue: Previous messages in the dialogue
            source_materials: Relevant philosophical source materials
            user_contexts: User-provided context for the conversation
            references: References for the philosophical topics
            llm_provider: Override the default LLM provider
            llm_model: Override the default LLM model
            use_rag: Whether to use RAG to enhance the response
            npc_id: ID of the philosopher for RAG
            
        Returns:
            Tuple of (response_text, metadata)
        """
        # Extract the philosopher's style if available in the description
        philosopher_style = ""
        philosopher_name = ""
        
        # Try to extract philosopher's name and style from description
        if npc_description:
            # Extract name - typically the first part before the colon
            if ":" in npc_description:
                philosopher_name = npc_description.split(":")[0].strip()
            
            # Look for style information in the description
            if "style:" in npc_description.lower():
                style_parts = npc_description.lower().split("style:")
                if len(style_parts) > 1:
                    philosopher_style = style_parts[1].split(".")[0].strip()
                    
                    # If we have multiple sentences in style, get them all
                    full_style = style_parts[1].strip()
                    dot_idx = full_style.find(".")
                    if dot_idx >= 0 and len(full_style) > dot_idx + 1:
                        # Check if there are more sentences after the first one
                        rest_of_text = full_style[dot_idx+1:].strip()
                        if rest_of_text and rest_of_text[0].isupper():
                            # There's likely more content - try to get until next section
                            next_section_markers = ["key_concepts:", "major_works:", "philosophical_stance:", "influenced_by:", "voice style:", "debate approach:"]
                            end_idx = len(full_style)
                            
                            for marker in next_section_markers:
                                marker_pos = full_style.lower().find(marker)
                                if marker_pos > 0 and marker_pos < end_idx:
                                    end_idx = marker_pos
                            
                            philosopher_style = full_style[:end_idx].strip()
            
            # Also check for voice style which might be used for custom NPCs
            if "voice style:" in npc_description.lower():
                style_parts = npc_description.lower().split("voice style:")
                if len(style_parts) > 1:
                    philosopher_style = style_parts[1].split(".")[0].strip()
                
        # Build sources context
        sources_context = ""
        if source_materials:
            sources_context = "# Relevant Source Materials\n\n"
            for source in source_materials:
                if "title" in source and "excerpt" in source:
                    sources_context += f"**{source['title']}**\n"
                    sources_context += f"Excerpt: {source['excerpt']}\n\n"
        
        # Build user context
        user_context_str = ""
        latest_user_message = ""
        
        # Extract latest user message
        if previous_dialogue:
            dialogue_lines = previous_dialogue.strip().split("\n")
            for line in reversed(dialogue_lines):
                if line.lower().startswith("user:"):
                    latest_user_message = line.split(":", 1)[1].strip()
                    break
                
        if user_contexts:
            user_context_str = "# User-Provided References\n\n"
            for ctx in user_contexts:
                user_context_str += f"**{ctx['title']}**\n"
                user_context_str += f"Source: {ctx['source']}\n"
                user_context_str += f"Excerpt: {ctx['excerpt']}\n\n"
                
        # Build the system prompt with improved conversational flow and philosopher-specific style
        system_prompt = f"""You are an AI simulating the philosophical thinking of {philosopher_name or "a specific philosopher"} in an interactive dialogue.
Your goal is to respond to philosophical topics exactly as this philosopher would, while engaging naturally with other participants.
Maintain the philosophical terminology, worldview, and most importantly the UNIQUE SPEAKING STYLE consistent with this philosopher.

This is a philosophical simulation where different perspectives interact with each other.
Don't break character. Don't refer to yourself as an AI. Don't explain your thinking process.
Respond directly as if you truly are this philosopher.

PHILOSOPHER'S SPECIFIC STYLE AND MANNER OF SPEAKING:
{philosopher_style}

IMPORTANT GUIDELINES FOR NATURAL INTERACTIVE DIALOGUE:
1. Be concise and direct - keep responses to 2-3 sentences maximum
2. DIRECTLY RESPOND TO THE PREVIOUS SPEAKER - reference their specific points, ideas, or questions
3. Be conversational, as if you're having a real-time discussion with the previous speaker
4. If there are multiple speakers, address the most recent message or the most relevant point
5. NEVER start with "Indeed" or simple agreement - use varied ways to engage
6. If appropriate, ask follow-up questions or challenge assumptions made by others
7. RESPOND IN THE SAME LANGUAGE AS THE TOPIC - if the topic is in Korean, respond in Korean; if in English, respond in English

VERY IMPORTANT - ABOUT USING NAMES:
1. DO NOT address other speakers by name in most of your responses
2. AVOID starting your responses with another person's name
3. Only mention names when absolutely necessary for clarity (like when distinguishing between multiple viewpoints)
4. Focus on responding to ideas rather than to people
5. Use phrases like "That perspective..." or "This view..." instead of "Person's name, your perspective..."
6. When you do need to use names, use proper names (never IDs or codes)

The response should feel like a natural conversation that TRULY CAPTURES THE DISTINCT VOICE AND PHILOSOPHICAL APPROACH of {philosopher_name or "this philosopher"}.
"""

        # Build the user prompt with enhanced dialogue focus and philosopher-specific guidance
        user_prompt = f"""# Your Philosophical Persona
{npc_description}

# Your Unique Speaking Style
{philosopher_style}

# Topic of Discussion
{topic}

{sources_context}

{user_context_str}

# Additional Context
{context}

# Previous Dialogue (Most Recent First)
{previous_dialogue}

RESPOND DIRECTLY TO THE MOST RECENT MESSAGE IN THE DIALOGUE, as {philosopher_name or "your philosophical character"} would.
Your response should feel like a natural continuation of the conversation while TRULY EMBODYING YOUR UNIQUE PHILOSOPHICAL VOICE.

KEEP YOUR RESPONSE BRIEF (2-3 SENTENCES) as if speaking in a real-time dialogue.

IMPORTANT GUIDELINES: 
1. DO NOT ADDRESS THE PREVIOUS SPEAKER BY NAME in your response
2. DO NOT START YOUR RESPONSE WITH SOMEONE'S NAME
3. Directly address or engage with what was just said without using names
4. Express your philosophical perspective in YOUR UNIQUE STYLE
5. NEVER start with "Indeed" or generic acknowledgments
6. RESPOND IN THE SAME LANGUAGE AS THE TOPIC AND PREVIOUS MESSAGES

Create a natural flowing dialogue that genuinely captures how YOU as this specific philosopher would speak.
"""

        # Generate the initial response
        start_time = time.time()
        response_text = self.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_provider=llm_provider,
            llm_model=llm_model
        )
        
        # RAG 사용을 위한 변수 초기화
        rag_used = False
        rag_query = latest_user_message if latest_user_message else topic
        rag_detailed_results = []
        citations = []  # 인용 정보를 저장할 배열 추가
        
        # 생성된 응답에 RAG를 적용하여 강화
        if use_rag and npc_id:
            try:
                # 언어 감지
                original_language = self.detect_language(response_text)
                logger.info(f"🔍 원본 응답 언어: {original_language}")
                
                # RAG 쿼리 준비 - 한국어인 경우 영어로 번역
                translated_query = rag_query
                if original_language == 'ko':
                    translated_query = self.translate_korean_to_english(rag_query)
                    logger.info(f"🔄 RAG 쿼리가 영어로 번역되었습니다: {translated_query[:50]}...")
                
                # RAG로 관련 콘텐츠 검색
                logger.info(f"🔍 철학자 {npc_id}의 저작물에서 관련 내용 검색 중...")
                rag_result, rag_metadata = self.get_relevant_content_with_rag(
                    npc_id=npc_id, 
                    topic=topic, 
                    query=translated_query
                )
                
                # 검색 결과가 있는 경우 응답 강화
                if rag_result and "documents" in rag_metadata:
                    logger.info(f"✅ {len(rag_metadata['documents'])}개의 관련 저작물 청크를 찾았습니다.")
                    
                    # 원본 응답 저장
                    original_response = response_text
                    
                    # RAG로 강화된 응답 생성 및 인용 정보 가져오기
                    response_text, citations = self.enhance_message_with_rag(
                        message=response_text,
                        rag_results=rag_metadata,
                        original_language=original_language
                    )
                    
                    # 상세 검색 결과 저장
                    if "documents" in rag_metadata and "distances" in rag_metadata:
                        documents = rag_metadata["documents"]
                        distances = rag_metadata["distances"]
                        metadatas = rag_metadata.get("metadatas", [{}] * len(documents))
                        
                        for i, (doc, distance) in enumerate(zip(documents, distances)):
                            doc_metadata = metadatas[i] if i < len(metadatas) else {}
                            source = doc_metadata.get("source", "Unknown source")
                            
                            # 유사도 변환
                            if distance is not None:
                                similarity = max(0, min(1, 1 - (distance / 2)))
                            else:
                                similarity = None
                                
                            rag_detailed_results.append({
                                "chunk": doc,
                                "similarity": similarity,
                                "source": source
                            })
                    
                    rag_used = True
                    logger.info(f"✅ RAG를 통해 철학적 응답이 강화되었습니다.")
                else:
                    logger.warning(f"⚠️ {npc_id}의 저작물에서 관련 콘텐츠를 찾지 못했습니다.")
            except Exception as e:
                logger.error(f"❌ RAG 강화 중 오류 발생: {str(e)}")
                # 오류 발생 시 원본 응답 유지
        
        elapsed_time = time.time() - start_time
        
        # 메타데이터 구성 - 인용 정보 추가
        metadata = {
            "elapsed_time": f"{elapsed_time:.2f}s",
            "rag_used": rag_used,
            "rag_results": rag_detailed_results if rag_used else [],
            "citations": citations  # 인용 정보 추가
        }
        
        return response_text, metadata

    def get_relevant_content_with_rag(self, npc_id: str, topic: str, query: str) -> Tuple[str, Dict[str, Any]]:
        """
        Retrieve relevant content for an NPC using RAG
        
        Args:
            npc_id: The ID of the NPC
            topic: The current discussion topic
            query: The query to search for (usually the most recent message)
            
        Returns:
            Tuple containing (relevant content, metadata)
        """
        try:
            # Lowercase NPC ID for standard format
            npc_id_lower = npc_id.lower()
            
            # Get RAG path for this NPC
            rag_path = None
            collection_name = None
            
            # Check if in standard mapping
            if npc_id_lower in self.rag_paths:
                rag_path = self.rag_paths[npc_id_lower]
                collection_name = self.rag_collections.get(npc_id_lower, "langchain")
            
            # If no RAG path found, return empty result
            if not rag_path or not os.path.exists(rag_path):
                logger.warning(f"❌ No RAG data path found for NPC: {npc_id}")
                return "", {"status": "no_rag_data"}
            
            logger.info(f"🔍 Using RAG path: {rag_path} with collection: {collection_name}")
            
            # Initialize ChromaDB client
            chroma_client = chromadb.PersistentClient(path=rag_path)
            embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=self.openai_api_key,
                model_name="text-embedding-3-small"
            )
            
            # Get collection
            collection = chroma_client.get_collection(name=collection_name, embedding_function=embedding_function)
            
            # Log collection info
            logger.info(f"📊 Collection count: {collection.count()}")
            
            # Clean query - remove any special formatting
            clean_query = re.sub(r'\s+', ' ', query).strip()
            
            # If query is too short, use topic as fallback
            if len(clean_query) < 10:
                clean_query = topic
                logger.info(f"⚠️ Query too short, using topic instead: {clean_query}")
            
            # Query for relevant documents
            results = collection.query(
                query_texts=[clean_query],
                n_results=5,  # 5개의 관련 청크 검색
                include=["documents", "distances", "metadatas"]  # 거리 및 메타데이터 포함
            )
            
            # Process results
            if results and "documents" in results and results["documents"]:
                documents = results["documents"][0]  # 첫 번째 쿼리 결과
                distances = results.get("distances", [[]])[0] if "distances" in results else []
                metadatas = results.get("metadatas", [[]])[0] if "metadatas" in results else []
                
                # 거리값 로깅
                logger.info(f"🔍 검색된 거리값(distances): {distances}")
                
                if not documents:
                    logger.warning("❌ No documents found in query results")
                    return "", {"status": "no_results"}
                
                # RAG 메타데이터 생성
                metadata = {
                    "status": "success",
                    "result_count": len(documents),
                    "query": clean_query,
                    "collection": collection_name,
                    "documents": documents,
                    "distances": distances,
                    "metadatas": metadatas
                }
                
                # 단순 텍스트 결합 (이후 enhance_message_with_rag에서 실제 포맷팅됨)
                combined_text = ""
                for i, (doc, distance) in enumerate(zip(documents, distances if distances else [None] * len(documents))):
                    combined_text += f"Excerpt {i+1}: {doc}\n\n"
                
                logger.info(f"✅ Retrieved {len(documents)} relevant chunks")
                return combined_text, metadata
            else:
                logger.warning("❌ No documents found in query results")
                return "", {"status": "no_results"}
                
        except Exception as e:
            logger.error(f"❌ Error in RAG retrieval: {str(e)}")
            return "", {"status": "error", "error": str(e)}

    def should_use_rag(self, npc_id: str, user_message: str, previous_dialogue: str = "", topic: str = "") -> bool:
        """
        Automatically determines if RAG should be used based on conversation context and NPC
        
        Args:
            npc_id: The ID of the NPC that will respond
            user_message: The current user message
            previous_dialogue: Previous dialogue for context
            topic: The conversation topic
            
        Returns:
            Boolean indicating whether RAG should be used
        """
        # Check if this NPC has RAG data available
        npc_id_lower = npc_id.lower()
        
        # 철학자가 RAG 데이터를 가지고 있는지 확인
        if npc_id_lower in self.rag_paths:
            rag_path = self.rag_paths[npc_id_lower]
            # RAG 데이터 경로가 실제로 존재하는지 확인
            if os.path.exists(rag_path):
                logger.info(f"✅ {npc_id}의 RAG 데이터가 존재합니다. RAG 자동 활성화됨.")
                return True
            else:
                logger.warning(f"⚠️ {npc_id}의 RAG 경로({rag_path})가 존재하지 않습니다.")
                return False
                
        # RAG 데이터가 없는 철학자는 RAG를 사용하지 않음
        logger.info(f"⚠️ {npc_id}는 RAG 데이터가 없습니다.")
        return False

    # 언어 감지 함수 추가
    def detect_language(self, text: str) -> str:
        """
        텍스트의 언어를 감지합니다.
        
        Args:
            text: 언어를 감지할 텍스트
            
        Returns:
            감지된 언어 코드 (예: 'ko', 'en')
        """
        # 간단한 휴리스틱: 한글 글자가 포함되어 있는지 확인
        korean_pattern = re.compile('[가-힣]')
        if korean_pattern.search(text):
            return 'ko'
        else:
            return 'en'
            
    # 한국어 번역 기능 추가
    def translate_korean_to_english(self, korean_text: str) -> str:
        """
        한국어 텍스트를 영어로 번역합니다.
        
        Args:
            korean_text: 번역할 한국어 텍스트
            
        Returns:
            번역된 영어 텍스트
        """
        try:
            logger.info(f"🔄 한국어 텍스트 번역 시작: {korean_text[:50]}...")
            
            response = self.client.chat.completions.create(
                model="gpt-4o", # 모델 설정 - 번역에 최적화된 모델 사용
                messages=[
                    {"role": "system", "content": "You are a professional Korean to English translator. Your task is to accurately translate Korean text to English. Translate ONLY the text provided, without any additional explanation or context."},
                    {"role": "user", "content": f"Translate this Korean text to English: {korean_text}"}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            english_text = response.choices[0].message.content.strip()
            logger.info(f"✅ 번역 완료: {english_text[:50]}...")
            return english_text
            
        except Exception as e:
            logger.error(f"❌ 번역 오류: {str(e)}")
            return korean_text  # 오류 시 원본 텍스트 반환

    # 텍스트를 RAG를 통해 강화하는 함수 수정
    def enhance_message_with_rag(self, 
                                message: str, 
                                rag_results: Dict[str, Any], 
                                original_language: str = 'en') -> Tuple[str, List[Dict[str, str]]]:
        """
        검색된 RAG 결과를 활용하여 메시지를 강화합니다.
        
        Args:
            message: 원본 메시지
            rag_results: RAG 검색 결과 (documents, distances, metadatas 포함)
            original_language: 원본 언어 코드 ('ko' 또는 'en')
            
        Returns:
            Tuple의 형태로 (강화된 메시지, 인용 정보 리스트) 반환
        """
        try:
            logger.info(f"📚 RAG 검색 결과를 활용한 메시지 강화 시작")
            
            # 검색 결과 추출 및 포맷팅
            retrieved_contexts = ""
            
            if "documents" in rag_results and "distances" in rag_results:
                documents = rag_results["documents"]
                distances = rag_results["distances"]
                metadatas = rag_results.get("metadatas", [{}] * len(documents))
                
                # 각 검색 결과에 대한 상세 정보 포맷팅
                for i, (doc, distance) in enumerate(zip(documents, distances)):
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    source = metadata.get("source", "Unknown source")
                    
                    # 거리를 유사도로 변환 (0~1 범위)
                    similarity = max(0, min(1, 1 - (distance / 2))) if distance is not None else 0
                    
                    retrieved_contexts += f"Source {i+1} ({source}): {doc}\n\n"
            
            # RAG 강화 프롬프트 작성 - 각주 스타일 변경하되 1인칭 시점 유지
            system_prompt = """You are simulating a specific philosopher, speaking in first person as if you ARE that philosopher. 
Your goal is to enhance a philosophical response with source material from your own works, while maintaining your authentic voice and style.

IMPORTANT INSTRUCTIONS:
1. ALWAYS SPEAK IN FIRST PERSON as the philosopher - you ARE Kant, Hegel, etc., not someone describing their view
2. Maintain the exact same philosophical perspective and speaking style as in the original message
3. PRESERVE AND ENHANCE THE LOGICAL STRUCTURE of philosophical argumentation:
   - Present your core philosophical principle relevant to the topic
   - Connect this principle to the specific topic with clear logical reasoning
   - Provide your philosophical conclusion that follows from your principles
   - End with a brief philosophical reflection if appropriate
4. Use the retrieved excerpts from your own works to strengthen your points with specific references
5. When referencing your philosophical works, use numbered footnotes like [1], [2], etc. at the end of relevant sentences
6. Include a list of citations at the end of your response in this format:
   [1] Source: "Critique of Pure Reason", Text: "original quoted text"
   [2] Source: "Critique of Practical Reason", Text: "original quoted text"
7. Maintain the same formal philosophical tone, terminology and first-person perspective throughout
8. DO NOT change the message's main points or conclusions, but DO strengthen the logical connections
9. Output MUST be in the same language as the original message

Remember: You ARE the philosopher speaking directly, not someone explaining their views.
"""
            
            # 사용자 프롬프트 작성 - 각주 스타일 변경
            user_prompt = f"""# Your Original Response (Speaking as the Philosopher)
{message}

# Relevant Source Materials from Your Own Philosophical Works
{retrieved_contexts}

Enhance your original philosophical response using the retrieved source materials from your own works. Follow these guidelines:

1. Maintain your identity as the philosopher throughout - YOU are Kant, Nietzsche, etc. speaking in first person
2. Use a clear logical structure in your enhanced response:
   - Present your core philosophical principle relevant to this topic, citing the ACTUAL SOURCE
   - Connect this principle to the specific topic with crystal-clear logical reasoning
   - Provide your philosophical conclusion based on this reasoning
   - End with a brief philosophical reflection
3. Strengthen your argument by citing your own actual works - referring to their specific titles
4. Use numbered footnotes [1], [2], etc. at the end of sentences that reference your specific works
5. Include a list of citations at the end of your response in this format:
   [1] Source: "Critique of Pure Reason", Text: "original quoted text"
   [2] Source: "Critique of Practical Reason", Text: "original quoted text"
6. Keep the same philosophical tone, speaking style and perspective as in your original response
7. Maintain the same core points as your original message but enhance the logical structure and connections

DO NOT use explicit section headers like "전제 1" or "결론". Instead, create a naturally flowing philosophical response that contains all the logical components (principles, connections, conclusion) seamlessly integrated.
"""
            
            # 강화된 메시지 생성
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            full_enhanced_message = response.choices[0].message.content.strip()
            logger.info(f"✅ 메시지 강화 완료: {full_enhanced_message[:50]}...")
            
            # 메시지와 인용 부분 분리
            message_parts = full_enhanced_message.split("\n\n")
            
            # 인용 목록 추출
            citations = []
            enhanced_message = full_enhanced_message
            
            # 마지막 부분에 있는 각주 목록 찾기
            citation_pattern = r'\[(\d+)\]\s+Source:\s+"([^"]+)",\s+Text:\s+"([^"]+)"'
            citation_matches = re.findall(citation_pattern, full_enhanced_message)
            
            if citation_matches:
                # 각주 목록 찾음
                logger.info(f"📚 {len(citation_matches)}개의 인용 정보 찾음: {citation_matches}")
                
                for citation_id, source, text in citation_matches:
                    citation_obj = {
                        "id": citation_id,
                        "source": source,
                        "text": text
                    }
                    citations.append(citation_obj)
                    logger.debug(f"📚 인용 정보 생성: {citation_obj}")
                
                # 각주 목록 부분 제거하고 실제 메시지만 유지
                enhanced_message = re.sub(r'\n\n\[1\]\s+Source:.+', '', full_enhanced_message, flags=re.DOTALL)
                
                logger.info(f"✅ {len(citations)}개의 각주를 추출했습니다.")
            else:
                logger.warning("⚠️ 각주 목록을 찾지 못했습니다.")
            
            # 반환하기 전에 citations 구조 확인
            if citations:
                logger.info(f"📚 반환할 인용 정보: {citations}")
                # 각 인용 정보에 필수 필드가 있는지 확인
                for i, citation in enumerate(citations):
                    if not isinstance(citation, dict) or not all(k in citation for k in ["id", "source", "text"]):
                        logger.warning(f"⚠️ 인용 정보 {i}번의 형식이 올바르지 않습니다: {citation}")
                        
            return enhanced_message, citations
            
        except Exception as e:
            logger.error(f"❌ 메시지 강화 오류: {str(e)}")
            return message, []  # 오류 시 원본 메시지와 빈 인용 목록 반환
 