from app.mcp.progress import progress_summary


def recommend_next(user_id: str) -> dict:
    progress = progress_summary(user_id)
    score = progress["average_score"]
    if progress["attempt_count"] < 3:
        difficulty = "easy"
    elif score >= 82:
        difficulty = "hard"
    elif score >= 58:
        difficulty = "medium"
    else:
        difficulty = "easy"

    return {
        "difficulty": difficulty,
        "weak_topics": progress["weak_topics"],
        "reason": "Based on average score and weakest topic history.",
    }
