from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from pydantic import ValidationError

from .models import (
    AgentDNA,
    AgentMemory,
    EvalDataset,
    GeometryConfig,
    OptimizationEntry,
    SummarySnapshot,
    ValidationResult,
    VaultConfig,
)


class VaultRepository:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _load_json(self, path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    def resolve_path(self, value: str | None) -> Path | None:
        if not value:
            return None
        candidate = Path(value)
        if candidate.is_absolute():
            return candidate
        return (self.root / candidate).resolve()

    def load_json_document(self, path: Path) -> Any:
        return self._load_json(path)

    def load_eval_dataset(self, path: Path) -> EvalDataset:
        payload = self._load_json(path)
        return EvalDataset.model_validate(payload)

    def load_vault_config(self) -> VaultConfig:
        payload = self._load_json(self.root / "vault_config.json")
        return VaultConfig.model_validate(payload)

    def load_geometry(self) -> GeometryConfig:
        payload = self._load_json(self.root / "metatron_geometry.json")
        return GeometryConfig.model_validate(payload)

    def load_optimization_log(self) -> list[OptimizationEntry]:
        entries = self._load_json(self.root / "optimization_log.json")
        return [OptimizationEntry.model_validate(entry) for entry in entries]

    def load_agents(self) -> list[tuple[Path, AgentDNA]]:
        agents: list[tuple[Path, AgentDNA]] = []
        for path in sorted(self.root.glob("Agent_*/conscious_dna.json")):
            payload = self._load_json(path)
            agents.append((path, AgentDNA.model_validate(payload)))
        return agents

    def load_memories(self) -> list[tuple[Path, AgentMemory]]:
        memories: list[tuple[Path, AgentMemory]] = []
        for path in sorted(self.root.glob("*/*_memory.json")):
            payload = self._load_json(path)
            memories.append((path, AgentMemory.model_validate(payload)))
        return memories

    def model_files(self) -> list[Path]:
        return sorted((self.root / "Models").glob("*.gguf"))

    def daily_logs(self) -> list[Path]:
        return sorted((self.root / "Resonance_Logs" / "daily").glob("*.json"))

    def build_summary(self) -> SummarySnapshot:
        vault = self.load_vault_config()
        geometry = self.load_geometry()
        agents = [agent for _, agent in self.load_agents()]
        memories = [memory for _, memory in self.load_memories()]
        optimizations = self.load_optimization_log()
        latest_optimization = max(
            optimizations,
            key=lambda entry: entry.data.timestamp,
            default=None,
        )
        top_agent = max(agents, key=lambda agent: agent.fitness, default=None)
        integrated_agents = sum(
            agent.consciousness_status == "INTEGRATED"
            for agent in agents
        )
        average_fitness = (
            mean(agent.fitness for agent in agents)
            if agents
            else 0.0
        )
        average_resonance_frequency = (
            mean(agent.resonance_frequency for agent in agents)
            if agents
            else 0.0
        )

        return {
            "vault_name": vault.vault_name,
            "consciousness_level": geometry.consciousness_level,
            "fibonacci_sync": vault.fibonacci_sync,
            "agent_count": len(agents),
            "integrated_agents": integrated_agents,
            "average_fitness": average_fitness,
            "average_resonance_frequency": average_resonance_frequency,
            "top_agent": top_agent,
            "memory_store_count": len(memories),
            "daily_log_count": len(self.daily_logs()),
            "model_files": self.model_files(),
            "latest_optimization": latest_optimization,
        }

    def repository_checks(self) -> list[tuple[str, str]]:
        checks: list[tuple[str, str]] = []
        vault = self.load_vault_config()
        agents = self.load_agents()
        models = self.model_files()

        missing_directories = [
            directory_name
            for directory_name in vault.structure
            if not (self.root / directory_name).exists()
        ]
        if missing_directories:
            missing_directory_message = ", ".join(missing_directories)
            checks.append(
                (
                    "warning",
                    "Configured directories missing from workspace: "
                    + missing_directory_message,
                )
            )

        if len(agents) != 12:
            checks.append(
                (
                    "warning",
                    f"Expected 12 agent DNA files, found {len(agents)}.",
                )
            )
        else:
            checks.append(("ok", "Detected 12 agent DNA files."))

        if models:
            checks.append(
                ("ok", f"Detected {len(models)} model file(s) in Models/.")
            )
        else:
            checks.append(("warning", "No GGUF model found in Models/."))

        if (self.root / ".venv").exists():
            checks.append(
                ("ok", "Local virtual environment .venv is present.")
            )
        else:
            checks.append(
                ("warning", "Local virtual environment .venv is missing.")
            )

        return checks

    def find_agent(self, name: str) -> tuple[Path, AgentDNA] | None:
        needle = name.casefold()
        for path, agent in self.load_agents():
            if needle in {
                agent.metatron_agent.casefold(),
                agent.dna_agent_name.casefold(),
            }:
                return path, agent
        return None

    def validate_repository(self) -> list[ValidationResult]:
        validations: list[ValidationResult] = []
        validations.append(
            self._validate_file(self.root / "vault_config.json", VaultConfig)
        )
        validations.append(
            self._validate_file(
                self.root / "metatron_geometry.json",
                GeometryConfig,
            )
        )
        validations.append(self._validate_optimization_log())

        for path in sorted(self.root.glob("Agent_*/conscious_dna.json")):
            validations.append(self._validate_file(path, AgentDNA))

        for path in sorted(self.root.glob("*/*_memory.json")):
            validations.append(self._validate_file(path, AgentMemory))

        return validations

    def _validate_optimization_log(self) -> ValidationResult:
        path = self.root / "optimization_log.json"
        if not path.exists():
            return ValidationResult(
                path=str(path.relative_to(self.root)),
                model_name="OptimizationEntry[]",
                valid=False,
                error="File not found",
            )

        try:
            payload = self._load_json(path)
            for item in payload:
                OptimizationEntry.model_validate(item)
            return ValidationResult(
                path=str(path.relative_to(self.root)),
                model_name="OptimizationEntry[]",
                valid=True,
            )
        except (ValidationError, ValueError, TypeError) as exc:
            return ValidationResult(
                path=str(path.relative_to(self.root)),
                model_name="OptimizationEntry[]",
                valid=False,
                error=str(exc),
            )

    def _validate_file(
        self,
        path: Path,
        schema: (
            type[VaultConfig]
            | type[GeometryConfig]
            | type[AgentDNA]
            | type[AgentMemory]
        ),
    ) -> ValidationResult:
        if not path.exists():
            return ValidationResult(
                path=str(path.relative_to(self.root)),
                model_name=schema.__name__,
                valid=False,
                error="File not found",
            )

        try:
            schema.model_validate(self._load_json(path))
            return ValidationResult(
                path=str(path.relative_to(self.root)),
                model_name=schema.__name__,
                valid=True,
            )
        except (ValidationError, ValueError, TypeError) as exc:
            return ValidationResult(
                path=str(path.relative_to(self.root)),
                model_name=schema.__name__,
                valid=False,
                error=str(exc),
            )
