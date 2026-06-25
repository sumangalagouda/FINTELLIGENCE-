import os
import requests

def call_ollama(system_prompt: str, user_prompt: str, max_tokens: int = 2048) -> str:
    """
    Calls the local Ollama API to generate a response.
    """
    url = os.environ.get("OLLAMA_API_URL", "http://localhost:11434/api/chat")
    model = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": float(os.environ.get("AI_TEMPERATURE", 0.1)),
            "num_predict": max_tokens
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=120.0)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")
    except Exception as exc:
        raise RuntimeError(f"AI request failed (ollama): {exc}") from exc
