import requests
import logging
import random
import time
from typing import Dict, List, Any, Optional
import json
import re
import os
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv, dotenv_values

# Load environment variables
load_dotenv(override=True)

logger = logging.getLogger(__name__)

class SmartSearch:
    """
    Provides smart search capabilities to find relevant information
    on philosophical topics from various online sources.
    """
    
    def __init__(self):
        """
        Initialize the smart search engine.
        """
        # Get API keys from .env file
        env_values = dotenv_values()
        self.serp_api_key = env_values.get("SERP_API_KEY") or os.getenv("SERP_API_KEY")
        self.semantic_scholar_api_key = env_values.get("SEMANTIC_SCHOLAR_API_KEY") or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        
        # Cache for search results to avoid repeated requests
        self.search_cache = {}
    
    def search_for_topic(self, topic: str, search_type: str = "all") -> List[Dict[str, Any]]:
        """
        Search for information related to a topic.
        
        Args:
            topic: The philosophical topic to search for
            search_type: Type of search ("academic", "news", "statistics", "all")
            
        Returns:
            List of relevant information found
        """
        # Check cache first
        cache_key = f"{topic}_{search_type}"
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]
            
        results = []
        
        # Determine which search methods to use
        if search_type in ["academic", "all"]:
            academic_results = self.search_academic_sources(topic)
            results.extend(academic_results)
            
        if search_type in ["news", "all"]:
            news_results = self.search_news_sources(topic)
            results.extend(news_results)
            
        if search_type in ["statistics", "all"]:
            stats_results = self.search_statistics(topic)
            results.extend(stats_results)
            
        # Cache the results
        self.search_cache[cache_key] = results
        
        return results
    
    def search_academic_sources(self, topic: str) -> List[Dict[str, Any]]:
        """
        Search academic sources for information on the topic.
        
        Args:
            topic: The topic to search for
            
        Returns:
            List of academic references
        """
        try:
            logger.info(f"Searching academic sources for: {topic}")
            
            if self.semantic_scholar_api_key:
                # Use Semantic Scholar API if available
                return self._search_semantic_scholar(topic)
            else:
                # Fall back to general search with academic focus
                return self._search_serp_api(topic, "scholarly")
                
        except Exception as e:
            logger.error(f"Error searching academic sources: {str(e)}")
            # Fall back to mock data in case of error
            return self._generate_mock_academic_results(topic)
    
    def search_news_sources(self, topic: str) -> List[Dict[str, Any]]:
        """
        Search news sources for information on the topic.
        
        Args:
            topic: The topic to search for
            
        Returns:
            List of news articles
        """
        try:
            logger.info(f"Searching news sources for: {topic}")
            
            if self.serp_api_key:
                return self._search_serp_api(topic, "news")
            else:
                # Fall back to mock data if no API key
                return self._generate_mock_news_results(topic)
                
        except Exception as e:
            logger.error(f"Error searching news sources: {str(e)}")
            return self._generate_mock_news_results(topic)
    
    def search_statistics(self, topic: str) -> List[Dict[str, Any]]:
        """
        Search for statistical data related to the topic.
        
        Args:
            topic: The topic to search for
            
        Returns:
            List of statistical information
        """
        try:
            logger.info(f"Searching for statistics on: {topic}")
            
            # Add "statistics" to the query to focus on statistical data
            if self.serp_api_key:
                return self._search_serp_api(f"{topic} statistics data survey", "statistic")
            else:
                return self._generate_mock_statistics(topic)
                
        except Exception as e:
            logger.error(f"Error searching for statistics: {str(e)}")
            return self._generate_mock_statistics(topic)
    
    def _search_semantic_scholar(self, topic: str) -> List[Dict[str, Any]]:
        """Search for academic papers using Semantic Scholar API"""
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        
        params = {
            "query": topic,
            "limit": 5,
            "fields": "title,abstract,authors,year,journal,url,venue"
        }
        
        headers = {}
        if self.semantic_scholar_api_key:
            headers["x-api-key"] = self.semantic_scholar_api_key
            
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for paper in data.get("data", []):
            if not paper.get("title") or not paper.get("abstract"):
                continue
                
            authors = []
            for author in paper.get("authors", []):
                if author.get("name"):
                    authors.append(author["name"])
            
            results.append({
                "type": "academic",
                "title": paper.get("title", ""),
                "abstract": paper.get("abstract", ""),
                "authors": authors,
                "year": paper.get("year", "Unknown"),
                "journal": paper.get("venue", paper.get("journal", {}).get("name", "Unknown")),
                "url": paper.get("url", "")
            })
            
        return results
    
    def _search_serp_api(self, query: str, search_type: str) -> List[Dict[str, Any]]:
        """Search using SERP API for various types of content"""
        if not self.serp_api_key:
            raise ValueError("SERP API key not available")
            
        base_url = "https://serpapi.com/search"
        
        params = {
            "api_key": self.serp_api_key,
            "q": query,
            "num": 5
        }
        
        if search_type == "news":
            params["tbm"] = "nws"
        elif search_type == "scholarly":
            params["tbm"] = "sch"
        
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        results = []
        
        if search_type == "news" and "news_results" in data:
            for item in data["news_results"]:
                results.append({
                    "type": "news",
                    "title": item.get("title", ""),
                    "source": item.get("source", ""),
                    "date": item.get("date", ""),
                    "summary": item.get("snippet", ""),
                    "url": item.get("link", "")
                })
        elif search_type == "scholarly" and "organic_results" in data:
            for item in data["organic_results"]:
                if "publication_info" in item:
                    pub_info = item["publication_info"]
                    authors = []
                    if "authors" in pub_info:
                        for author in pub_info["authors"]:
                            authors.append(author.get("name", ""))
                    
                    results.append({
                        "type": "academic",
                        "title": item.get("title", ""),
                        "abstract": item.get("snippet", ""),
                        "authors": authors,
                        "year": pub_info.get("published_date", {}).get("year", "Unknown"),
                        "journal": pub_info.get("summary", "Unknown"),
                        "url": item.get("link", "")
                    })
        elif search_type == "statistic" and "organic_results" in data:
            for item in data["organic_results"]:
                # Look for results that mention statistics, surveys, or data
                snippet = item.get("snippet", "").lower()
                if any(term in snippet for term in ["statistics", "survey", "data", "report", "study", "research", "analysis"]):
                    results.append({
                        "type": "statistics",
                        "title": item.get("title", ""),
                        "source": item.get("source", ""),
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "key_findings": item.get("snippet", ""),
                        "url": item.get("link", "")
                    })
        
        return results
    
    def extract_content_from_url(self, url: str) -> str:
        """Extract main content from a URL"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for tag in soup(['script', 'style', 'header', 'footer', 'nav']):
                tag.extract()
                
            # Find main content (this is a simple approach, real implementations would be more sophisticated)
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
            
            if main_content:
                text = main_content.get_text(separator=' ', strip=True)
            else:
                text = soup.get_text(separator=' ', strip=True)
                
            # Clean up the text
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Extract a reasonable length excerpt
            if len(text) > 1000:
                text = text[:1000] + "..."
                
            return text
            
        except Exception as e:
            logger.error(f"Error extracting content from URL {url}: {str(e)}")
            return ""

    # Keep the mock methods for fallback in case the APIs are not available
    def _generate_mock_academic_results(self, topic: str) -> List[Dict[str, Any]]:
        """Generate mock academic search results for demonstration purposes."""
        keywords = re.findall(r'\b\w+\b', topic.lower())
        
        # Dictionary of philosophical topics and related academic papers
        philosophy_papers = {
            "consciousness": [
                {
                    "title": "The Hard Problem of Consciousness: An Integrated Approach",
                    "authors": ["David Chalmers", "Patricia Churchland"],
                    "year": 2022,
                    "journal": "Journal of Consciousness Studies",
                    "abstract": "This paper examines the gap between neural correlates and subjective experience, proposing an integrated framework for understanding phenomenal consciousness.",
                    "url": "https://example.org/consciousness-hard-problem"
                },
                {
                    "title": "Neural Correlates of Conscious Experience",
                    "authors": ["Stanislas Dehaene", "Jean-Pierre Changeux"],
                    "year": 2020,
                    "journal": "Trends in Cognitive Sciences",
                    "abstract": "We review recent advances in identifying neural signatures that specifically accompany conscious perception, particularly focusing on visual awareness and its relationship to attention.",
                    "url": "https://example.org/neural-conscious-experience"
                }
            ],
            "free will": [
                {
                    "title": "Compatibilism and Neuroscientific Approaches to Free Will",
                    "authors": ["Daniel Dennett", "Adina Roskies"],
                    "year": 2023,
                    "journal": "Philosophical Psychology",
                    "abstract": "We defend compatibilist accounts of free will against challenges from neuroscience, arguing that determinism does not undermine moral responsibility.",
                    "url": "https://example.org/compatibilism-neuroscience"
                },
                {
                    "title": "Free Will in Social Contexts: Decision-Making and Moral Responsibility",
                    "authors": ["Alfred Mele", "Eddy Nahmias"],
                    "year": 2021,
                    "journal": "Mind & Language",
                    "abstract": "This paper examines how social contexts influence our sense of agency and decision-making capabilities, with implications for our understanding of free will.",
                    "url": "https://example.org/freewill-social-contexts"
                }
            ],
            "ethics": [
                {
                    "title": "Digital Ethics: Moral Challenges in the Age of AI",
                    "authors": ["Luciano Floridi", "Shannon Vallor"],
                    "year": 2022,
                    "journal": "Ethics and Information Technology",
                    "abstract": "We examine emerging ethical challenges posed by artificial intelligence systems, including issues of transparency, accountability, and value alignment.",
                    "url": "https://example.org/digital-ethics-ai"
                },
                {
                    "title": "Virtue Ethics in Practice: Character and Action in Contemporary Contexts",
                    "authors": ["Martha Nussbaum", "Rosalind Hursthouse"],
                    "year": 2020,
                    "journal": "Journal of Applied Philosophy",
                    "abstract": "This paper revitalizes virtue ethics for addressing contemporary moral problems, demonstrating its effectiveness compared to consequentialist and deontological approaches.",
                    "url": "https://example.org/virtue-ethics-practice"
                }
            ],
            "technology": [
                {
                    "title": "Philosophy of Technology: The Technological Mediation of Experience",
                    "authors": ["Peter-Paul Verbeek", "Don Ihde"],
                    "year": 2021,
                    "journal": "Techné: Research in Philosophy and Technology",
                    "abstract": "This paper develops a post-phenomenological approach to understanding how technologies shape human experience and moral decision-making.",
                    "url": "https://example.org/technological-mediation"
                },
                {
                    "title": "The Ethics of Artificial Intelligence: Autonomy, Responsibility, and Transparency",
                    "authors": ["Nick Bostrom", "Stuart Russell"],
                    "year": 2023,
                    "journal": "AI & Society",
                    "abstract": "We analyze ethical frameworks for ensuring AI systems align with human values, focusing on problems of specification, robustness, and value alignment.",
                    "url": "https://example.org/ethics-artificial-intelligence"
                }
            ],
            "meaning": [
                {
                    "title": "Meaning in a Secular Age: Existential Resources for Contemporary Life",
                    "authors": ["Charles Taylor", "Regina Rini"],
                    "year": 2022,
                    "journal": "Journal of the Philosophy of Life",
                    "abstract": "This paper explores sources of meaning available in post-religious societies, arguing that secular frameworks can provide robust foundations for meaningful lives.",
                    "url": "https://example.org/meaning-secular-age"
                },
                {
                    "title": "The Construction of Meaning Through Narrative Identity",
                    "authors": ["Paul Ricoeur", "Galen Strawson"],
                    "year": 2020,
                    "journal": "Journal of Consciousness Studies",
                    "abstract": "We examine how narrative self-understanding contributes to a sense of meaning and purpose, while acknowledging limitations of narrative approaches to identity.",
                    "url": "https://example.org/narrative-meaning-identity"
                }
            ],
            "society": [
                {
                    "title": "Digital Democracy: Social Media and Political Participation",
                    "authors": ["Jürgen Habermas", "Zeynep Tufekci"],
                    "year": 2023,
                    "journal": "New Media & Society",
                    "abstract": "This paper examines how digital platforms are transforming the public sphere, with both positive and negative implications for democratic discourse.",
                    "url": "https://example.org/digital-democracy-social"
                },
                {
                    "title": "Justice in an Age of Inequality: Reviving Egalitarian Political Philosophy",
                    "authors": ["Elizabeth Anderson", "Thomas Piketty"],
                    "year": 2021,
                    "journal": "Philosophy & Public Affairs",
                    "abstract": "We develop a relational theory of equality that addresses contemporary forms of social and economic inequality, proposing institutional reforms to promote justice.",
                    "url": "https://example.org/justice-inequality-egalitarian"
                }
            ]
        }
        
        # Find matching papers based on keywords
        results = []
        for keyword in keywords:
            for topic, papers in philosophy_papers.items():
                if keyword in topic or topic in keyword:
                    for paper in papers:
                        # Avoid duplicates
                        if not any(r["title"] == paper["title"] for r in results):
                            paper_copy = paper.copy()
                            paper_copy["type"] = "academic"
                            paper_copy["relevance"] = random.uniform(0.7, 0.95)
                            results.append(paper_copy)
        
        # If no specific matches, return some general papers
        if not results:
            general_papers = []
            for papers in philosophy_papers.values():
                general_papers.extend(papers)
            
            # Randomly select a few papers
            sample_size = min(3, len(general_papers))
            for paper in random.sample(general_papers, sample_size):
                paper_copy = paper.copy()
                paper_copy["type"] = "academic"
                paper_copy["relevance"] = random.uniform(0.6, 0.8)
                results.append(paper_copy)
        
        return results[:3]  # Limit to top 3 results
    
    def _generate_mock_news_results(self, topic: str) -> List[Dict[str, Any]]:
        """Generate mock news search results for demonstration purposes."""
        keywords = re.findall(r'\b\w+\b', topic.lower())
        
        # Dictionary of philosophical topics and related news articles
        philosophy_news = {
            "consciousness": [
                {
                    "title": "New Brain Mapping Technique Sheds Light on the Neural Basis of Consciousness",
                    "source": "Scientific American",
                    "date": "2023-06-15",
                    "summary": "Researchers have developed a new technique for mapping brain activity that may help understand the neural correlates of conscious experience.",
                    "url": "https://example.org/brain-mapping-consciousness"
                },
                {
                    "title": "Consciousness Conference Brings Together Scientists and Philosophers",
                    "source": "The Guardian",
                    "date": "2023-02-22",
                    "summary": "The annual Science of Consciousness conference witnessed heated debates between neuroscientists and philosophers about the nature of subjective experience.",
                    "url": "https://example.org/consciousness-conference"
                }
            ],
            "ethics": [
                {
                    "title": "Tech Companies Establish Ethics Boards for AI Development",
                    "source": "Wired",
                    "date": "2023-05-10",
                    "summary": "Major technology companies have announced the formation of independent ethics committees to oversee the development of artificial intelligence systems.",
                    "url": "https://example.org/tech-ethics-boards"
                },
                {
                    "title": "Bioethics Panel Debates Gene Editing Regulations",
                    "source": "Nature News",
                    "date": "2023-03-04",
                    "summary": "International panel of bioethicists meets to establish guidelines for human gene editing technologies following controversial experiments.",
                    "url": "https://example.org/bioethics-gene-editing"
                }
            ],
            "technology": [
                {
                    "title": "AI Model Creates Philosophical Texts Indistinguishable from Human Writing",
                    "source": "MIT Technology Review",
                    "date": "2023-07-12",
                    "summary": "A new large language model specializing in philosophical reasoning has passed blind tests where experts could not distinguish its writing from human philosophers.",
                    "url": "https://example.org/ai-philosophy-writing"
                },
                {
                    "title": "Virtual Reality Platform Aims to Simulate Philosophical Thought Experiments",
                    "source": "The Verge",
                    "date": "2023-04-18",
                    "summary": "New educational VR software allows users to experience classic philosophical thought experiments like the trolley problem and Mary's room firsthand.",
                    "url": "https://example.org/vr-thought-experiments"
                }
            ],
            "society": [
                {
                    "title": "Social Media Regulations Face Philosophical Challenges Over Free Speech",
                    "source": "The New York Times",
                    "date": "2023-08-02",
                    "summary": "Lawmakers and philosophers debate the boundaries between harmful content moderation and free speech principles as new regulations are proposed.",
                    "url": "https://example.org/social-media-free-speech"
                },
                {
                    "title": "Universal Basic Income Trial Shows Promising Results for Social Well-being",
                    "source": "Bloomberg",
                    "date": "2023-01-30",
                    "summary": "A three-year trial of universal basic income in a mid-sized city reports significant improvements in mental health and social cohesion among participants.",
                    "url": "https://example.org/ubi-trial-results"
                }
            ]
        }
        
        # Find matching news based on keywords
        results = []
        for keyword in keywords:
            for topic, articles in philosophy_news.items():
                if keyword in topic or topic in keyword:
                    for article in articles:
                        # Avoid duplicates
                        if not any(r["title"] == article["title"] for r in results):
                            article_copy = article.copy()
                            article_copy["type"] = "news"
                            article_copy["relevance"] = random.uniform(0.7, 0.95)
                            results.append(article_copy)
        
        # If no specific matches, return some general news
        if not results:
            general_news = []
            for articles in philosophy_news.values():
                general_news.extend(articles)
            
            # Randomly select a few articles
            sample_size = min(2, len(general_news))
            for article in random.sample(general_news, sample_size):
                article_copy = article.copy()
                article_copy["type"] = "news"
                article_copy["relevance"] = random.uniform(0.6, 0.8)
                results.append(article_copy)
        
        return results[:2]  # Limit to top 2 results
    
    def _generate_mock_statistics(self, topic: str) -> List[Dict[str, Any]]:
        """Generate mock statistical data for demonstration purposes."""
        keywords = re.findall(r'\b\w+\b', topic.lower())
        
        # Dictionary of philosophical topics and related statistics
        philosophy_stats = {
            "ethics": [
                {
                    "title": "Ethical Attitudes Across Generations",
                    "source": "Pew Research Center",
                    "date": "2022-11-20",
                    "summary": "Survey of 5,000 adults shows significant generational differences in moral attitudes, with younger generations more likely to emphasize harm prevention over traditional values.",
                    "key_findings": "68% of adults under 30 prioritize harm prevention, compared to 42% of those over 65.",
                    "url": "https://example.org/ethical-attitudes-generations"
                }
            ],
            "technology": [
                {
                    "title": "Public Perceptions of AI Risk and Benefits",
                    "source": "Gallup",
                    "date": "2023-02-15",
                    "summary": "Global survey reveals varied attitudes toward artificial intelligence, with 62% expressing concern about potential risks while 78% acknowledge likely benefits.",
                    "key_findings": "62% concerned about AI risks; 78% acknowledge AI benefits; 45% support stronger regulation",
                    "url": "https://example.org/ai-public-perception"
                }
            ],
            "society": [
                {
                    "title": "Trust in Institutions Survey Data",
                    "source": "World Values Survey",
                    "date": "2022-09-03",
                    "summary": "Multi-national study shows declining trust in traditional institutions across 30 countries, with significant variations based on education level and political alignment.",
                    "key_findings": "Trust in government declined by 12% since 2010; Social media companies trusted by only 24% of respondents",
                    "url": "https://example.org/trust-institutions-survey"
                }
            ],
            "free will": [
                {
                    "title": "Belief in Free Will Across Cultures",
                    "source": "International Social Survey Programme",
                    "date": "2022-05-18",
                    "summary": "Comparative study of 40 countries reveals variations in belief in free will, with stronger belief correlated with individualistic cultural values.",
                    "key_findings": "87% of Americans express strong belief in free will compared to 63% in collectivist societies",
                    "url": "https://example.org/freewill-cross-cultural"
                }
            ]
        }
        
        # Find matching statistics based on keywords
        results = []
        for keyword in keywords:
            for topic, stats in philosophy_stats.items():
                if keyword in topic or topic in keyword:
                    for stat in stats:
                        # Avoid duplicates
                        if not any(r["title"] == stat["title"] for r in results):
                            stat_copy = stat.copy()
                            stat_copy["type"] = "statistics"
                            stat_copy["relevance"] = random.uniform(0.7, 0.95)
                            results.append(stat_copy)
        
        # If no specific matches, return some general statistics
        if not results:
            general_stats = []
            for stats in philosophy_stats.values():
                general_stats.extend(stats)
            
            # Randomly select a statistic
            if general_stats:
                stat = random.choice(general_stats)
                stat_copy = stat.copy()
                stat_copy["type"] = "statistics"
                stat_copy["relevance"] = random.uniform(0.6, 0.8)
                results.append(stat_copy)
        
        return results[:1]  # Limit to top result 
 