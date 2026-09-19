import json
import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

try:
    import anthropic
except ModuleNotFoundError:
    anthropic = None

try:
    from groq import Groq as GroqClient
except ModuleNotFoundError:
    GroqClient = None


class AIClientError(RuntimeError):
    """Raised when the LLM client cannot complete or parse a request."""


class AIClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int = 1200,
        provider: str | None = None,
    ) -> None:
        self.max_tokens = max_tokens

        env_groq_key = os.getenv("GROQ_API_KEY", "")
        env_gemini_key = os.getenv("GEMINI_API_KEY", "")
        env_anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

        detected_provider = None
        if model:
            model_lower = model.lower()
            if "claude" in model_lower:
                detected_provider = "anthropic"
            elif "gemini" in model_lower:
                detected_provider = "gemini"
            elif any(x in model_lower for x in ("llama", "mixtral", "gemma", "groq")):
                detected_provider = "groq"

        if provider:
            self.provider = provider.lower()
        elif detected_provider:
            self.provider = detected_provider
        elif env_groq_key:
            self.provider = "groq"
        elif env_gemini_key:
            self.provider = "gemini"
        elif env_anthropic_key:
            self.provider = "anthropic"
        else:
            self.provider = "groq"

        if self.provider == "gemini":
            self.api_key = api_key or env_gemini_key
            self.model = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        elif self.provider == "groq":
            self.api_key = api_key or env_groq_key
            self.model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        else:
            self.api_key = api_key or env_anthropic_key
            self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    @property
    def available(self) -> bool:
        if self.provider == "gemini":
            return bool(self.api_key)
        elif self.provider == "groq":
            return bool(self.api_key and GroqClient)
        else:
            return bool(self.api_key and anthropic)

    def complete_text(self, prompt: str, system: str = "") -> str:
        if self.provider == "gemini":
            return self._complete_text_gemini(prompt, system)
        elif self.provider == "groq":
            return self._complete_text_groq(prompt, system)
        else:
            return self._complete_text_anthropic(prompt, system)

    def _complete_text_groq(self, prompt: str, system: str = "") -> str:
        if not self.api_key:
            raise AIClientError("GROQ_API_KEY is not configured.")
        if GroqClient is None:
            raise AIClientError("groq package is not installed. Run: pip install groq")

        client = GroqClient(api_key=self.api_key)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
            )
            text = response.choices[0].message.content
            if not text:
                raise AIClientError("Groq returned an empty response.")
            return text.strip()
        except AIClientError:
            raise
        except Exception as exc:
            raise AIClientError(f"Groq API request failed: {exc}") from exc

    def _complete_text_gemini(self, prompt: str, system: str = "") -> str:
        if not self.api_key:
            raise AIClientError("GEMINI_API_KEY is not configured.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}

        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        payload["generationConfig"] = {"maxOutputTokens": self.max_tokens}

        import urllib.request
        import urllib.error

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                candidates = res_data.get("candidates", [])
                if not candidates:
                    raise AIClientError("Gemini returned empty candidates.")
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    raise AIClientError("Gemini returned empty parts in content.")
                text = parts[0].get("text", "")
                if not text:
                    raise AIClientError("Gemini returned an empty response.")
                return text
        except urllib.error.HTTPError as e:
            try:
                error_body = e.read().decode("utf-8")
                logger.error("Gemini HTTP Error body: %s", error_body)
            except Exception:
                error_body = ""
            raise AIClientError(f"Gemini API request failed (HTTP {e.code}): {e.reason}. Detail: {error_body}")
        except AIClientError:
            raise
        except Exception as exc:
            raise AIClientError(f"Gemini API request failed: {exc}") from exc

    def _complete_text_anthropic(self, prompt: str, system: str = "") -> str:
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


AnthropicAIClient = AIClient


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
