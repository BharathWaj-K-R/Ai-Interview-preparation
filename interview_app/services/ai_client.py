import json
import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

try:
    import anthropic
except ModuleNotFoundError:
    anthropic = None


class AIClientError(RuntimeError):
    """Raised when the LLM client cannot complete or parse a request."""


class AnthropicAIClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 1200,
    ) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.max_tokens = max_tokens

    @property
    def available(self) -> bool:
        return bool(self.api_key and anthropic)

    def complete_text(self, prompt: str, system: str = "") -> str:
        if not self.api_key:
            raise AIClientError("ANTHROPIC_API_KEY is not configured.")
        if anthropic is None:
            raise AIClientError("anthropic package is not installed.")

        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        parts: List[str] = []
        for block in getattr(response, "content", []):
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        if not parts:
            raise AIClientError("Anthropic returned an empty response.")
        return "\n".join(parts).strip()


def extract_json_payload(raw_text: str) -> Any:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("json").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start_candidates = [idx for idx in (cleaned.find("["), cleaned.find("{")) if idx != -1]
    if not start_candidates:
        raise AIClientError("No JSON payload found in LLM response.")

    start = min(start_candidates)
    end = max(cleaned.rfind("]"), cleaned.rfind("}"))
    if end <= start:
        raise AIClientError("Malformed JSON payload in LLM response.")

    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise AIClientError("Could not parse JSON payload from LLM response.") from exc


def coerce_score(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(100.0, number))


def require_keys(payload: Dict[str, Any], keys: List[str]) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise AIClientError(f"LLM response missing required keys: {', '.join(missing)}")
