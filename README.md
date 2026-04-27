# Educator: RAG Learning App

Educator is a local FastAPI app for PDF-based learning. It extracts PDF text, chunks it, creates Gemini embeddings, stores them in a local FAISS index, and uses SQLite to track documents, quiz questions, attempts, and progress.

## Requirements

- Python 3.12
- A Gemini API key

## Quick Start

From the `rag-learning-app` directory:

### Windows

```bat
run.bat
```

Git Bash on Windows is also supported:

```bash
./run.sh
```

### Linux or macOS

```bash
chmod +x run.sh
./run.sh
```

The startup script creates `venv`, installs dependencies, creates `.env` from `.env.example` if needed, and starts the backend at:

```text
http://127.0.0.1:8000
```

If `.env` was created for you, stop the server, add your real `GEMINI_API_KEY`, then run the script again.

## Manual Setup

```bash
python3.12 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

On Windows PowerShell:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_GENERATION_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
```

Run the backend:

```bash
cd backend
python -m uvicorn app.main:app --reload
```

Use `python -m pip` and `python -m uvicorn` instead of direct `pip` or `uvicorn` launchers on Windows. Some local security policies block the generated `.exe` shims in `venv/Scripts`, while module execution through Python still works.

## Local Data

The app creates these folders automatically:

- `backend/data/uploads` for uploaded PDFs
- `backend/data/faiss` for FAISS indexes and metadata
- `backend/data/learning.db` for SQLite data

Generated local data is ignored by Git.

## API Usage

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

Upload a PDF:

```bash
curl -X POST http://127.0.0.1:8000/api/upload \
  -F "user_id=default" \
  -F "file=@/path/to/document.pdf"
```

Ask a question:

```bash
curl -X POST http://127.0.0.1:8000/api/ask \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"default\",\"document_id\":\"DOCUMENT_ID\",\"question\":\"What is this about?\"}"
```

Generate a quiz:

```bash
curl -X POST http://127.0.0.1:8000/api/quiz \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"default\",\"document_id\":\"DOCUMENT_ID\",\"count\":5}"
```

Submit an answer:

```bash
curl -X POST http://127.0.0.1:8000/api/quiz/submit \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"default\",\"question_id\":\"QUESTION_ID\",\"answer\":\"My answer\"}"
```

Dashboard:

```bash
curl "http://127.0.0.1:8000/api/dashboard?user_id=default"
```

## Notes

- `GEMINI_API_KEY` is required for PDF ingestion, Q&A, quiz generation, and subjective answer evaluation.
- FAISS indexes are saved to disk and loaded on each retrieval.
- Existing legacy indexes under `backend/data/indexes` are still readable, but new indexes are written to `backend/data/faiss`.
- SQLite tables are created automatically on backend startup.
- The frontend is served by FastAPI from `frontend/` at the root URL.
