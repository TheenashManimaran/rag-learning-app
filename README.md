# RAG Adaptive Learning App

Production-ready starter for an AI-powered adaptive learning app using FastAPI, Gemini, FAISS, SQLite, and a modular RAG + MCP backend.

## Setup

From `rag-learning-app`:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key
# Optional override. Default: gemini-2.5-flash
GEMINI_GENERATION_MODEL=gemini-2.5-flash
# Optional override. Default: gemini-embedding-001
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
```

Run the backend inside the virtual environment:

```powershell
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## Architecture

- `backend/app/rag`: PDF extraction, chunking, Gemini embeddings, FAISS retrieval
- `backend/app/mcp`: evaluation engine, adaptive difficulty, code execution, progress tracking
- `backend/app/services`: grounded Q&A and quiz orchestration
- `backend/app/storage`: SQLite persistence
- `frontend`: HTML, CSS, vanilla JavaScript

## Notes

- Answers use a strict context-only prompt.
- Quiz generation retrieves document context and tracks previous questions to reduce repetition.
- Coding evaluation expects submitted Python to expose `solve(...)`.
- The code execution tool uses timeout and source validation, but operating-system level sandboxing should be added before running untrusted code in a public deployment.
