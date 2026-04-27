from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.api.quiz_routes import router as quiz_router
from app.mcp.evaluation import evaluate_answer
from app.mcp.progress import progress_summary
from app.rag.pipeline import ingest_pdf
from app.services.qa_service import answer_question
from app.services.quiz_service import generate_document_quiz
from app.storage import database


router = APIRouter()
router.include_router(quiz_router)


class AskRequest(BaseModel):
    document_id: str
    question: str = Field(min_length=3)
    user_id: str = "default"


class QuizRequest(BaseModel):
    document_id: str
    count: int = Field(default=5, ge=1, le=10)
    user_id: str = "default"


class SubmitRequest(BaseModel):
    question_id: str
    answer: str
    user_id: str = "default"
    time_taken_seconds: float | None = Field(default=None, ge=0)


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/documents")
def documents(user_id: str = "default") -> dict:
    return {"documents": database.list_documents(user_id)}


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...), user_id: str = Form("default")) -> dict:
    try:
        doc = await ingest_pdf(file, user_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"document": doc}


@router.post("/ask")
def ask(payload: AskRequest) -> dict:
    if not database.get_document(payload.document_id, payload.user_id):
        raise HTTPException(status_code=404, detail="Document not found.")
    try:
        return answer_question(payload.user_id, payload.document_id, payload.question)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/quiz")
def quiz(payload: QuizRequest) -> dict:
    if not database.get_document(payload.document_id, payload.user_id):
        raise HTTPException(status_code=404, detail="Document not found.")
    try:
        return generate_document_quiz(payload.user_id, payload.document_id, payload.count)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/quiz/submit")
def submit(payload: SubmitRequest) -> dict:
    try:
        return evaluate_answer(
            payload.user_id,
            payload.question_id,
            payload.answer,
            payload.time_taken_seconds,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/dashboard")
def dashboard(user_id: str = "default") -> dict:
    return progress_summary(user_id)
