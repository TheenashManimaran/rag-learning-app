import uuid

from app.core.gemini import gemini
from app.mcp.adaptive import recommend_next
from app.rag.vector_store import vector_store
from app.storage import database


def generate_quiz(user_id: str, document_id: str, count: int = 5) -> dict:
    profile = recommend_next(user_id)
    query = "key concepts weak topics " + " ".join(profile["weak_topics"])
    chunks = vector_store.retrieve(user_id, document_id, query, top_k=8)
    context = "\n\n".join(f"[Page {chunk['page']}] {chunk['text']}" for chunk in chunks)
    previous = "\n".join(database.previous_question_texts(user_id, document_id))

    prompt = f"""
Create a RAG-grounded adaptive quiz from the provided context only.

Rules:
- Use only facts, terminology, and examples present in the context.
- Avoid repeating previous questions.
- Generate exactly {count} questions.
- Include a mix of mcq and subjective questions.
- Add one coding question only if the context clearly supports programming or algorithms.
- Difficulty must be "{profile['difficulty']}" unless context is too limited.
- Return strict JSON only.

JSON schema:
{{
  "questions": [
    {{
      "type": "mcq|subjective|coding",
      "topic": "short topic label",
      "difficulty": "easy|medium|hard",
      "question": "question text",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "exact correct option text for mcq",
      "rubric": "scoring rubric for subjective",
      "starter_code": "optional starter code for coding",
      "test_cases": [{{"input": "JSON literal", "expected": "JSON literal"}}]
    }}
  ]
}}

Previous questions:
{previous or "None"}

Context:
{context}
""".strip()

    data = gemini.generate_json(prompt, temperature=0.2)
    questions = []
    for item in data.get("questions", []):
        q_type = item.get("type", "subjective")
        question = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "document_id": document_id,
            "type": q_type,
            "topic": item.get("topic", "General"),
            "difficulty": item.get("difficulty", profile["difficulty"]),
            "question": item.get("question", ""),
            "options": item.get("options", []) if q_type == "mcq" else [],
            "correct_answer": item.get("correct_answer", ""),
            "rubric": item.get("rubric", ""),
            "starter_code": item.get("starter_code", ""),
            "test_cases": item.get("test_cases", []),
        }
        if question["question"]:
            questions.append(question)

    database.add_questions(questions)
    return {"profile": profile, "questions": _hide_answers(questions)}


def _hide_answers(questions: list[dict]) -> list[dict]:
    hidden = []
    for question in questions:
        copy = dict(question)
        copy.pop("correct_answer", None)
        copy.pop("user_id", None)
        hidden.append(copy)
    return hidden
