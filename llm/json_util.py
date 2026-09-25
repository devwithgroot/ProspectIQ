from __future__ import annotations

import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from config.research_log import get_logger

log = get_logger("json")


T = TypeVar("T", bound=BaseModel)

_FENCE_RE = re.compile(
    r"```(?:json)?\s*(.*?)\s*```",
    re.DOTALL | re.IGNORECASE,
)
_THINK_RE = re.compile(
    r"<think>.*?</think>",
    re.DOTALL | re.IGNORECASE,
)
_THINK_CAPTURE_RE = re.compile(
    r"<think>(.*?)</think>",
    re.DOTALL | re.IGNORECASE,
)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def extract_think(text: str) -> str:
    parts = [
        match.group(1).strip()
        for match in _THINK_CAPTURE_RE.finditer(text or "")
        if match.group(1).strip()
    ]
    return " ".join(parts)


def reason_lines(
    text: str,
    *,
    limit: int = 2,
    width: int = 180,
) -> list[str]:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return []

    sentences = [part.strip() for part in _SENTENCE_RE.split(cleaned) if part.strip()]
    if not sentences:
        sentences = [cleaned]

    lines: list[str] = []
    for sentence in sentences:
        if len(sentence) > width:
            sentence = sentence[: width - 1].rsplit(" ", 1)[0] + "…"
        lines.append(f"Why: {sentence}")
        if len(lines) >= limit:
            break
    return lines


def extract_json_text(text: str) -> str:
    cleaned = _THINK_RE.sub("", text).strip()

    fenced = _FENCE_RE.search(cleaned)
    if fenced:
        return fenced.group(1).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1]

    return cleaned


def parse_model(model_cls: type[T], text: str) -> T:
    payload = extract_json_text(text)
    return model_cls.model_validate_json(payload)


def generate_model(
    llm,
    model_cls: type[T],
    prompt: str,
    *,
    temperature: float = 0.0,
    max_tokens: int = 700,
) -> T:
    """
    Generate a response and parse it as a Pydantic model.

    Retries once if the first response is not valid JSON for the model.
    """

    last_error: Exception | None = None

    for attempt in range(2):
        retry_prompt = prompt
        if attempt == 1 and last_error is not None:
            retry_prompt = (
                prompt
                + "\n\nYour previous answer was not valid JSON. "
                "Return ONLY valid JSON. No markdown. No extra text."
            )

        log.info(
            "Parse %s attempt=%s tokens=%s",
            model_cls.__name__,
            attempt + 1,
            max_tokens,
        )
        response = llm.generate(
            prompt=retry_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        try:
            parsed = parse_model(model_cls, response)
        except (ValidationError, ValueError) as exc:
            last_error = exc
            log.warning(
                "Parse %s failed attempt=%s: %s",
                model_cls.__name__,
                attempt + 1,
                exc,
            )
            continue
        log.info("Parse %s ok", model_cls.__name__)
        return parsed

    raise ValueError(
        f"LLM did not return valid {model_cls.__name__} JSON: {last_error}"
    )
