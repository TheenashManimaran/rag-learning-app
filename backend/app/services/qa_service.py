from app.core.config import settings
from app.core.gemini import gemini
from app.rag.vector_store import vector_store


def answer_question(user_id: str, document_id: str, question: str) -> dict:
    chunks = vector_store.retrieve(user_id, document_id, question, settings.top_k)
    context = "\n\n".join(
        f"[Page {chunk['page']}] {chunk['text']}" for chunk in chunks
    )
    prompt = f"""
You are a grounded learning assistant.

Answer ONLY using the provided context.
If the answer is not present in the context, say: "I don't know based on the uploaded document."
Do not use outside knowledge.

Context:
{context}

Question:
{question}

Answer:
""".strip()
    answer = gemini.generate_text(prompt, temperature=0.0)
    return {"answer": answer, "sources": chunks}
