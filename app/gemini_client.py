"""Shared helper that talks to Google's Gemini API (google-genai SDK).

If a model is overloaded (503), rate limited (429) or not found (404),
the next model in the fallback list is tried automatically.
"""
import os
import re
import time

from . import config


class GeminiError(RuntimeError):
    """Raised when the Gemini API cannot produce a usable answer."""


# Extra models to try, in order, when the chosen model fails.
# Override in .env with:  GEMINI_FALLBACK_MODELS=model1,model2,model3
DEFAULT_FALLBACKS = "gemini-3.7-flash,gemini-3.6-flash,gemini-3.5-flash,gemini-3.5-flash-lite,gemini-2.5-flash,gemini-2.5-flash-lite"

_client = None


def get_client():
    global _client
    if not config.GOOGLE_API_KEY:
        raise GeminiError(
            "GOOGLE_API_KEY is missing. Create a .env file (see .env.example) and add your Gemini API key."
        )
    if _client is None:
        from google import genai  # imported here so the app can start even without the key

        _client = genai.Client(api_key=config.GOOGLE_API_KEY)
    return _client


def clean_text(text: str) -> str:
    """Remove markdown symbols so the text looks clean inside <pre> blocks."""
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)                  # **bold**
    text = re.sub(r"^[ \t]{0,3}#{1,6}[ \t]*", "", text, flags=re.M)      # # headings
    text = re.sub(r"^[ \t]*[\*\-][ \t]+", "• ", text, flags=re.M)        # bullets
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _model_chain(model: str) -> list:
    raw = os.getenv("GEMINI_FALLBACK_MODELS", DEFAULT_FALLBACKS)
    chain = [model] + [m.strip() for m in raw.split(",") if m.strip()]
    seen, result = set(), []
    for m in chain:  # remove duplicates, keep order
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


def _is_key_problem(message: str) -> bool:
    msg = message.lower()
    return any(s in msg for s in ("api key not valid", "api_key_invalid", "permission_denied", "401", "403"))


def generate_text(model: str, prompt: str) -> str:
    """Call Gemini and return cleaned text, falling back to other models if needed."""
    client = get_client()
    errors = []
    for name in _model_chain(model):
        for attempt in range(2):  # one quick retry per model
            try:
                response = client.models.generate_content(model=name, contents=prompt)
                text = (response.text or "").strip()
                if not text:
                    raise ValueError("empty response")
                return clean_text(text)
            except Exception as exc:
                message = str(exc)
                if _is_key_problem(message):
                    raise GeminiError(f"Your API key was rejected by Google: {message}")
                if attempt == 0:
                    time.sleep(1.5)
                else:
                    errors.append(f"{name}: {message[:120]}")
    raise GeminiError(
        "All Gemini models failed. Please wait a minute and try again. Details: " + " | ".join(errors[-3:])
    )