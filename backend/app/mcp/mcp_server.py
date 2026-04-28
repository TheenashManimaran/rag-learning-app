import asyncio
import json
import sqlite3
import uuid

from fastmcp import FastMCP

from app.core.llm_gateway import LLMGateway
from app.rag.vector_store import vector_store
from app.storage.database import connect, utc_now

mcp = FastMCP("Educator")
gateway = LLMGateway()

@mcp.tool()
async def search_knowledge_base(query: str, doc_id: str) -> list[dict]:
    """
    Search the vector database for relevant text chunks using FAISS.
    Returns the top 3 most relevant chunks for the given query and document ID.
    """
    def _search():
        with connect() as conn:
            row = conn.execute("SELECT user_id FROM documents WHERE id = ?", (doc_id,)).fetchone()
            if not row:
                raise ValueError(f"Document {doc_id} not found.")
            user_id = row["user_id"]
        return vector_store.retrieve(user_id=user_id, document_id=doc_id, query=query, top_k=3)
    
    return await asyncio.to_thread(_search)


@mcp.tool()
async def list_available_materials() -> list[dict]:
    """
    List all available educational materials in the database.
    Returns a list containing the id, title, and filename of each document.
    """
    def _list_materials():
        with connect() as conn:
            rows = conn.execute("SELECT id, title, filename FROM documents ORDER BY created_at DESC").fetchall()
            return [dict(row) for row in rows]
            
    return await asyncio.to_thread(_list_materials)


@mcp.tool()
async def get_context_summary(doc_id: str) -> dict:
    """
    Retrieve document metadata and its chunk count for context.
    """
    def _get_summary():
        with connect() as conn:
            row = conn.execute("SELECT id, filename, title, chunk_count, created_at FROM documents WHERE id = ?", (doc_id,)).fetchone()
            if not row:
                raise ValueError(f"Document {doc_id} not found.")
            return dict(row)
            
    return await asyncio.to_thread(_get_summary)


@mcp.tool()
async def fetch_student_stats(user_id: str) -> dict:
    """
    Retrieve a student's average score and list of weak topics (topics where average score < 70%).
    """
    def _fetch_stats():
        with connect() as conn:
            avg_row = conn.execute("SELECT AVG(score) as avg_score FROM attempts WHERE user_id = ?", (user_id,)).fetchone()
            avg_score = avg_row["avg_score"] if avg_row and avg_row["avg_score"] is not None else 0.0
            
            topic_rows = conn.execute(
                """
                SELECT topic, AVG(score) as topic_avg 
                FROM attempts 
                WHERE user_id = ? 
                GROUP BY topic 
                HAVING topic_avg < 0.7
                """, 
                (user_id,)
            ).fetchall()
            weak_topics = [row["topic"] for row in topic_rows]
            
            return {"average_score": avg_score, "weak_topics": weak_topics}
            
    return await asyncio.to_thread(_fetch_stats)


@mcp.tool()
async def update_learning_path(user_id: str, topic: str, score: float) -> dict:
    """
    Update the student's learning path by logging a new score for a topic.
    Returns the next recommended difficulty level based on their new average.
    """
    def _update_path():
        attempt_id = str(uuid.uuid4())
        with connect() as conn:
            # Minimal required fields for attempts table
            conn.execute(
                """
                INSERT INTO attempts 
                (id, user_id, document_id, question_id, question_type, topic, difficulty, score, feedback, is_correct, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt_id, user_id, "system", "system", "path_update", topic, "unknown",
                    score, "Path updated by AI", 1 if score >= 0.7 else 0, utc_now()
                )
            )
            
            # Recalculate avg score to determine next difficulty
            avg_row = conn.execute("SELECT AVG(score) as avg_score FROM attempts WHERE user_id = ?", (user_id,)).fetchone()
            avg_score = avg_row["avg_score"] if avg_row and avg_row["avg_score"] is not None else 0.0
            
            if avg_score >= 0.8:
                next_difficulty = "hard"
            elif avg_score >= 0.6:
                next_difficulty = "medium"
            else:
                next_difficulty = "easy"
                
            return {"new_average": avg_score, "next_difficulty": next_difficulty}
            
    return await asyncio.to_thread(_update_path)


@mcp.tool()
async def get_recent_mistakes(user_id: str) -> list[dict]:
    """
    Retrieve the last 5 incorrect questions (score < 70%) for a student.
    Returns the question text, topic, and the student's score.
    """
    def _get_mistakes():
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT q.question, q.topic, a.score, a.created_at
                FROM attempts a
                JOIN questions q ON q.id = a.question_id
                WHERE a.user_id = ? AND a.score < 0.7
                ORDER BY a.created_at DESC
                LIMIT 5
                """,
                (user_id,)
            ).fetchall()
            return [dict(row) for row in rows]
            
    return await asyncio.to_thread(_get_mistakes)


@mcp.tool()
async def validate_quiz_answer(question_id: str, student_answer: str) -> dict:
    """
    Validate a student's answer against the ground truth in the database.
    Returns correctness and an AI-generated hint if the answer is wrong.
    """
    def _fetch_question():
        with connect() as conn:
            row = conn.execute("SELECT payload FROM questions WHERE id = ?", (question_id,)).fetchone()
            if not row:
                raise ValueError(f"Question {question_id} not found.")
            return json.loads(row["payload"])
            
    question_data = await asyncio.to_thread(_fetch_question)
    
    evaluation_prompt = f"""
    Evaluate the student's answer against the ground truth.
    Question: {question_data.get('question')}
    Ground Truth context/answer details: {json.dumps(question_data)}
    Student Answer: {student_answer}
    
    Is the student's answer correct based on the ground truth? 
    If incorrect, provide a brief, helpful hint without giving away the direct answer.
    Respond strictly in JSON format: {{"correct": true, "hint": "string or null"}}
    """
    
    response = await gateway.get_response(
        role="JUDGE",
        messages=[{"role": "user", "content": evaluation_prompt}]
    )
    
    try:
        content = response.choices[0].message.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        result = json.loads(content)
        return {
            "correct": result.get("correct", False),
            "hint": result.get("hint")
        }
    except Exception as e:
        return {
            "correct": False,
            "hint": "Unable to definitively evaluate. Please review the material."
        }


@mcp.tool()
async def log_ai_decision(session_id: str, logic_reasoning: str) -> dict:
    """
    Log an AI decision trace for observability.
    """
    def _log_decision():
        with connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    logic_reasoning TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "INSERT INTO ai_logs (session_id, logic_reasoning, created_at) VALUES (?, ?, ?)",
                (session_id, logic_reasoning, utc_now())
            )
            return {"status": "success", "logged": True}
            
    return await asyncio.to_thread(_log_decision)


if __name__ == "__main__":
    mcp.run()
