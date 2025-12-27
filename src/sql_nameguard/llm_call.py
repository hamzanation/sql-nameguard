from .llm_request import LLMRequest
import requests
from typing import Callable, Dict

ProviderFunc = Callable[[LLMRequest, str], str]
PROVIDER_REGISTRY: Dict[str, ProviderFunc] = {}

def register_provider(name: str):
    def decorator(func: ProviderFunc) -> ProviderFunc:
        PROVIDER_REGISTRY[name] = func
        return func
    return decorator

@register_provider("openai")
def call_openai(req: LLMRequest, api_key: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": req.model,
        "messages": req.messages_as_json(),
        # "max_tokens": req.max_tokens,
        "max_completion_tokens": req.max_tokens,
        "temperature": req.temperature,
    }

    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30,
    )

    # Always surface the response text on errors
    if not r.ok:
        try:
            err = r.json()
        except Exception:
            err = r.text
        raise RuntimeError(f"OpenAI HTTP {r.status_code} error:\n{err}")

    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

@register_provider("anthropic")
def call_anthropic(req: LLMRequest, api_key: str) -> str:
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    system_prompt = None
    messages = []

    for m in req.messages:
        if m.role == "system":
            system_prompt = m.parts[0].text 
        else:
            messages.append({
                "role": m.role,
                "content": m.parts[0].text
            })

    payload = {
        "model": req.model,
        "messages": messages,
        "max_tokens": req.max_tokens,
        "temperature": req.temperature,
    }

    if system_prompt:
        payload["system"] = system_prompt

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=payload,
        timeout=30,
    )

    # Always surface the response text on errors
    if not r.ok:
        try:
            err = r.json()
        except Exception:
            err = r.text
        raise RuntimeError(f"Anthropic HTTP {r.status_code} error:\n{err}")
    
    r.raise_for_status()
    return r.json()["content"][0]["text"]

@register_provider("google")
def call_gemini(req: LLMRequest, api_key: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/{req.model}:generateContent"
        f"?key={api_key}"
    )

    contents = []
    for m in req.messages:
        contents.append({
            "role": "user" if m.role != "assistant" else "model",
            "parts": [{"text": m.parts[0].text}],
        })

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": req.temperature,
            "maxOutputTokens": req.max_tokens,
        },
    }

    r = requests.post(url, json=payload, timeout=30)


    # Always surface the response text on errors
    if not r.ok:
        try:
            err = r.json()
        except Exception:
            err = r.text
        raise RuntimeError(f"Google HTTP {r.status_code} error:\n{err}")
    
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]

def call_llm(provider: str, req: LLMRequest, api_key: str) -> str:
    try:
        fn = PROVIDER_REGISTRY[provider]
    except KeyError:
        raise ValueError(f"Unknown provider: {provider}")
    return fn(req, api_key)
