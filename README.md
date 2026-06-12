# 🧠 CodeLens AI — Codebase Debugging & Knowledge Assistant

An AI-powered system that ingests codebases, builds structural + semantic understanding, and lets developers query, debug, and explore code using natural language.

![Architecture](https://img.shields.io/badge/Architecture-RAG%20%2B%20Vector%20Search-6c63ff)
![Backend](https://img.shields.io/badge/Backend-FastAPI-009688)
![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB)

## ✨ Features

- **📦 Codebase Ingestion** — Clone GitHub repos or upload ZIP files
- **🔍 Semantic Code Search** — FAISS-powered vector search with sentence-transformers
- ** AI Chat** — Natural language Q&A with streaming responses and code references
- **📝 Monaco Editor** — VS Code-like code viewer with syntax highlighting
- **📂 File Explorer** — Browse project structure with language-colored icons

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────────────┐     ┌──────────────┐
│   Frontend   │────▶│   FastAPI Backend     │────▶│  Gemini API  │
│  React+Vite  │◀────│                      │     └──────────────┘
└─────────────┘     │  ┌────────────────┐  │
                    │  │  Regex Parser  │  │
                    │  │  Code Parser   │  │
                    │  └────────────────┘  │
                    │  ┌────────────────┐  │
                    │  │  FAISS Vector  │  │
                    │  │    Index       │  │
                    │  └────────────────┘  │
                    └──────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Gemini API key

### Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Run server
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** — the frontend proxies API calls to the backend.

## 📖 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ingest/github` | Clone & analyze a GitHub repo |
| POST | `/api/ingest/upload` | Upload & analyze a ZIP file |
| GET | `/api/ingest/projects` | List all projects |
| POST | `/api/query/` | Query codebase (non-streaming) |
| POST | `/api/query/stream` | Query codebase (streaming) |
| GET | `/api/files/{id}/tree` | Get file tree |
| GET | `/api/files/{id}/content/{path}` | Get file content |

## 🧩 Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python, FastAPI |
| Parsing | Regex-based |
| Vector DB | FAISS |
| Embeddings | sentence-transformers |
| LLM | Google Gemini 1.5 Flash |
| Frontend | React 18, Vite |
| Styling | Tailwind CSS v4 |
| Code Editor | Monaco Editor |

## 📁 Project Structure

```
codebase-ai/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entry point
│   │   ├── config.py          # Settings
│   │   ├── models/schemas.py  # Pydantic models
│   │   ├── routers/           # API endpoints
│   │   ├── services/          # Core logic
│   │   └── utils/             # Helpers
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── services/api.js    # API client
│   │   ├── store/             # State management
│   │   ├── App.jsx            # Main layout
│   │   └── index.css          # Global styles
│   └── package.json
└── README.md
```
