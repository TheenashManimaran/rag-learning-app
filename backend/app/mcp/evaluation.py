import uuid

from app.core.gemini import gemini
from app.mcp.adaptive import recommend_next
from app.mcp.code_execution import run_python_solution
from app.storage import database


def evaluate_answer(user_id: str, question_id: str, answer: str, time_taken_seconds: float | None = None) -> dict:
    question = database.get_question(question_id, user_id)
    if not question:
        raise ValueError("Question not found.")

    q_type = question["type"]
    if q_type in {"mcq", "true_false", "fill_blank"}:
        score = 1.0 if answer.strip().lower() == question["correct_answer"].strip().lower() else 0.0
        if score == 1.0:
            feedback = f"Correct. {question.get('explanation', '')}".strip()
        else:
            feedback = (
                f"Incorrect. Correct answer: {question['correct_answer']}. "
                f"{question.get('explanation', '')}"
            ).strip()
    elif q_type == "coding":
        result = run_python_solution(answer, question.get("test_cases", []))
        score = float(result["score"])
        feedback = result["feedback"]
    else:
        prompt = f"""
Evaluate this student answer using the rubric and the source-grounded expected question.
Return strict JSON only: {{"score": 0.0, "feedback": "brief feedback"}}

Question: {question['question']}
Rubric: {question.get('rubric', 'Accuracy, completeness, and relevance.')}
Expected answer: {question.get('correct_answer', '')}
Explanation: {question.get('explanation', '')}
Student answer: {answer}

Scoring dimensions:
- accuracy
- completeness
- relevance
""".strip()
        data = gemini.generate_json(prompt, temperature=0.0)
        score = max(0.0, min(1.0, float(data.get("score", 0))))
        feedback = str(data.get("feedback", "Answer evaluated."))

    attempt = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "document_id": question["document_id"],
        "question_id": question["id"],
        "question_type": q_type,
        "topic": question["topic"],
        "difficulty": question["difficulty"],
        "score": score,
        "feedback": feedback,
        "time_taken_seconds": time_taken_seconds,
    }
    database.add_attempt(attempt)
    return {
        "score": round(score * 100, 1),
        "feedback": feedback,
        "is_correct": score >= 0.7,
        "next": recommend_next(user_id),
    }
