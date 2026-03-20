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
        return [
            self.inspect_ollama(),
            self.inspect_ollama_cloud(),
            self.inspect_llama_cpp(),
        ]

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
        configured_model_path = self._configured_model_path()
        serialized_artifacts = self._serialized_model_artifacts()
        unsupported_artifacts = self._unsupported_model_artifacts()

        if executable is None and not model_files:
            detail = (
                "No llama.cpp executable detected and no GGUF models "
                "found in Models/."
            )
            if (
                configured_model_path is not None
                and not configured_model_path.exists()
            ):
                detail += (
                    " Configured model path is missing: "
                    f"{configured_model_path.relative_to(self.root)}."
                )
            if serialized_artifacts:
                detail += (
                    " Serialized agent artifact(s) present: "
                    + ", ".join(path.name for path in serialized_artifacts)
                    + "."
                )
            if unsupported_artifacts:
                detail += (
                    " Unsupported artifact(s) present: "
                    + ", ".join(path.name for path in unsupported_artifacts)
                    + "."
                )
            return RuntimeStatus(
                name="llama.cpp",
                status="warning",
                detail=detail,
            )

        if executable is None:
            detail = (
                f"Detected {len(model_files)} GGUF model(s) in Models/, "
                "but no llama.cpp executable was found."
            )
            if (
                configured_model_path is not None
                and not configured_model_path.exists()
            ):
                detail += (
                    " Configured model path is missing: "
                    f"{configured_model_path.relative_to(self.root)}."
                )
            if serialized_artifacts:
                detail += (
                    " Serialized agent artifact(s) present: "
                    + ", ".join(path.name for path in serialized_artifacts)
                    + "."
                )
            return RuntimeStatus(
                name="llama.cpp",
                status="warning",
                detail=detail,
            )

        version = self._command_output([str(executable), "--version"])
        if model_files:
            detail = (
                f"llama.cpp executable found with {len(model_files)} GGUF "
                "model(s) available in Models/."
            )
            if (
                configured_model_path is not None
                and not configured_model_path.exists()
            ):
                detail += (
                    " Configured model path is missing: "
                    f"{configured_model_path.relative_to(self.root)}."
                )
            status = "ok"
        else:
            detail = (
                "llama.cpp executable found, but no GGUF models were found "
                "in Models/."
            )
            if (
                configured_model_path is not None
                and not configured_model_path.exists()
            ):
                detail += (
                    " Configured model path is missing: "
                    f"{configured_model_path.relative_to(self.root)}."
                )
            if serialized_artifacts:
                detail += (
                    " Serialized agent artifact(s) present: "
                    + ", ".join(path.name for path in serialized_artifacts)
                    + "."
                )
            if unsupported_artifacts:
                detail += (
                    " Unsupported artifact(s) present: "
                    + ", ".join(path.name for path in unsupported_artifacts)
                    + "."
                )
            status = "warning"

        return RuntimeStatus(
            name="llama.cpp",
            status=status,
            detail=detail,
            executable=executable,
            version=self._summarize_version("llama.cpp", version),
        )

    def inspect_ollama_cloud(self) -> RuntimeStatus:
        executable = self._which("ollama")
        if executable is None:
            return RuntimeStatus(
                name="Ollama Cloud",
                status="warning",
                detail="Ollama executable not found on PATH.",
            )

        if self.config is None:
            return RuntimeStatus(
                name="Ollama Cloud",
                status="warning",
                detail="Vault runtime configuration is not available.",
                executable=executable,
            )

        cloud_model = self.config.runtime.ollama.cloud_model
        if not self._is_cloud_model_tag(cloud_model):
            return RuntimeStatus(
                name="Ollama Cloud",
                status="warning",
                detail=(
                    "Configured cloud model does not use a cloud tag: "
                    f"{cloud_model}"
                ),
                executable=executable,
            )

        model_list = self._command_output([str(executable), "list"])
        if model_list is None:
            return RuntimeStatus(
                name="Ollama Cloud",
                status="warning",
                detail="Could not read Ollama model inventory.",
                executable=executable,
            )

        visible_models = self._parse_ollama_models(model_list)
        visible_cloud_models = [
            model
            for model in visible_models
            if self._is_cloud_model_tag(model)
        ]
        if cloud_model in visible_cloud_models:
            return RuntimeStatus(
                name="Ollama Cloud",
                status="ok",
                detail=(
                    "Configured cloud model is visible in Ollama inventory: "
                    f"{cloud_model}"
                ),
                executable=executable,
            )

        if visible_cloud_models:
            return RuntimeStatus(
                name="Ollama Cloud",
                status="warning",
                detail=(
                    "Configured cloud model is not visible in Ollama "
                    "inventory. Visible cloud model(s): "
                    + ", ".join(visible_cloud_models)
                ),
                executable=executable,
            )

        return RuntimeStatus(
            name="Ollama Cloud",
            status="warning",
            detail="No cloud-tagged models are visible in Ollama inventory.",
            executable=executable,
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
        configured_path = self._configured_model_path()
        if configured_path is None:
            return model_files
        if configured_path.exists() and configured_path not in model_files:
            model_files.append(configured_path)
        unique_paths = list(dict.fromkeys(sorted(model_files)))
        return unique_paths

    def _configured_model_path(self) -> Path | None:
        if self.config is None:
            return None
        configured_path = Path(self.config.runtime.llama_cpp.model_path)
        if not configured_path.is_absolute():
            configured_path = self.root / configured_path
        return configured_path

    def _unsupported_model_artifacts(self) -> list[Path]:
        models_dir = self.root / "Models"
        if not models_dir.exists():
            return []
        return sorted(
            path
            for path in models_dir.iterdir()
            if path.is_file()
            and path.suffix != ".gguf"
            and path.suffix != ".pkl"
            and not path.name.endswith(".json.gz")
        )

    def _serialized_model_artifacts(self) -> list[Path]:
        models_dir = self.root / "Models"
        if not models_dir.exists():
            return []
        return sorted(
            path
            for path in models_dir.iterdir()
            if path.is_file()
            and (path.suffix == ".pkl" or path.name.endswith(".json.gz"))
        )

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

    def _parse_ollama_models(self, model_list: str) -> list[str]:
        lines = [line for line in model_list.splitlines() if line.strip()]
        if not lines:
            return []
        if lines[0].casefold().startswith("name"):
            lines = lines[1:]
        models: list[str] = []
        for line in lines:
            models.append(line.split()[0])
        return models

    def _is_cloud_model_tag(self, model: str) -> bool:
        lowered = model.casefold()
        return lowered.endswith(":cloud") or lowered.endswith("-cloud")

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
