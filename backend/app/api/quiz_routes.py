from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.quiz_service import generate_quiz


router = APIRouter()


class GenerateQuizRequest(BaseModel):
    user_id: str = "default"
    document_id: str | None = None
    input_type: Literal["pdf", "text", "topic"]
    quiz_type: Literal["mcq", "true_false", "fill_blank", "short", "mixed"]
    difficulty: Literal["easy", "medium", "hard"] | None = None
    count: int = Field(default=5, ge=1, le=10)
    topic: str | None = None
    text: str | None = None


@router.post("/generate-quiz")
def generate_structured_quiz(payload: GenerateQuizRequest) -> dict:
    try:
        return generate_quiz(
            user_id=payload.user_id,
            document_id=payload.document_id,
            input_type=payload.input_type,
            quiz_type=payload.quiz_type,
            difficulty=payload.difficulty,
            count=payload.count,
            topic=payload.topic,
            text=payload.text,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
