# Notes

## Decisions

- Use FastAPI for the backend because the app is API-first and Python-native.
- Use vanilla HTML/CSS/JS because the requirement explicitly avoids frontend frameworks.
- Use SQLite for persistence because the app is local/simple and does not need a separate database server yet.
- Use FAISS instead of ChromaDB because Chroma's Windows dependency `chroma-hnswlib` required Microsoft C++ Build Tools in this environment.
- Store FAISS metadata in JSON beside each index for easy inspection and portability.
- Keep RAG and MCP code separated so retrieval, generation, evaluation, adaptation, and progress tracking remain independently maintainable.
- Use `gemini-embedding-001` because older `text-embedding-004` produced a 404 with the current Gemini API path.
- Use `gemini-2.5-flash` because older `gemini-1.5-flash` produced a 404 with the current Gemini API path.
- Keep the active local virtual environment as `venv` because Python 3.14 failed during venv `ensurepip`, while Python 3.12 worked.

## Operational Notes

- The app is run from `backend` with `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
- The frontend is served by FastAPI from `frontend`.
- `.env` lives at the project root: `rag-learning-app/.env`.
- Uploaded documents, FAISS indexes, and SQLite data live under `backend/data`.
- The current user state is keyed by the hardcoded frontend user id `default`.

## Known Limitations

- No authentication or multi-user login UI yet.
- No background job queue for large PDFs.
- No OCR support for scanned PDFs.
- Subjective grading depends on Gemini availability and prompt compliance.
- Coding execution is a local development sandbox, not a production-grade isolation boundary.
- Generated quiz JSON parsing expects Gemini to return strict JSON.

## Useful Next Improvements

- Add auth and per-user document isolation.
- Add OCR fallback for scanned PDFs.
- Add retry/repair logic for malformed Gemini JSON.
- Add background ingestion status for long PDFs.
- Add automated tests for routes, chunking, retrieval, and MCP tools.
- Replace local code execution with a containerized sandbox.

