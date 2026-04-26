import json
from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings


class GeminiClient:
    def __init__(self) -> None:
        if not settings.gemini_api_key:
            self.client = None
        else:
            self.client = genai.Client(api_key=settings.gemini_api_key)

    @property
    def available(self) -> bool:
        return self.client is not None

    def embed(self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
        if not self.client:
            raise RuntimeError("GEMINI_API_KEY is required for document embeddings.")

        vectors: list[list[float]] = []
        for text in texts:
            response = self.client.models.embed_content(
                model=settings.gemini_embedding_model,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=settings.gemini_embedding_dimensions,
                ),
            )
            embedding = response.embeddings[0].values
            vectors.append([float(value) for value in embedding])
        return vectors

    def generate_text(self, prompt: str, temperature: float = 0.2) -> str:
        if not self.client:
            raise RuntimeError("GEMINI_API_KEY is required for AI generation.")

        response = self.client.models.generate_content(
            model=settings.gemini_generation_model,
            contents=prompt,
            config={"temperature": temperature},
        )
        return (response.text or "").strip()

    def generate_json(self, prompt: str, temperature: float = 0.2) -> dict[str, Any]:
        text = self.generate_text(prompt, temperature=temperature)
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Gemini did not return valid JSON: {text[:500]}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Gemini JSON response must be an object.")
        return parsed


gemini = GeminiClient()
