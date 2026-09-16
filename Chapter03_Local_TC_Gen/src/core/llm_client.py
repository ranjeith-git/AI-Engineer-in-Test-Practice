"""LLM client with Ollama-primary / GROQ-fallback routing.

Strategy:
1. Try local Ollama (gemma3:1b by default).
2. If it is unreachable, times out, or returns output that fails structural
   validation against the template, retry once via GROQ.
3. Never log request bodies or credentials — only engine, latency, outcome.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import requests

from .config import Settings
from .logger import get_logger
from .output_validator import ValidationResult, validate
from .template_loader import TemplateFile

log = get_logger()

OLLAMA_CHAT_URL = "/api/chat"
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

# Long timeout: a 1B local model can be slow on CPU, and GROQ is remote.
_HTTP_TIMEOUT = 300
# Give up waiting for Ollama health / generation fast when it is not running.
_OLLAMA_CONNECT_TIMEOUT = 8


class EngineError(Exception):
    """Raised when an LLM engine fails (connectivity, timeout, API error)."""


@dataclass
class GenerationResult:
    engine: str  # "ollama" | "groq"
    model: str
    text: str
    validation: ValidationResult
    latency_s: float


def _ollama_messages(system: str, user: str) -> dict:
    return {
        "model": "",  # filled per call
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": 0.2},
    }


def ollama_generate(settings: Settings, system: str, user: str) -> str:
    """Call Ollama /api/chat. Raises EngineError on any failure."""
    url = settings.ollama_base_url.rstrip("/") + OLLAMA_CHAT_URL
    payload = _ollama_messages(system, user)
    payload["model"] = settings.ollama_model

    started = time.time()
    try:
        resp = requests.post(
            url,
            json=payload,
            timeout=(_OLLAMA_CONNECT_TIMEOUT, _HTTP_TIMEOUT),
        )
    except requests.exceptions.ConnectTimeout:
        log.info("ollama connect timeout after %ss", _OLLAMA_CONNECT_TIMEOUT)
        raise EngineError(
            f"Ollama at {settings.ollama_base_url} did not respond within "
            f"{_OLLAMA_CONNECT_TIMEOUT}s. Is the Ollama server running?"
        ) from None
    except requests.exceptions.RequestException as exc:
        log.info("ollama request failed: %s", type(exc).__name__)
        raise EngineError(
            f"Could not reach Ollama at {settings.ollama_base_url}. "
            f"Is the server running? (start it with: ollama serve)"
        ) from None

    latency = time.time() - started
    if resp.status_code >= 400:
        log.info("ollama HTTP error: %s", resp.status_code)
        raise EngineError(
            f"Ollama returned HTTP {resp.status_code}: {resp.text[:200]}"
        )

    try:
        data = resp.json()
        text = (data.get("message") or {}).get("content", "").strip()
    except (ValueError, AttributeError):
        log.info("ollama returned non-JSON response")
        raise EngineError("Ollama returned an unparseable response.") from None

    if not text:
        raise EngineError("Ollama returned an empty response.")
    log.info("ollama ok (model=%s, latency=%.1fs, chars=%d)",
             settings.ollama_model, latency, len(text))
    return text


def groq_generate(settings: Settings, system: str, user: str) -> str:
    """Call GROQ chat completions. Raises EngineError on any failure."""
    if not settings.is_groq_configured():
        raise EngineError("GROQ API key is not configured in Settings.")

    started = time.time()
    try:
        resp = requests.post(
            GROQ_CHAT_URL,
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.groq_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
                # A large output cap is required: gpt-oss is a reasoning model
                # whose default budget can be consumed entirely by hidden
                # chain-of-thought, leaving content empty. 16000 reserves room
                # for the generated table.
                "max_tokens": 16000,
            },
            timeout=_HTTP_TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        log.info("groq request failed: %s", type(exc).__name__)
        raise EngineError("Could not reach the GROQ API. Check your network.") from None

    latency = time.time() - started
    if resp.status_code in (401, 403):
        log.info("groq auth failed: HTTP %s", resp.status_code)
        raise EngineError("GROQ authentication failed. Check the API key in Settings.")
    if resp.status_code >= 400:
        log.info("groq HTTP error: %s", resp.status_code)
        raise EngineError(
            f"GROQ returned HTTP {resp.status_code}: {resp.text[:200]}"
        )

    try:
        data = resp.json()
        text = data["choices"][0]["message"]["content"].strip()
    except (ValueError, KeyError, IndexError, TypeError):
        log.info("groq returned unparseable response")
        raise EngineError("GROQ returned an unparseable response.") from None

    if not text:
        raise EngineError("GROQ returned an empty response.")
    log.info("groq ok (model=%s, latency=%.1fs, chars=%d)",
             settings.groq_model, latency, len(text))
    return text


def generate(
    settings: Settings,
    system: str,
    user: str,
    template: TemplateFile,
    force_groq: bool = False,
) -> GenerationResult:
    """Generate, preferring Ollama, falling back to GROQ on failure/mismatch."""
    start = time.time()

    if settings.force_groq or force_groq:
        # Bypass Ollama entirely (Settings has a "force fallback" toggle).
        text = groq_generate(settings, system, user)
        validation = validate(text, template)
        return GenerationResult(
            engine="groq", model=settings.groq_model, text=text,
            validation=validation, latency_s=time.time() - start,
        )

    try:
        text = ollama_generate(settings, system, user)
    except EngineError as exc:
        log.info("ollama failed, falling back to groq: %s", exc)
        return _groq_fallback(settings, system, user, template, start)

    validation = validate(text, template)
    if validation.valid:
        return GenerationResult(
            engine="ollama", model=settings.ollama_model, text=text,
            validation=validation, latency_s=time.time() - start,
        )

    # Ollama responded but output does not match the template structure.
    log.info("ollama output failed validation (%d issues); falling back to groq",
             len(validation.reasons))
    if not settings.is_groq_configured():
        log.info("no groq key configured — returning flagged ollama output")
        return GenerationResult(
            engine="ollama", model=settings.ollama_model, text=text,
            validation=validation, latency_s=time.time() - start,
        )
    return _groq_fallback(settings, system, user, template, start)


def _groq_fallback(settings: Settings, system: str, user: str,
                   template: TemplateFile, start: float) -> GenerationResult:
    try:
        text = groq_generate(settings, system, user)
    except EngineError as exc:
        raise EngineError(f"Both LLM engines failed. Last error (GROQ): {exc}") from exc

    validation = validate(text, template)
    return GenerationResult(
        engine="groq", model=settings.groq_model, text=text,
        validation=validation, latency_s=time.time() - start,
    )
