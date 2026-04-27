import uuid
from typing import Any, Literal

from app.core.gemini import gemini
from app.mcp.adaptive import recommend_next
from app.rag.vector_store import vector_store
from app.storage import database


InputType = Literal["topic", "text", "pdf"]
QuizType = Literal["mcq", "true_false", "fill_blank", "short", "mixed"]
Difficulty = Literal["easy", "medium", "hard"]

VALID_INPUT_TYPES = {"topic", "text", "pdf"}
VALID_QUIZ_TYPES = {"mcq", "true_false", "fill_blank", "short", "mixed"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
TOPIC_FOUND_THRESHOLD = 0.25


def generate_quiz(
    user_id: str,
    document_id: str | None,
    input_type: str,
    quiz_type: str,
    difficulty: str | None,
    count: int,
    topic: str | None = None,
    text: str | None = None,
) -> dict:
    input_type = _require_choice(input_type, VALID_INPUT_TYPES, "input_type")
    quiz_type = _require_choice(quiz_type, VALID_QUIZ_TYPES, "quiz_type")
    if difficulty:
        difficulty = _require_choice(difficulty, VALID_DIFFICULTIES, "difficulty")

    profile = recommend_next(user_id)
    effective_difficulty = difficulty or profile["difficulty"]
    context_bundle = _build_context(
        user_id=user_id,
        document_id=document_id,
        input_type=input_type,
        topic=topic,
        text=text,
        profile=profile,
    )
    previous = "\n".join(database.previous_question_texts(user_id, document_id))
    retry_focus = "\n".join(database.incorrect_question_texts(user_id))
    prompt = _build_prompt(
        quiz_type=quiz_type,
        difficulty=effective_difficulty,
        count=count,
        context=context_bundle["context"],
        topic=topic,
        previous=previous,
        retry_focus=retry_focus,
        context_source=context_bundle["source"],
    )

    data = gemini.generate_json(prompt, temperature=0.2)
    questions = _normalize_questions(
        items=data.get("questions", []),
        user_id=user_id,
        document_id=document_id,
        fallback_difficulty=effective_difficulty,
        fallback_topic=topic or context_bundle["topic"] or "General",
    )
    if not questions:
        raise ValueError("Gemini did not generate any valid questions.")

    database.add_questions(questions)
    return {
        "profile": {
            **profile,
            "difficulty": effective_difficulty,
            "source": context_bundle["source"],
            "topic_found_in_document": context_bundle["topic_found_in_document"],
        },
        "questions": _hide_answers(questions),
        "sources": context_bundle["sources"],
    }


def generate_document_quiz(user_id: str, document_id: str, count: int = 5) -> dict:
    profile = recommend_next(user_id)
    return generate_quiz(
        user_id=user_id,
        document_id=document_id,
        input_type="pdf",
        quiz_type="mixed",
        difficulty=profile["difficulty"],
        count=count,
        topic="key concepts weak topics " + " ".join(profile["weak_topics"]),
    )


def _build_context(
    user_id: str,
    document_id: str | None,
    input_type: str,
    topic: str | None,
    text: str | None,
    profile: dict[str, Any],
) -> dict[str, Any]:
    if input_type == "pdf":
        if not document_id:
            raise ValueError("document_id is required when input_type is 'pdf'.")
        query = topic or "key concepts weak topics " + " ".join(profile["weak_topics"])
        chunks = vector_store.retrieve(user_id, document_id, query, top_k=8)
        if not chunks:
            raise ValueError("No PDF context found. Upload or re-index the document first.")
        return {
            "context": _format_chunks(chunks),
            "sources": chunks,
            "source": "pdf",
            "topic": topic,
            "topic_found_in_document": True,
        }

    if input_type == "text":
        if not text or len(text.strip()) < 40:
            raise ValueError("text must contain enough content when input_type is 'text'.")
        return {
            "context": f"[Provided Text]\n{text.strip()}",
            "sources": [],
            "source": "text",
            "topic": topic,
            "topic_found_in_document": None,
        }

    if not topic or len(topic.strip()) < 3:
        raise ValueError("topic is required when input_type is 'topic'.")

    chunks = []
    topic_found = False
    if document_id:
        chunks = vector_store.retrieve(user_id, document_id, topic, top_k=8)
        topic_found = bool(chunks and max(chunk.get("score", 0) for chunk in chunks) >= TOPIC_FOUND_THRESHOLD)
    if topic_found:
        return {
            "context": _format_chunks(chunks),
            "sources": chunks,
            "source": "pdf_topic_match",
            "topic": topic,
            "topic_found_in_document": True,
        }

    conceptual_context = gemini.generate_text(
        f"""
Create concise study context for the topic below so a quiz can be generated.
Use broadly accepted educational facts. Do not invent document-specific claims.

Topic: {topic}
""".strip(),
        temperature=0.1,
    )
    return {
        "context": f"[Conceptual Topic Context]\n{conceptual_context}",
        "sources": chunks,
        "source": "conceptual_topic",
        "topic": topic,
        "topic_found_in_document": False,
    }


def _build_prompt(
    quiz_type: str,
    difficulty: str,
    count: int,
    context: str,
    topic: str | None,
    previous: str,
    retry_focus: str,
    context_source: str,
) -> str:
    type_rules = {
        "mcq": "Generate only MCQ questions with exactly 4 options and one exact correct_answer.",
        "true_false": "Generate only true_false questions. correct_answer must be 'true' or 'false'.",
        "fill_blank": "Generate only fill_blank questions using a clear blank such as '____'.",
        "short": "Generate only short answer questions with a concise expected correct_answer and rubric.",
        "mixed": "Generate a balanced mix of mcq, true_false, fill_blank, and short questions. Include coding only when the context clearly supports programming.",
    }[quiz_type]
    grounding_rule = (
        "Use only the retrieved PDF context."
        if context_source in {"pdf", "pdf_topic_match"}
        else "Use only the provided context."
    )
    return f"""
Create a structured learning quiz.

Rules:
- {grounding_rule}
- quiz_type: {quiz_type}
- difficulty: {difficulty}
- Generate exactly {count} questions.
- {type_rules}
- Avoid repeating previous questions.
- If retry focus is provided, generate similar practice around those weak concepts without duplicating wording.
- Every question must include an explanation that cites the provided context marker, such as [Page 2], [Provided Text], or [Conceptual Topic Context].
- The explanation must state why the correct answer is correct.
- Return strict JSON only. No markdown.

JSON schema:
{{
  "questions": [
    {{
      "type": "mcq | true_false | fill_blank | short | coding",
      "question": "text",
      "options": [],
      "correct_answer": "",
      "difficulty": "easy | medium | hard",
      "topic": "",
      "explanation": "",
      "rubric": "",
      "starter_code": "",
      "test_cases": [{{"input": "JSON literal", "expected": "JSON literal"}}]
    }}
  ]
}}

Topic hint:
{topic or "Use the strongest concepts in the context."}

Previous questions:
{previous or "None"}

Retry focus from recent incorrect answers:
{retry_focus or "None"}

Context:
{context}
""".strip()


def _normalize_questions(
    items: list[dict[str, Any]],
    user_id: str,
    document_id: str | None,
    fallback_difficulty: str,
    fallback_topic: str,
) -> list[dict[str, Any]]:
    questions = []
    for item in items:
        q_type = _normalize_type(str(item.get("type", "short")))
        question_text = str(item.get("question", "")).strip()
        if not question_text:
            continue
        options = item.get("options", [])
        if q_type == "true_false":
            options = ["True", "False"]
        elif q_type != "mcq":
            options = []

        questions.append(
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "document_id": document_id or "",
                "type": q_type,
                "topic": str(item.get("topic") or fallback_topic or "General"),
                "difficulty": _coerce_difficulty(str(item.get("difficulty") or fallback_difficulty)),
                "question": question_text,
                "options": options if isinstance(options, list) else [],
                "correct_answer": str(item.get("correct_answer", "")),
                "explanation": str(item.get("explanation", "")),
                "rubric": str(item.get("rubric", "")),
                "starter_code": str(item.get("starter_code", "")),
                "test_cases": item.get("test_cases", []) if isinstance(item.get("test_cases", []), list) else [],
            }
        )
    return questions


def _format_chunks(chunks: list[dict[str, Any]]) -> str:
    return "\n\n".join(f"[Page {chunk['page']}] {chunk['text']}" for chunk in chunks)


def _hide_answers(questions: list[dict]) -> list[dict]:
    hidden = []
    for question in questions:
        copy = dict(question)
        copy.pop("correct_answer", None)
        copy.pop("user_id", None)
        hidden.append(copy)
    return hidden


def _normalize_type(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    aliases = {
        "subjective": "short",
        "short_answer": "short",
        "fill_in_the_blank": "fill_blank",
        "fillblank": "fill_blank",
        "truefalse": "true_false",
    }
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in {"mcq", "true_false", "fill_blank", "short", "coding"} else "short"


def _coerce_difficulty(value: str) -> str:
    normalized = value.strip().lower()
    return normalized if normalized in VALID_DIFFICULTIES else "medium"


def _require_choice(value: str, choices: set[str], field: str) -> str:
    normalized = value.strip().lower()
    if normalized not in choices:
        raise ValueError(f"{field} must be one of: {', '.join(sorted(choices))}.")
    return normalized
