from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
import re

from .models import VaultConfig


@dataclass(frozen=True)
class RuntimeStatus:
    name: str
    status: str
    detail: str
    executable: Path | None = None
    version: str | None = None


class RuntimeInspector:
    def __init__(self, root: Path, config: VaultConfig | None = None) -> None:
        self.root = root.resolve()
        self.config = config

    def inspect_all(self) -> list[RuntimeStatus]:
        return [self.inspect_ollama(), self.inspect_llama_cpp()]

    def inspect_ollama(self) -> RuntimeStatus:
        executable = self._which("ollama")
        if executable is None:
            return RuntimeStatus(
                name="Ollama",
                status="warning",
                detail="Ollama executable not found on PATH.",
            )

        version = self._command_output([str(executable), "--version"])
        model_list = self._command_output([str(executable), "list"])
        model_count = self._count_ollama_models(model_list)

        if model_count is None:
            detail = (
                "Ollama executable found, but model inventory could not "
                "be read."
            )
        else:
            detail = (
                f"Ollama executable found with {model_count} local "
                "model(s)."
            )

        return RuntimeStatus(
            name="Ollama",
            status="ok",
            detail=detail,
            executable=executable,
            version=self._summarize_version("ollama", version),
        )

    def inspect_llama_cpp(self) -> RuntimeStatus:
        executable = self._find_llama_cpp_executable()
        model_files = self._configured_model_files()

        if executable is None and not model_files:
            return RuntimeStatus(
                name="llama.cpp",
                status="warning",
                detail=(
                    "No llama.cpp executable detected and no GGUF models "
                    "found in Models/."
                ),
            )

        if executable is None:
            return RuntimeStatus(
                name="llama.cpp",
                status="warning",
                detail=(
                    f"Detected {len(model_files)} GGUF model(s) in Models/, "
                    "but no llama.cpp executable was found."
                ),
            )

        version = self._command_output([str(executable), "--version"])
        if model_files:
            detail = (
                f"llama.cpp executable found with {len(model_files)} GGUF "
                "model(s) available in Models/."
            )
            status = "ok"
        else:
            detail = (
                "llama.cpp executable found, but no GGUF models were found "
                "in Models/."
            )
            status = "warning"

        return RuntimeStatus(
            name="llama.cpp",
            status=status,
            detail=detail,
            executable=executable,
            version=self._summarize_version("llama.cpp", version),
        )

    def _find_llama_cpp_executable(self) -> Path | None:
        configured_path = self._configured_llama_cpp_executable()
        if configured_path is not None:
            return configured_path

        candidate_names = [
            "llama-cli",
            "llama-cli.exe",
            "llama-server",
            "llama-server.exe",
            "main.exe",
        ]
        for name in candidate_names:
            path = self._which(name)
            if path is not None:
                return path

        search_roots = [
            self.root,
            self.root / "Models",
            self.root / "bin",
            self.root / "tools",
        ]
        seen: set[Path] = set()
        for base_path in search_roots:
            if not base_path.exists():
                continue
            for pattern in ("llama*.exe", "main.exe", "llama*", "main"):
                for path in base_path.rglob(pattern):
                    if path in seen or not path.is_file():
                        continue
                    seen.add(path)
                    lowered = path.name.casefold()
                    if lowered.startswith("llama") or lowered == "main.exe":
                        return path
        return None

    def _configured_llama_cpp_executable(self) -> Path | None:
        if self.config is None:
            return None
        configured_path = self.config.runtime.llama_cpp.executable_path
        if not configured_path:
            return None
        path = Path(configured_path)
        if not path.is_absolute():
            path = (self.root / path).resolve()
        if path.exists() and path.is_file():
            return path
        return None

    def _configured_model_files(self) -> list[Path]:
        model_files = sorted((self.root / "Models").glob("*.gguf"))
        if self.config is None:
            return model_files

        configured_path = Path(self.config.runtime.llama_cpp.model_path)
        if not configured_path.is_absolute():
            configured_path = self.root / configured_path
        if configured_path.exists() and configured_path not in model_files:
            model_files.append(configured_path)
        unique_paths = list(dict.fromkeys(sorted(model_files)))
        return unique_paths

    def _which(self, command: str) -> Path | None:
        resolved = shutil.which(command)
        return Path(resolved) if resolved is not None else None

    def _command_output(self, args: list[str]) -> str | None:
        try:
            completed = subprocess.run(
                args,
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (FileNotFoundError, OSError, subprocess.SubprocessError):
            return None

        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if stdout:
            return stdout
        if stderr:
            return stderr
        return None

    def _count_ollama_models(self, model_list: str | None) -> int | None:
        if not model_list:
            return None

        lines = [line for line in model_list.splitlines() if line.strip()]
        if not lines:
            return 0
        if lines[0].casefold().startswith("name"):
            return max(len(lines) - 1, 0)
        return len(lines)

    def _summarize_version(
        self,
        runtime_name: str,
        version_output: str | None,
    ) -> str | None:
        if not version_output:
            return None

        if runtime_name == "ollama":
            return version_output.splitlines()[0].strip()

        version_match = re.search(r"version:\s*([^\r\n]+)", version_output)
        build_match = re.search(r"built with\s*([^\r\n]+)", version_output)
        parts: list[str] = []
        if version_match:
            parts.append(version_match.group(1).strip())
        if build_match:
            parts.append(build_match.group(1).strip())
        if parts:
            return " | ".join(parts)
        return version_output.splitlines()[0].strip()
