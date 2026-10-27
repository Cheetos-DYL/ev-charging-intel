"""DeepSeek chat helper (OpenAI-compatible REST over httpx) + strict JSON parsing."""
import json
import os

import httpx

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL


def chat(messages: list[dict], model: str, max_tokens: int = 4096, temperature: float = 0.2,
         json_mode: bool = True) -> str:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY not set")
    base = dict(model=model, messages=messages, max_tokens=max_tokens, temperature=temperature)
    # provider JSON-mode quirks vary (Groq+gpt-oss rejects valid JSON) → best-effort,
    # parse_json() is the real safety net
    payloads = [{**base, "response_format": {"type": "json_object"}}] if json_mode else []
    payloads.append(base)
    last_err = None
    for payload in payloads:
        try:
            r = httpx.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                # x-opencode-session: required routing header on opencode.ai/zen (400 MissingSessionID without it)
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                         "x-opencode-session": os.environ.get("OPENCODE_SESSION_ID", "ev-charging-intel")},
                json=payload, timeout=180,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            last_err = e
    raise RuntimeError(f"LLM call failed: {last_err}")


def parse_json(text: str) -> dict:
    """Parse a JSON object from LLM output (fences / prose tolerated)."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1]
        if t.startswith("json"):
            t = t[4:]
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in: {text[:200]}")
    return json.loads(t[start:end + 1])
