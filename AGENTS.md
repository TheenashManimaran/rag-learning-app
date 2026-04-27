# AGENTS.md

## Project Mission

Build and maintain a production-ready adaptive learning app where uploaded educational PDFs power grounded Q&A, adaptive quizzes, answer evaluation, and progress tracking.

## Required Stack

- Frontend: HTML, CSS, vanilla JavaScript.
- Backend: FastAPI.
- AI: Gemini for generation, evaluation, and embeddings.
- Vector DB: FAISS.
- Database: SQLite.
- Python dependencies must stay inside the project virtual environment.

## Run Commands

Preferred local startup from the project root:

```powershell
.\run.bat
```

Git Bash on Windows and Unix-like shells:

```bash
./run.sh
```

Manual PowerShell run:

```powershell
cd E:\RagProject\Project1\rag-learning-app
.\venv\Scripts\Activate.ps1
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

App URL:

```text
http://127.0.0.1:8000
```

Health check:

```powershell
curl.exe http://127.0.0.1:8000/api/health
```

## Environment

`.env` belongs at the project root:

```text
rag-learning-app/.env
```

Expected keys:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_GENERATION_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
DATABASE_PATH=backend/data/learning.db
UPLOAD_DIR=backend/data/uploads
FAISS_INDEX_DIR=backend/data/faiss
```

All variables except `GEMINI_API_KEY` are optional unless overriding defaults. Relative paths are resolved from the project root.

## Code Ownership Map

- API routes: `backend/app/api/routes.py`
- Config: `backend/app/core/config.py`
- Gemini wrapper: `backend/app/core/gemini.py`
- PDF extraction: `backend/app/rag/pdf_loader.py`
- Chunking: `backend/app/rag/chunker.py`
- Vector storage/retrieval: `backend/app/rag/vector_store.py`
- Ingestion pipeline: `backend/app/rag/pipeline.py`
- Grounded Q&A: `backend/app/services/qa_service.py`
- Quiz generation: `backend/app/services/quiz_service.py`
- MCP evaluation: `backend/app/mcp/evaluation.py`
- MCP adaptive difficulty: `backend/app/mcp/adaptive.py`
- MCP code execution: `backend/app/mcp/code_execution.py`
- MCP progress tracking: `backend/app/mcp/progress.py`
- SQLite helpers: `backend/app/storage/database.py`
- Frontend: `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`

## Development Rules

- Keep backend modules separated by responsibility. Do not collapse RAG and MCP logic into route handlers.
- Do not install Python packages globally. Use `venv`.
- Use Python 3.12. The startup scripts rebuild `venv` if it was created with the wrong Python version.
- Prefer `python -m pip` and `python -m uvicorn` over direct `pip` or `uvicorn` launchers, especially on Windows where local policy may block generated `.exe` shims.
- Do not commit real API keys.
- Keep `.env` local and out of generated documentation except for placeholder examples.
- Preserve the strict grounded-answer behavior: answers must only use retrieved context.
- Keep quiz generation grounded in retrieved context and continue tracking previous questions to reduce repetition.
- Treat generated AI JSON as untrusted input. Validate before storing or rendering where practical.
- Keep coding answer execution constrained. Do not weaken blocked imports, blocked functions, or timeout behavior without replacing it with stronger isolation.

## Validation Checklist

After backend edits:

```powershell
cd E:\RagProject\Project1\rag-learning-app\backend
..\venv\Scripts\python.exe -B -c "import ast, pathlib; [ast.parse(p.read_text(), filename=str(p)) for p in pathlib.Path('app').rglob('*.py')]; print('syntax ok')"
curl.exe http://127.0.0.1:8000/api/health
```

After frontend edits:

- Open `http://127.0.0.1:8000`.
- Check Upload, Q&A, Quiz, and Dashboard views.
- Confirm text fits at desktop and mobile widths.

## Current Assumptions

- Single local user id is `default`.
- PDFs contain selectable text.
- Gemini API key is valid and has access to the configured models.
- New FAISS indexes are stored under `backend/data/faiss`; old local indexes under `backend/data/indexes` remain readable for compatibility.
- The app is intended for local development unless extra production hardening is added.
