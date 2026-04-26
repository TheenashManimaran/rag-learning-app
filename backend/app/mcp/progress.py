from collections import defaultdict

from app.storage import database


def progress_summary(user_id: str) -> dict:
    attempts = database.attempts_for_user(user_id)
    if not attempts:
        return {
            "average_score": 0,
            "attempt_count": 0,
            "weak_topics": [],
            "topic_performance": [],
            "trend": [],
        }

    topic_scores: dict[str, list[float]] = defaultdict(list)
    trend = []
    for attempt in reversed(attempts):
        topic_scores[attempt["topic"]].append(float(attempt["score"]))
        trend.append(
            {
                "date": attempt["created_at"],
                "score": round(float(attempt["score"]) * 100, 1),
                "topic": attempt["topic"],
            }
        )

    topic_performance = [
        {
            "topic": topic,
            "average": round(sum(scores) / len(scores) * 100, 1),
            "attempts": len(scores),
        }
        for topic, scores in topic_scores.items()
    ]
    weak_topics = [
        item["topic"]
        for item in sorted(topic_performance, key=lambda row: row["average"])
        if item["average"] < 70
    ][:5]

    avg = sum(float(attempt["score"]) for attempt in attempts) / len(attempts)
    return {
        "average_score": round(avg * 100, 1),
        "attempt_count": len(attempts),
        "weak_topics": weak_topics,
        "topic_performance": sorted(topic_performance, key=lambda row: row["topic"]),
        "trend": trend[-20:],
    }
