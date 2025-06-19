# Sapiens Engine

An AI-powered philosophical debate and conversation platform featuring autonomous philosopher agents, retrieval-augmented generation (RAG), and real-time dialogue management.

## 🏗️ Architecture Overview

Sapiens Engine is a full-stack application consisting of:

- **Frontend**: Next.js React application (`agoramind/`) with modern UI/UX
- **Backend**: FastAPI Python server (`api/`) with modular router architecture  
- **AI Engine**: Sophisticated agent system (`src/`) with specialized philosopher personas
- **RAG System**: Vector database integration for knowledge-enhanced conversations
- **Containerization**: Docker-based deployment with docker-compose orchestration

## 📁 Project Structure

```
├── agoramind/                   # Next.js Frontend Application
│   ├── src/
│   │   ├── app/                 # Next.js 13+ App Router
│   │   ├── components/          # React components
│   │   ├── lib/                 # Utility functions
│   │   ├── hooks/               # Custom React hooks
│   │   ├── types/               # TypeScript definitions
│   │   └── config/              # Configuration files
│   ├── public/                  # Static assets
│   └── package.json             # Node.js dependencies
│
├── api/                         # FastAPI Backend Server
│   ├── routers/                 # API route handlers
│   │   ├── chat.py              # Chat functionality
│   │   ├── philosophers.py      # Philosopher management
│   │   ├── npc.py               # NPC interactions
│   │   └── debug.py             # Debug endpoints
│   ├── core/                    # Core functionality
│   ├── models/                  # Pydantic models
│   ├── utils/                   # Backend utilities
│   └── main.py                  # FastAPI application entry point
│
├── src/                         # AI Agent Engine
│   ├── agents/                  # Agent implementations
│   │   ├── base/                # Base agent classes
│   │   ├── moderator/           # Debate moderator agents
│   │   ├── participant/         # Philosopher participant agents
│   │   ├── specialty/           # Domain-specific agents
│   │   ├── utility/             # Utility agents (emotion, humor)
│   │   └── configs/             # Agent configuration
│   ├── rag/                     # Retrieval Augmented Generation
│   │   ├── retrieval/           # Document & web retrieval
│   │   ├── generation/          # Response generation
│   │   ├── evaluation/          # RAG quality evaluation
│   │   └── pipeline/            # RAG processing pipeline
│   ├── dialogue/                # Dialogue management
│   │   ├── types/               # Dialogue type implementations
│   │   ├── state/               # Conversation state management
│   │   └── strategies/          # Dialogue strategies
│   ├── models/                  # AI model interfaces
│   │   ├── llm/                 # Large Language Model wrappers
│   │   ├── embedding/           # Text embedding models
│   │   └── specialized/         # Specialized AI models
│   └── utils/                   # Shared utilities
│
├── data/                        # Data storage
│   ├── vector_store/            # Vector database files
│   ├── sources/                 # Source documents
│   └── test_*/                  # Test datasets
│
├── portraits/                   # Philosopher portrait images
├── models/                      # Model files and configurations
└── config/                      # Application configuration
```

## 🚀 Features

### 🤖 AI-Powered Philosopher Agents
- **Multi-Persona System**: Unique philosopher personalities with distinct argumentation styles
- **Advanced Debate Logic**: Structured argument generation, attack/defense strategies, and follow-up responses
- **Dynamic Response Generation**: Context-aware responses using GPT-4/GPT-4o models
- **Emotional Intelligence**: Sentiment analysis and emotion-aware interactions

### 🧠 Retrieval Augmented Generation (RAG)
- **Vector Database Integration**: ChromaDB for efficient document retrieval
- **Multi-Source Knowledge**: Integration of philosophical texts, academic papers, and web sources
- **Intelligent Query Generation**: Automatic generation of search queries for argument enhancement
- **Real-time Knowledge Augmentation**: Dynamic retrieval during conversations

### 💬 Sophisticated Dialogue Management
- **Multi-Stage Debates**: Opening statements, cross-examination, rebuttals, and closing arguments
- **Turn-Based Logic**: Intelligent turn management and speaking order optimization
- **Context Preservation**: Comprehensive conversation history and state management
- **Real-time Moderation**: AI moderator for debate flow and rule enforcement

### 🎯 Advanced Argumentation System
- **Argument Structure Analysis**: Automatic extraction and analysis of argument components
- **Vulnerability Assessment**: Identification of logical weaknesses and attack opportunities
- **Strategic Planning**: Dynamic strategy selection based on opponent analysis
- **Evidence Integration**: Seamless incorporation of retrieved evidence into arguments

## 🛠️ Installation & Setup

### Prerequisites
- Node.js 18+ and npm/yarn
- Python 3.9+
- Docker and Docker Compose (optional)
- OpenAI API key

### Local Development

1. **Clone the repository**
```bash
git clone <repository-url>
cd sapiens_engine
```

2. **Backend Setup**
```bash
# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
export OPENAI_API_KEY="your-openai-api-key"

# Start the FastAPI server
cd api
python main.py
```

3. **Frontend Setup**
```bash
# Install Node.js dependencies
cd agoramind
npm install

# Start the Next.js development server
npm run dev
```

4. **Access the Application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Docker Deployment

```bash
# Build and start all services
docker-compose up --build

# Run in background
docker-compose up -d
```

## 📚 Usage Examples

### Basic Philosophical Debate

```python
from src.agents.factory import AgentFactory
from src.dialogue.state.dialogue_state import DialogueState

# Initialize dialogue state
dialogue_state = DialogueState(
    dialogue_id="ethics_debate_001",
    dialogue_type="philosophical_debate",
    topic="The Ethics of Artificial Intelligence",
    language="en"
)

# Create agents using factory
factory = AgentFactory()
agents = factory.create_debate_agents(
    pro_philosophers=["Aristotle", "Kant"],
    con_philosophers=["Nietzsche", "Foucault"],
    moderator_style="academic"
)

# Start the debate
for agent_name, agent in agents.items():
    print(f"Agent: {agent_name} - {agent.get_stance()}")
```

### RAG-Enhanced Conversation

```python
from src.rag.pipeline.rag_pipeline import RAGPipeline

# Initialize RAG system
rag = RAGPipeline(
    vector_store_path="./data/vector_store",
    embedding_model="sentence-transformers/all-MiniLM-L6-v2"
)

# Enhance argument with retrieved knowledge
enhanced_response = rag.enhance_argument(
    philosopher="Socrates",
    topic="What is justice?",
    argument="Justice is the harmony of the soul..."
)
```

## 🔧 Configuration

### Environment Variables

```bash
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o

# RAG Configuration  
VECTOR_DB_PATH=./data/vector_store
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Frontend Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Customizing Philosophers

Add new philosophers in `src/agents/configs/philosopher_configs.json`:

```json
{
  "custom_philosopher": {
    "name": "Custom Philosopher",
    "era": "Modern",
    "style": "analytical",
    "expertise": ["ethics", "logic"],
    "personality_traits": ["logical", "precise", "methodical"]
  }
}
```

## 📊 Performance & Costs

- **Average Debate Cost**: ~$1.20 per full debate (optimized to ~$0.86)
- **Token Usage**: 74,600 input + 37,600 output tokens per debate
- **Response Time**: 2-5 seconds per philosopher response
- **Supported Languages**: English, Korean (expandable)

## 🧪 Testing

```bash
# Run backend tests
cd src
python -m pytest tests/

# Run frontend tests  
cd agoramind
npm test

# Run integration tests
python -m pytest tests/integration/
```

## 📖 Documentation

- [LLM Usage Documentation](./LLM_Usage_Documentation.md) - Detailed LLM usage and cost analysis
- [RAG Experiment Report](./rag_experiment_report.md) - RAG system performance analysis
- [Cost Optimization Plan](./cost_optimization_plan.md) - Token usage optimization strategies

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔮 Roadmap

- [ ] Multi-language support expansion
- [ ] WebRTC integration for real-time audio debates
- [ ] Advanced emotion recognition and response
- [ ] Custom knowledge base upload functionality
- [ ] Mobile application development
- [ ] Integration with academic databases
- [ ] Advanced visualization of argument structures

## 🏆 Acknowledgments

- OpenAI for GPT-4/GPT-4o models
- Hugging Face for embedding models
- ChromaDB for vector storage
- FastAPI and Next.js communities

---

*Sapiens Engine - Where Philosophy Meets Artificial Intelligence* 🧠✨ 