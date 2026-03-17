# pyright: reportMissingImports=false

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

import requests

from .ollama_api import run as ollama_run
from .models import RuntimeConfig


@dataclass(frozen=True)
class RunResult:
    backend: str
    mode: str
    model: str
    command: list[str] | str
    returncode: int
    stdout: str
    stderr: str
    duration_ms: int = 0


class RuntimeRunner:
    def __init__(self, root: Path, runtime_config: RuntimeConfig) -> None:
        self.root = root.resolve()
        self.runtime_config = runtime_config

    def run(
        self,
        prompt: str,
        backend: str | None = None,
        mode: str | None = None,
        model: str | None = None,
        system: str | None = None,
        timeout: int = 120,
    ) -> RunResult:
        selected_backend = self._resolve_backend(backend)
        if selected_backend == "ollama":
            return self._run_ollama(
                prompt=prompt,
                mode=mode,
                model=model,
                system=system,
                timeout=timeout,
            )
        raise ValueError(
            "The configured backend is llama.cpp, but only Ollama execution "
            "is currently supported by the run command."
        )

    def _run_ollama(
        self,
        prompt: str,
        mode: str | None,
        model: str | None,
        system: str | None,
        timeout: int,
    ) -> RunResult:
        selected_mode = self._resolve_mode(mode)
        selected_model = model or self._default_ollama_model(selected_mode)
        merged_system = (
            system or self.runtime_config.ollama.prompt_prefix or ""
        )

        if selected_mode == "cloud":
            if not self._is_cloud_model(selected_model):
                return RunResult(
                    backend="ollama",
                    mode=selected_mode,
                    model=selected_model,
                    command="ollama run",
                    returncode=1,
                    stdout="",
                    stderr=(
                        "Cloud mode requires an explicit cloud model tag. "
                        "Use a tag such as qwen3.5:397b-cloud or "
                        "qwen3-coder-next:cloud."
                    ),
                    duration_ms=0,
                )
            return self._run_ollama_cloud(
                model=selected_model,
                prompt=prompt,
                system=merged_system,
                timeout=timeout,
            )

        try:
            response = ollama_run(
                model=selected_model,
                prompt=prompt,
                system=merged_system,
                timeout=timeout,
                temperature=0.0,
            )
            return RunResult(
                backend="ollama",
                mode=selected_mode,
                model=selected_model,
                command="ollama HTTP API",
                returncode=response.returncode,
                stdout=self._clean_output(response.response),
                stderr="",
                duration_ms=response.total_duration_ns // 1_000_000,
            )
        except requests.RequestException as exc:
            return RunResult(
                backend="ollama",
                mode=selected_mode,
                model=selected_model,
                command="ollama HTTP API",
                returncode=1,
                stdout="",
                stderr=self._clean_output(str(exc)),
                duration_ms=0,
            )

    def _run_ollama_cloud(
        self,
        *,
        model: str,
        prompt: str,
        system: str,
        timeout: int,
    ) -> RunResult:
        full_prompt = self._merge_prompt(system=system, prompt=prompt)
        command = ["ollama", "run", model, full_prompt]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=self.root,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return RunResult(
                backend="ollama",
                mode="cloud",
                model=model,
                command=command,
                returncode=1,
                stdout="",
                stderr="Cloud model invocation timed out.",
                duration_ms=0,
            )
        except OSError as exc:
            return RunResult(
                backend="ollama",
                mode="cloud",
                model=model,
                command=command,
                returncode=1,
                stdout="",
                stderr=self._clean_output(str(exc)),
                duration_ms=0,
            )

        return RunResult(
            backend="ollama",
            mode="cloud",
            model=model,
            command=command,
            returncode=completed.returncode,
            stdout=self._clean_output(completed.stdout),
            stderr=self._clean_output(completed.stderr),
            duration_ms=0,
        )

    def _resolve_backend(
        self,
        backend: str | None,
    ) -> Literal["ollama", "llama.cpp"]:
        selected_backend = backend or self.runtime_config.preferred_backend
        if selected_backend not in {"ollama", "llama.cpp"}:
            raise ValueError(
                "Unsupported backend. Expected one of: ollama, llama.cpp."
            )
        return cast(Literal["ollama", "llama.cpp"], selected_backend)

    def _resolve_mode(self, mode: str | None) -> Literal["local", "cloud"]:
        selected_mode = mode or self.runtime_config.ollama.mode
        if selected_mode not in {"local", "cloud"}:
            raise ValueError(
                "Unsupported Ollama mode. Expected one of: local, cloud."
            )
        return cast(Literal["local", "cloud"], selected_mode)

    def _default_ollama_model(self, mode: Literal["local", "cloud"]) -> str:
        if mode == "cloud":
            return self.runtime_config.ollama.cloud_model
        return self.runtime_config.ollama.local_model

    def _is_cloud_model(self, model: str) -> bool:
        lowered = model.casefold()
        return lowered.endswith(":cloud") or lowered.endswith("-cloud")

    def _merge_prompt(self, *, system: str, prompt: str) -> str:
        if not system:
            return prompt
        return f"System instructions:\n{system}\n\nUser task:\n{prompt}"

    def _clean_output(self, value: str | None) -> str:
        if value is None:
            return ""
        stripped = value.strip()
        if not stripped:
            return ""
        ansi_pattern = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
        cursor_pattern = re.compile(r"[\u0080-\u00ff]+")
        cleaned = ansi_pattern.sub("", stripped)
        cleaned = cursor_pattern.sub("", cleaned)
        cleaned = re.sub(r"[^\x09\x0A\x0D\x20-\x7E]", "", cleaned)
        return cleaned.strip()
