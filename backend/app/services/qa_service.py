from typing import Any

from app.core.config import settings
from app.core.gemini import gemini
from app.rag.vector_store import vector_store


def answer_question(user_id: str, document_id: str, question: str) -> dict:
    chunks = vector_store.retrieve(user_id, document_id, question, settings.top_k)
    context = "\n\n".join(
        f"[Page {chunk['page']}] {chunk['text']}" for chunk in chunks
    )
    if not chunks:
        return {
            "answer": "I don't know based on the uploaded document.",
            "sources": [],
            "confidence": "low",
            "explanation": "No relevant document chunks were retrieved for this question.",
        }

    prompt = f"""
You are a grounded learning assistant.

Answer ONLY using the provided context.
If the answer is not present in the context, say: "I don't know based on the uploaded document."
Do not use outside knowledge.

Return strict JSON only with this schema:
{{
  "answer": "direct answer",
  "explanation": "why the answer follows from the context, citing page markers",
  "confidence": "low | medium | high"
}}

Confidence rules:
- high: the context directly and completely answers the question.
- medium: the context partially answers the question or requires a small inference.
- low: the context is weak, indirect, or missing the answer.

Context:
{context}

Question:
{question}
""".strip()
    data = gemini.generate_json(prompt, temperature=0.0)
    confidence = _confidence(data.get("confidence"), chunks)
    return {
        "answer": str(data.get("answer") or "I don't know based on the uploaded document.").strip(),
        "sources": chunks,
        "confidence": confidence,
        "explanation": str(data.get("explanation") or _fallback_explanation(confidence, chunks)).strip(),
    }


def _confidence(value: Any, chunks: list[dict[str, Any]]) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"low", "medium", "high"}:
        return normalized
    best_score = max((float(chunk.get("score", 0)) for chunk in chunks), default=0.0)
    if best_score >= 0.65:
        return "high"
    if best_score >= 0.35:
        return "medium"
    return "low"


def _fallback_explanation(confidence: str, chunks: list[dict[str, Any]]) -> str:
    if not chunks:
        return "No source chunks were available."
    pages = ", ".join(f"Page {chunk['page']}" for chunk in chunks[:3])
    return f"The answer is based on the retrieved source context from {pages}. Confidence is {confidence}."
