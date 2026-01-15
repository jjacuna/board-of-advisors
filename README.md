# Board of Directors AI

A Flask-based application that simulates a corporate board of directors, where multiple AI advisors (CFO, CTO, CMO) provide perspectives on your questions, and a CEO synthesizes their input into an executive decision.

## Features

- **Multi-Model AI Board**: Each advisor uses a different AI model via OpenRouter
- **Customizable Advisors**: Edit names, roles, models, and system prompts via Settings
- **Knowledge Base (RAG)**: Upload documents to give your board context about your business
- **Conversation History**: All conversations are saved and accessible from the sidebar
- **Clean UI**: Genspark-inspired design with responsive layout

## The Board

| Advisor | Default Model | Focus Area |
|---------|---------------|------------|
| Victoria Sterling (CFO) | Google Gemini 2.0 Flash | Financial analysis, ROI, costs, risks |
| Marcus Chen (CTO) | Anthropic Claude 3.5 Haiku | Technical feasibility, scalability |
| Sophia Rodriguez (CMO) | Meta Llama 3.1 8B | Market positioning, customer perception |
| Alexandra Wright (CEO) | OpenAI GPT-4o Mini | Executive synthesis and decision-making |

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/jjacuna/board-of-advisors.git
cd board-of-advisors
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables
```bash
cp .env.example .env
# Edit .env and add your API keys
```

Required:
- `OPENROUTER_API_KEY` - Get from [openrouter.ai](https://openrouter.ai)

Optional (for Knowledge Base):
- `OPENAI_API_KEY` - For text embeddings
- `PINECONE_API_KEY` - For vector storage (free tier at [pinecone.io](https://pinecone.io))

### 4. Run the application
```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

## Knowledge Base (RAG)

The Knowledge Base feature allows you to upload documents that the board will reference when answering questions.

### Supported File Types
- PDF (.pdf)
- Word Documents (.docx)
- Text Files (.txt)
- Markdown (.md)

### How It Works
1. Go to Settings > Knowledge Base
2. Upload your documents (max 10MB each)
3. Documents are chunked, embedded, and stored in Pinecone
4. When you ask questions, relevant context is retrieved and provided to all advisors

### Setup
1. Create a free account at [Pinecone](https://pinecone.io)
2. Get an API key from [OpenAI](https://platform.openai.com)
3. Add both keys to your `.env` file

## Project Structure

```
board-of-directors/
├── app.py              # Flask application and routes
├── advisors.py         # Advisor configurations and API calls
├── database.py         # SQLite database functions
├── knowledge.py        # RAG/document processing module
├── schema.sql          # Database schema
├── templates/
│   └── index.html      # Frontend UI
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── Procfile            # Railway deployment
└── runtime.txt         # Python version
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main application page |
| `/ask` | POST | Submit a question to the board |
| `/history` | GET | Get conversation history |
| `/settings` | GET | Get all advisor configurations |
| `/settings/<key>` | POST | Update an advisor's settings |
| `/documents` | GET | List all uploaded documents |
| `/documents/upload` | POST | Upload a document |
| `/documents/<id>` | DELETE | Delete a document |

## Deployment

### Railway
1. Connect your GitHub repo to Railway
2. Add environment variables in Railway dashboard
3. Deploy automatically on push

### Environment Variables for Production
```
OPENROUTER_API_KEY=your_key
OPENAI_API_KEY=your_key (optional)
PINECONE_API_KEY=your_key (optional)
PORT=5000
```

## Tech Stack

- **Backend**: Python 3.12, Flask
- **Database**: SQLite
- **AI Models**: OpenRouter API (multi-model)
- **Vector Store**: Pinecone (for RAG)
- **Embeddings**: OpenAI text-embedding-3-small
- **Frontend**: HTML, Tailwind CSS (CDN)

## License

MIT
