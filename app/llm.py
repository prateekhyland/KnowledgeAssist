"""Thin client for a local Ollama server."""
from __future__ import annotations

from typing import Iterator

import requests

from .config import get_settings


def chat(messages: list[dict], stream: bool = False) -> str:
    """Send a chat completion request to Ollama and return the full text."""
    settings = get_settings()
    resp = requests.post(
        f"{settings.ollama_base_url}/api/chat",
        json={
            "model": settings.llm_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": settings.llm_temperature,
                "num_ctx": settings.llm_num_ctx,
            },
        },
        timeout=300,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("message", {}).get("content", "")


def chat_stream(messages: list[dict]) -> Iterator[str]:
    """Stream a chat completion from Ollama, yielding content deltas."""
    import json

    settings = get_settings()
    with requests.post(
        f"{settings.ollama_base_url}/api/chat",
        json={
            "model": settings.llm_model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": settings.llm_temperature,
                "num_ctx": settings.llm_num_ctx,
            },
        },
        stream=True,
        timeout=300,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            token = chunk.get("message", {}).get("content", "")
            if token:
                yield token
            if chunk.get("done"):
                break


def health() -> bool:
    """Return True if the Ollama server is reachable."""
    settings = get_settings()
    try:
        r = requests.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
        return r.status_code == 200
    except requests.RequestException:
        return False
