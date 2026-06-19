import os
from dotenv import load_dotenv

# Ensure .env variables are loaded regardless of the Flask entrypoint.
load_dotenv()

# Prefer httpx if available, fall back to requests for HTTP provider shim
try:
    import httpx as _httpx
except Exception:  # pragma: no cover - best-effort import
    _httpx = None
    try:
        import requests as _requests
    except Exception:
        _requests = None

# Try to import Groq SDK if present. Keep compatibility with existing code.
_groq_client = None
try:
    from groq import Groq as _Groq
    try:
        _groq_client = _Groq(api_key=os.environ.get("GROQ_API_KEY")) if os.environ.get("GROQ_API_KEY") else None
    except Exception as e:  # pragma: no cover - runtime environment dependent
        print(f"Failed to initialize Groq client: {e}")
        _groq_client = None
except Exception:
    _Groq = None
    _groq_client = None


def _call_groq_via_groq(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
    if not _groq_client:
        raise RuntimeError("Groq client not configured. Set GROQ_API_KEY or choose another AI_PROVIDER.")
    try:
        response = _groq_client.chat.completions.create(
            model=os.environ.get("GROQ_MODEL", "llama3-70b-8192"),
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            max_tokens=max_tokens,
            temperature=0.1,
        )
        # Keep compatible with Groq/Chat response shape
        return getattr(response.choices[0].message, "content", response.choices[0].message)
    except Exception as exc:
        raise RuntimeError(f"AI request failed (groq): {exc}") from exc


def _call_cerebras_via_http(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
    key = os.environ.get("CEREBRAS_API_KEY")
    url = os.environ.get("CEREBRAS_API_URL")
    model = os.environ.get("CEREBRAS_MODEL") or os.environ.get("GROQ_MODEL") or "default"
    if not key or not url:
        raise RuntimeError("Cerebras configuration missing: set CEREBRAS_API_KEY and CEREBRAS_API_URL in your environment.")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": float(os.environ.get("AI_TEMPERATURE", 0.1)),
    }

    # Use httpx if available for async-friendly behavior, otherwise requests
    try:
        if _httpx is not None:
            resp = _httpx.post(url, json=payload, headers={"Authorization": f"Bearer {key}"}, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
        elif _requests is not None:
            resp = _requests.post(url, json=payload, headers={"Authorization": f"Bearer {key}"}, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
        else:
            raise RuntimeError("No HTTP client available (install httpx or requests)")
    except Exception as exc:
        raise RuntimeError(f"AI request failed (cerebras http): {exc}") from exc

    # Try common response shapes: choices[].message.content or output_text
    try:
        choices = data.get("choices")
        if choices and len(choices) > 0:
            msg = choices[0].get("message") or choices[0]
            if isinstance(msg, dict):
                return msg.get("content") or msg.get("text") or str(msg)
            return str(msg)
    except Exception:
        pass

    # Fallback - try top-level text fields
    return data.get("text") or data.get("output") or data.get("result") or str(data)


def call_groq(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
    """Provider-agnostic AI call. Selects provider based on `AI_PROVIDER` or available env vars.

    Supported flows:
    - AI_PROVIDER=cerebras and CEREBRAS_API_KEY/CEREBRAS_API_URL present -> Cerebras HTTP path
    - GROQ_API_KEY present and Groq SDK importable -> Groq SDK path
    """
    provider = os.environ.get("AI_PROVIDER", "").strip().lower()

    # Prefer Groq SDK when a GROQ_API_KEY is present and the SDK initialized successfully.
    if os.environ.get("GROQ_API_KEY") and _groq_client is not None:
        return _call_groq_via_groq(system_prompt, user_prompt, max_tokens=max_tokens)

    # Next, allow explicit Cerebras selection or auto-detect via CEREBRAS env vars.
    if provider == "cerebras" or (os.environ.get("CEREBRAS_API_KEY") and os.environ.get("CEREBRAS_API_URL")):
        return _call_cerebras_via_http(system_prompt, user_prompt, max_tokens=max_tokens)

    # Finally, if Groq SDK is available, use it as a fallback.
    if _groq_client is not None and (_Groq is not None):
        return _call_groq_via_groq(system_prompt, user_prompt, max_tokens=max_tokens)

    raise RuntimeError("No AI provider configured. Set GROQ_API_KEY for Groq or set AI_PROVIDER=cerebras with CEREBRAS_API_KEY and CEREBRAS_API_URL.")
