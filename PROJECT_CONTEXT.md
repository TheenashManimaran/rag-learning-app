# Project Context: Educator RAG Learning App

## 1. Project Overview

Educator is a local adaptive learning web application. Users upload educational PDFs, and the app turns those documents into a searchable knowledge base for grounded question answering, adaptive quiz generation, answer evaluation, and progress tracking.

The core idea is a RAG + MCP adaptive learning system:

- RAG retrieves relevant chunks from uploaded documents before asking Gemini to answer or generate quiz content.
- MCP-style components separate evaluation, adaptive difficulty, code execution, and progress tracking into focused backend modules.
- The frontend provides a simple browser UI for upload, Q&A, quiz, and dashboard workflows.

The project is designed for local development with a Python virtual environment, FastAPI backend, static frontend, local FAISS vector indexes, and SQLite persistence.

## 2. Tech Stack

- Backend: FastAPI, Pydantic, Uvicorn.
- Frontend: HTML, CSS, vanilla JavaScript.
- AI: Gemini via `google-genai`.
- Embeddings: Gemini embedding model `gemini-embedding-001`.
- Vector DB: FAISS CPU (`faiss-cpu`).
- Database: SQLite.
- PDF parsing: PyMuPDF.
- Environment loading: `python-dotenv` and `pydantic-settings`.
- Runtime target: Python 3.12.

## 3. Folder Structure

```text
rag-learning-app/
  backend/
    app/
      api/
        routes.py
      core/
        config.py
        gemini.py
      rag/
        chunker.py
        pdf_loader.py
        pipeline.py
        vector_store.py
      services/
        qa_service.py
        quiz_service.py
      mcp/
        adaptive.py
        code_execution.py
        evaluation.py
        progress.py
      storage/
        database.py
      main.py
    data/
      uploads/
      faiss/
      learning.db
  frontend/
    index.html
    styles.css
    app.js
  docs/
    architecture.md
  .env.example
  .python-version
  requirements.txt
  run.bat
  run.sh
  README.md
  AGENTS.md
  notes.md
  PROJECT_CONTEXT.md
```

Folder purposes:

- `backend/`: FastAPI backend and local runtime data.
- `backend/app/`: main Python package.
- `backend/app/api/`: REST routes and request models.
- `backend/app/core/`: configuration, environment loading, runtime directory setup, and Gemini client wrapper.
- `backend/app/rag/`: PDF extraction, text chunking, ingestion pipeline, FAISS storage, and retrieval.
- `backend/app/services/`: higher-level Q&A and quiz orchestration.
- `backend/app/mcp/`: modular learning tools for evaluation, adaptation, code execution, and progress.
- `backend/app/storage/`: SQLite connection helpers, schema initialization, and CRUD functions.
- `backend/data/`: generated local runtime data. Most contents are ignored by Git.
- `frontend/`: static browser UI served by FastAPI.
- `docs/`: architecture notes.
- `models/`: no dedicated `models/` folder currently exists. Request models live in `backend/app/api/routes.py`, and persisted records are represented as dictionaries in `backend/app/storage/database.py`.

## 4. RAG Pipeline Explanation

PDF processing:

1. `POST /api/upload` receives a PDF file.
2. `backend/app/rag/pipeline.py` validates the file extension and saves it under `backend/data/uploads`.
3. `backend/app/rag/pdf_loader.py` uses PyMuPDF to extract selectable text page by page.
4. `backend/app/rag/chunker.py` splits page text into overlapping chunks using sentence boundaries.
5. Empty or very short chunks are discarded.

Embedding creation:

1. `backend/app/rag/vector_store.py` sends chunk text to `GeminiClient.embed`.
2. Gemini uses `gemini-embedding-001` by default.
3. Embeddings are converted to `float32` NumPy arrays.
4. FAISS normalizes vectors with `faiss.normalize_L2`.
5. An `IndexFlatIP` FAISS index stores the normalized embeddings.

Retrieval:

1. User queries are embedded with Gemini using retrieval-query mode.
2. The query vector is normalized.
3. FAISS searches the document index for top-k matching chunks.
4. Retrieved chunks are returned with text, page number, and score.
5. Q&A and quiz generation prompts only receive retrieved context.

## 5. MCP Components

Quiz evaluation engine:

- File: `backend/app/mcp/evaluation.py`
- Entry point: `evaluate_answer(user_id, question_id, answer)`
- MCQ answers are checked by normalized string match.
- Coding answers are delegated to `run_python_solution`.
- Subjective answers are scored by Gemini using a rubric and strict JSON response.
- Each evaluated attempt is saved to SQLite.

Adaptive difficulty system:

- File: `backend/app/mcp/adaptive.py`
- Entry point: `recommend_next(user_id)`
- Uses average score and attempt count from progress history.
- Fewer than 3 attempts starts at `easy`.
- Average score >= 82 recommends `hard`.
- Average score >= 58 recommends `medium`.
- Lower scores recommend `easy`.
- Includes weak topics from progress tracking.

Code execution system:

- File: `backend/app/mcp/code_execution.py`
- Entry point: `run_python_solution(code, test_cases)`
- Requires submitted code to define `solve(...)`.
- Blocks dangerous imports such as `os`, `subprocess`, `socket`, `pathlib`, `shutil`, and `requests`.
- Blocks dangerous functions such as `eval`, `exec`, `open`, `compile`, and `__import__`.
- Runs code in a temporary directory with timeout from `CODE_TIMEOUT_SECONDS`.
- This is a local-development safety layer, not a production sandbox.

Progress tracker:

- File: `backend/app/mcp/progress.py`
- Entry point: `progress_summary(user_id)`
- Reads attempts from SQLite.
- Computes average score, attempt count, weak topics, topic performance, accuracy, optional timing, and recent trend.
- Weak topics are topics with average score below 70 percent.

## 6. Key Workflows

PDF upload -> embedding -> storage:

1. Frontend posts a PDF to `POST /api/upload`.
2. Backend saves the PDF under `backend/data/uploads`.
3. Text is extracted with PyMuPDF.
4. Text is chunked with overlap.
5. Chunks are embedded with Gemini.
6. FAISS index is written to `backend/data/faiss/u_<user>_d_<document>/index.faiss`.
7. Chunk metadata is written beside it as `metadata.json`.
8. Document metadata is inserted into SQLite.
9. API returns the document record.

Question answering flow:

1. Frontend sends `document_id`, `question`, and `user_id` to `POST /api/ask`.
2. Backend verifies the document belongs to the user.
3. The question is embedded as a retrieval query.
4. FAISS returns top-k source chunks.
5. `qa_service.py` builds a strict grounded prompt.
6. Gemini answers only from retrieved context.
7. API returns the answer, source chunks, confidence level, and explanation.

Quiz generation flow:

1. Frontend can call legacy `POST /api/quiz` for PDF mixed quizzes or `POST /api/generate-quiz` for configurable generation.
2. Advanced generation accepts `input_type`: `pdf`, `text`, or `topic`.
3. Advanced generation accepts `quiz_type`: `mcq`, `true_false`, `fill_blank`, `short`, or `mixed`.
4. If difficulty is omitted, `adaptive.py` recommends difficulty based on past attempts.
5. PDF mode retrieves context from FAISS and remains RAG-grounded.
6. Text mode uses supplied text as context.
7. Topic mode first tries FAISS retrieval when `document_id` is provided; if no good match is found, Gemini creates conceptual study context.
8. Previous and recently incorrect questions are loaded to reduce repetition and support retry-style practice.
9. Gemini generates strict JSON quiz data with explanations.
10. Questions are normalized, assigned IDs, and stored in SQLite.
11. Correct answers are hidden before returning to the frontend.

Evaluation flow:

1. Frontend sends `question_id`, `answer`, and `user_id` to `POST /api/quiz/submit`.
2. Backend loads the stored question payload.
3. MCQ answers are checked directly.
4. Coding answers run through the code execution tool.
5. Subjective answers are scored by Gemini.
6. Attempt data, correctness, and optional time taken are saved to SQLite.
7. API returns score, correctness, feedback, and next adaptive recommendation.

## 7. API Endpoints

Base prefix: `/api`

### `GET /api/health`

Request body: none.

Response:

```json
{
  "status": "ok"
}
```

### `GET /api/documents`

Query parameters:

- `user_id`: string, optional, default `default`.

Response:

```json
{
  "documents": [
    {
      "id": "document uuid",
      "user_id": "default",
      "filename": "source.pdf",
      "title": "source",
      "chunk_count": 12,
      "created_at": "ISO timestamp"
    }
  ]
}
```

### `POST /api/upload`

Content type: `multipart/form-data`

Request fields:

- `file`: PDF upload, required.
- `user_id`: string, optional, default `default`.

Response:

```json
{
  "document": {
    "id": "document uuid",
    "user_id": "default",
    "filename": "source.pdf",
    "title": "source",
    "chunk_count": 12
  }
}
```

### `POST /api/ask`

Request body:

```json
{
  "document_id": "document uuid",
  "question": "What does the document say about photosynthesis?",
  "user_id": "default"
}
```

Response:

```json
{
  "answer": "Grounded answer text.",
  "sources": [
    {
      "text": "Retrieved chunk text.",
      "page": 3,
      "score": 0.82
    }
  ],
  "confidence": "high",
  "explanation": "Why the answer follows from the retrieved context."
}
```

### `POST /api/generate-quiz`

Request body:

```json
{
  "user_id": "default",
  "document_id": "optional document uuid",
  "input_type": "pdf",
  "quiz_type": "mixed",
  "difficulty": "medium",
  "count": 5,
  "topic": "optional topic",
  "text": "optional source text"
}
```

Allowed values:

- `input_type`: `pdf`, `text`, `topic`
- `quiz_type`: `mcq`, `true_false`, `fill_blank`, `short`, `mixed`
- `difficulty`: `easy`, `medium`, `hard`, or omitted to use adaptive difficulty

Response:

```json
{
  "profile": {
    "difficulty": "medium",
    "weak_topics": [],
    "reason": "Based on average score and weakest topic history.",
    "source": "pdf",
    "topic_found_in_document": true
  },
  "questions": [
    {
      "id": "question uuid",
      "document_id": "document uuid",
      "type": "true_false",
      "topic": "Topic",
      "difficulty": "medium",
      "question": "Question text?",
      "options": ["True", "False"],
      "explanation": "Why the answer is correct, citing context.",
      "rubric": "",
      "starter_code": "",
      "test_cases": []
    }
  ],
  "sources": []
}
```

### `POST /api/quiz`

Legacy endpoint for PDF-based mixed adaptive quizzes. Prefer `/api/generate-quiz` for configurable quiz type and input mode.

Request body:

```json
{
  "document_id": "document uuid",
  "count": 5,
  "user_id": "default"
}
```

Response:

```json
{
  "profile": {
    "difficulty": "easy",
    "weak_topics": [],
    "reason": "Based on average score and weakest topic history."
  },
  "questions": [
    {
      "id": "question uuid",
      "document_id": "document uuid",
      "type": "mcq",
      "topic": "General",
      "difficulty": "easy",
      "question": "Question text?",
      "options": ["A", "B", "C", "D"],
      "rubric": "",
      "starter_code": "",
      "test_cases": []
    }
  ]
}
```

### `POST /api/quiz/submit`

Request body:

```json
{
  "question_id": "question uuid",
  "answer": "Student answer",
  "user_id": "default",
  "time_taken_seconds": 42.5
}
```

Response:

```json
{
  "score": 80.0,
  "feedback": "Brief feedback.",
  "is_correct": true,
  "next": {
    "difficulty": "medium",
    "weak_topics": ["Topic"],
    "reason": "Based on average score and weakest topic history."
  }
}
```

### `GET /api/dashboard`

Query parameters:

- `user_id`: string, optional, default `default`.

Response:

```json
{
  "average_score": 75.0,
  "attempt_count": 4,
  "weak_topics": ["Topic"],
  "topic_performance": [
    {
      "topic": "Topic",
      "average": 65.0,
      "accuracy": 50.0,
      "attempts": 2,
      "average_time_seconds": 31.2
    }
  ],
  "trend": [
    {
      "date": "ISO timestamp",
      "score": 80.0,
      "topic": "Topic",
      "is_correct": true
    }
  ]
}
```

## 8. Data Storage

FAISS:

- New FAISS indexes are stored under `backend/data/faiss`.
- Each document has its own directory named like `u_default_d_<document_id>`.
- Each directory contains `index.faiss` and `metadata.json`.
- Legacy local indexes under `backend/data/indexes` are still readable for compatibility.

SQLite:

- Database path defaults to `backend/data/learning.db`.
- Tables are created automatically on FastAPI startup.
- Tables:
  - `documents`: uploaded document metadata.
  - `questions`: generated quiz questions and hidden answer payloads.
  - `attempts`: scored submissions, correctness, optional time taken, and feedback history.

File storage:

- Uploaded PDFs are stored in `backend/data/uploads`.
- Filenames are prefixed with the generated document ID.
- Generated runtime data is ignored by Git.

## 9. Environment Setup

Python version:

- Required: Python 3.12.
- `.python-version` is set to `3.12`.

Virtual environment:

- Local venv path: `venv`.
- Do not install project dependencies globally.
- Startup scripts create or repair `venv`.
- If `venv` was created with the wrong Python version, scripts rebuild it.

Required packages:

- `fastapi==0.115.6`
- `uvicorn[standard]==0.34.0`
- `python-multipart==0.0.20`
- `pydantic==2.10.4`
- `pydantic-settings==2.7.1`
- `python-dotenv==1.2.2`
- `google-genai==0.5.0`
- `faiss-cpu==1.13.2`
- `PyMuPDF==1.25.1`
- `numpy==2.4.4`

Environment variables:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_GENERATION_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_EMBEDDING_DIMENSIONS=768
APP_NAME=RAG Adaptive Learning App
API_PREFIX=/api
MAX_UPLOAD_MB=30
TOP_K=5
CHUNK_SIZE=1200
CHUNK_OVERLAP=180
CODE_TIMEOUT_SECONDS=5
DATABASE_PATH=backend/data/learning.db
UPLOAD_DIR=backend/data/uploads
FAISS_INDEX_DIR=backend/data/faiss
```

Only `GEMINI_API_KEY` is required for AI-powered workflows. Other variables are optional overrides. Relative paths are resolved from the project root.

## 10. Known Issues and Limitations

- Gemini can return transient service errors such as 503; there is no retry/backoff layer yet.
- Gemini must return strict JSON for quiz generation and subjective grading; malformed JSON currently raises an error.
- Topic mode can fall back to conceptual Gemini-generated context when the topic is not found in a RAG document, so it is not document-grounded unless `topic_found_in_document` is true.
- FAISS storage is local-file based and one index is stored per document. There is no global index, compaction, migration system, or concurrent write coordination.
- Legacy FAISS indexes under `backend/data/indexes` are readable but new writes go to `backend/data/faiss`.
- PDFs must contain selectable text. There is no OCR fallback for scanned documents.
- Code execution is constrained but not production-grade isolation.
- There is no authentication; the frontend uses hardcoded `user_id = "default"`.
- `faiss-cpu` and `numpy` versions are pinned for local stability.
- The app depends on network access to Gemini for embedding, generation, quiz generation, and subjective grading.
- On Windows, generated launchers such as `pip.exe` or `uvicorn` may be blocked by security policy. Use `python -m pip` and `python -m uvicorn`.

## 11. How to Run the Project

Fast path:

Windows:

```bat
run.bat
```

Git Bash on Windows, Linux, or macOS:

```bash
./run.sh
```

Manual setup on Linux or macOS:

```bash
python3.12 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Manual setup on Windows PowerShell:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set:

```env
GEMINI_API_KEY=your_real_key
```

Run backend manually:

```bash
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open frontend:

```text
http://127.0.0.1:8000
```

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

## 12. Future Improvements

- Add authentication and real multi-user isolation.
- Add OCR support for scanned PDFs.
- Add retry/backoff for Gemini 503 and rate-limit errors.
- Add JSON repair or schema validation for Gemini responses.
- Add a dedicated retry-wrong-questions endpoint and frontend flow.
- Add background jobs for large PDF ingestion.
- Add tests for routes, chunking, retrieval, database operations, and MCP tools.
- Add a production code-execution sandbox with CPU, memory, filesystem, and network isolation.
- Add global search across multiple documents.
- Improve frontend UX, loading states, error handling, and mobile polish.
- Add model configuration UI and model fallback behavior.
- Add deployment documentation for production environments.

## 13. Rules for AI Agents

- Always preserve grounded RAG behavior. Answers must be based on retrieved document context.
- Do not hallucinate facts about uploaded documents. If context does not contain the answer, say the document does not provide enough information.
- Keep the modular architecture:
  - routes in `backend/app/api`
  - configuration and Gemini client in `backend/app/core`
  - RAG logic in `backend/app/rag`
  - orchestration in `backend/app/services`
  - learning tools in `backend/app/mcp`
  - persistence in `backend/app/storage`
- Do not move RAG, MCP, or database logic directly into route handlers.
- Do not commit real API keys or generated local data.
- Use Python 3.12 and the project `venv`.
- Prefer `python -m pip` and `python -m uvicorn` to avoid Windows launcher issues.
- Keep FAISS indexes persistent on disk.
- Keep SQLite auto-initialization on startup.
- Validate or sanitize AI-generated JSON before storing or rendering when extending the project.
- Do not weaken code execution restrictions without adding stronger isolation.
- Follow existing request and response shapes unless intentionally making a versioned API change.
- Update this file whenever project structure, setup, endpoints, models, workflows, dependencies, or runtime behavior changes.
