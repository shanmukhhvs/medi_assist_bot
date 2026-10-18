import requests
from app.config import settings

ONEMIN_URL = "https://api.1min.ai/api/chat-with-ai"
LLM_TIMEOUT_SECONDS = 60


class LLMUnavailableError(RuntimeError):
    """No cloud LLM provider is configured, or every configured provider failed."""


def _call_1min(prompt: str, system_instruction: str) -> str:
    full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
    resp = requests.post(
        ONEMIN_URL,
        headers={"API-KEY": settings.ONEMIN_API_KEY, "Content-Type": "application/json"},
        json={
            "type": "UNIFY_CHAT_WITH_AI",
            "model": settings.ONEMIN_MODEL,
            "promptObject": {"prompt": full_prompt},
        },
        timeout=LLM_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    return resp.json()["aiRecord"]["aiRecordDetail"]["resultObject"][0]


def _call_gemini(prompt: str, system_instruction: str) -> str:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=system_instruction or None, temperature=0.1),
    )
    return response.text or ""


def _call_openai(prompt: str, system_instruction: str) -> str:
    import openai
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY, timeout=LLM_TIMEOUT_SECONDS)
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(model=settings.OPENAI_MODEL, messages=messages, temperature=0.1)
    return response.choices[0].message.content or ""


def call_llm(prompt: str, system_instruction: str = "") -> str:
    """
    Call the first configured cloud LLM provider (1min.ai -> Gemini -> OpenAI), moving to the next on failure.
    Raises LLMUnavailableError when none is configured or all fail; there is no offline/canned answer.
    """
    providers = [
        ("1min.ai", settings.ONEMIN_API_KEY, _call_1min),
        ("Gemini", settings.GOOGLE_API_KEY, _call_gemini),
        ("OpenAI", settings.OPENAI_API_KEY, _call_openai),
    ]
    configured = [(name, fn) for name, key, fn in providers if key]
    if not configured:
        raise LLMUnavailableError(
            "No LLM provider is configured. Set ONEMIN_API_KEY, GOOGLE_API_KEY or OPENAI_API_KEY in backend/.env."
        )

    # Full exception text is logged server-side only; the client sees provider names and error types.
    failures = []
    for name, fn in configured:
        try:
            text = fn(prompt, system_instruction).strip()
            if text:
                return text
            failures.append(f"{name}: empty response")
            print(f"[LLM] {name} returned an empty response")
        except Exception as e:
            failures.append(f"{name}: {type(e).__name__}")
            print(f"[LLM] {name} call failed: {type(e).__name__}: {e}")

    raise LLMUnavailableError("The LLM service is unavailable (" + "; ".join(failures) + "). Please try again later.")
