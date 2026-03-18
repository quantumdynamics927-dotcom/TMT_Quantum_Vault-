# pyright: reportMissingImports=false

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

OLLAMA_BASE = "http://localhost:11434"


@dataclass(frozen=True)
class OllamaResponse:
    model: str
    response: str
    done: bool
    total_duration_ns: int = 0
    returncode: int = 0


def run(
    model: str,
    prompt: str,
    system: str = "",
    timeout: int = 120,
    num_predict: int = 512,
    temperature: float = 0.7,
    base_url: str = OLLAMA_BASE,
    headers: dict[str, str] | None = None,
) -> OllamaResponse:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": num_predict,
            "temperature": temperature,
        },
    }
    if system:
        payload["system"] = system

    response = requests.post(
        f"{base_url.rstrip('/')}/api/generate",
        json=payload,
        headers=headers,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    return OllamaResponse(
        model=model,
        response=data.get("response", "").strip(),
        done=data.get("done", False),
        total_duration_ns=data.get("total_duration", 0),
    )


def list_models() -> list[str]:
    response = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=10)
    response.raise_for_status()
    payload = response.json()
    return [model["name"] for model in payload.get("models", [])]


def extract_error_message(response: requests.Response) -> str:
    try:
        payload: Any = response.json()
    except ValueError:
        return response.text.strip() or f"HTTP {response.status_code}"

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, str) and error.strip():
            return error.strip()
    return response.text.strip() or f"HTTP {response.status_code}"


def is_available() -> bool:
    try:
        requests.get(f"{OLLAMA_BASE}/api/tags", timeout=3)
        return True
    except requests.RequestException:
        return False
