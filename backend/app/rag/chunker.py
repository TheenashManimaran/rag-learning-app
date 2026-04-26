import re

from app.core.config import settings


def _sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", normalized) if part.strip()]


def chunk_pages(pages: list[dict[str, str | int]]) -> list[dict[str, str | int]]:
    chunks: list[dict[str, str | int]] = []
    for page in pages:
        current: list[str] = []
        current_len = 0
        for sentence in _sentences(str(page["text"])):
            if current and current_len + len(sentence) > settings.chunk_size:
                text = " ".join(current).strip()
                chunks.append({"text": text, "page": int(page["page"])})
                overlap = text[-settings.chunk_overlap :]
                current = [overlap, sentence]
                current_len = len(overlap) + len(sentence)
            else:
                current.append(sentence)
                current_len += len(sentence)
        if current:
            chunks.append({"text": " ".join(current).strip(), "page": int(page["page"])})
    return [chunk for chunk in chunks if len(str(chunk["text"])) > 80]
