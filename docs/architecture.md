# Architecture

## Purpose

This project is an adaptive learning web app. Users upload educational PDFs, the backend builds a document-grounded RAG index, and learners can ask questions, generate quizzes, submit answers, and view progress.

## Runtime Shape

```text
frontend HTML/CSS/JS
        |
        | REST calls
        v
FastAPI backend
        |
        +-- RAG pipeline: PDF text -> chunks -> Gemini embeddings -> FAISS
        +-- AI services: grounded Q&A and quiz generation
        +-- MCP tools: evaluation, adaptive difficulty, code execution, progress
        +-- SQLite: documents, questions, attempts
```

## Project Structure

```text
rag-learning-app/
  backend/
    app/
      api/          REST routes
      core/         configuration and Gemini client
      rag/          PDF extraction, chunking, vector store, ingestion
      services/     Q&A and quiz orchestration
      mcp/          modular tool layer
      storage/      SQLite persistence
    data/           uploaded PDFs, FAISS indexes, SQLite DB
  frontend/         static HTML/CSS/vanilla JS app
  docs/             developer architecture notes
  requirements.txt
  README.md
```

## Backend Flow

### PDF Ingestion

Endpoint: `POST /api/upload`

1. Accepts a PDF upload.
2. Stores it under `backend/data/uploads`.
3. Extracts text with PyMuPDF in `rag/pdf_loader.py`.
4. Chunks extracted pages in `rag/chunker.py`.
5. Embeds chunks with Gemini in `core/gemini.py`.
6. Stores normalized embeddings in FAISS via `rag/vector_store.py`.
7. Persists document metadata in SQLite.

### Grounded Q&A

Endpoint: `POST /api/ask`

1. Embeds the user question as a retrieval query.
2. Retrieves top-k chunks from FAISS.
3. Sends only retrieved context to Gemini.
4. Uses the strict instruction: answer only from provided context.
5. Returns the answer plus source chunks and page numbers.

### Quiz Generation

Endpoint: `POST /api/quiz`

1. Reads progress history via MCP adaptive tool.
2. Retrieves relevant document context.
3. Sends context, difficulty, weak topics, and previous questions to Gemini.
4. Requires strict JSON containing MCQ, subjective, and optionally coding questions.
5. Stores generated questions in SQLite, including hidden answer/rubric metadata.

### Quiz Submission

Endpoint: `POST /api/quiz/submit`

Evaluation is delegated to MCP tools:

- MCQ: exact normalized string match.
- Subjective: Gemini evaluation with rubric dimensions.
- Coding: runs submitted Python `solve(...)` against JSON test cases.

Each attempt is persisted and the adaptive profile is recalculated.

## MCP Tool Layer

The `backend/app/mcp` folder models tool boundaries:

- `evaluation.py`: routes answers to the correct evaluator.
- `adaptive.py`: recommends easy, medium, or hard based on past scores.
- `code_execution.py`: executes Python answer code with source validation and timeout.
- `progress.py`: summarizes scores, weak topics, topic performance, and trends.

This is intentionally modular so the MCP tools can later be exposed through an actual MCP server without rewriting business logic.

## Data Storage

SQLite database: `backend/data/learning.db`

Tables:

- `documents`: uploaded document metadata.
- `questions`: generated quiz questions and hidden answer payloads.
- `attempts`: scored submissions and feedback history.

Vector data:

- Stored under `backend/data/indexes`.
- Each document gets a FAISS index plus JSON metadata.

## AI Models

Defaults live in `backend/app/core/config.py`.

- Generation: `gemini-2.5-flash`
- Embeddings: `gemini-embedding-001`
- Embedding dimensions: `768`

Environment overrides are loaded from `.env` in the project root.

## Frontend

The frontend is a static app served by FastAPI:

- `frontend/index.html`: views for upload, Q&A, quiz, dashboard.
- `frontend/styles.css`: responsive UI styling.
- `frontend/app.js`: REST API calls and client state.

The app currently uses a simple default user id: `default`.

## Security Notes

The coding evaluator blocks dangerous imports and functions and applies a timeout. This is useful for local development, but a production public deployment should move execution into an OS/container sandbox with strict CPU, memory, file, and network isolation.

