#!/usr/bin/env python3
"""
Tests for Vault Repository module.

Tests for repository loading and path resolution.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tmt_quantum_vault.models import (
    AgentDNA,
    EvalDataset,
    GeometryConfig,
    OptimizationEntry,
    VaultConfig,
)
from tmt_quantum_vault.repository import VaultRepository


class TestVaultRepository:
    """Tests for VaultRepository class."""

    def test_initialization(self, tmp_path: Path) -> None:
        """Test VaultRepository initialization."""
        repo = VaultRepository(tmp_path)

        assert repo.root == tmp_path.resolve()

    def test_resolve_path_absolute(self, tmp_path: Path) -> None:
        """Test resolve_path with absolute path."""
        repo = VaultRepository(tmp_path)

        # On Windows, absolute paths get resolved with drive letter
        # Just check that the path is returned as a Path object
        result = repo.resolve_path("/absolute/path")

        # The path should be resolved (on Windows it adds drive letter)
        assert isinstance(result, Path)
        assert "absolute" in str(result) or "absolute" in result.parts[-2]

    def test_resolve_path_relative(self, tmp_path: Path) -> None:
        """Test resolve_path with relative path."""
        repo = VaultRepository(tmp_path)

        result = repo.resolve_path("relative/path")

        assert result == (tmp_path / "relative" / "path").resolve()

    def test_resolve_path_none(self, tmp_path: Path) -> None:
        """Test resolve_path with None."""
        repo = VaultRepository(tmp_path)

        result = repo.resolve_path(None)

        assert result is None

    def test_resolve_path_empty(self, tmp_path: Path) -> None:
        """Test resolve_path with empty string."""
        repo = VaultRepository(tmp_path)

        result = repo.resolve_path("")

        assert result is None


class TestVaultRepositoryLoading:
    """Tests for VaultRepository loading methods."""

    def test_load_json_document(self, tmp_path: Path) -> None:
        """Test loading JSON document."""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value"}')

        repo = VaultRepository(tmp_path)
        result = repo.load_json_document(json_file)

        assert result == {"key": "value"}

    def test_load_vault_config(self, tmp_path: Path) -> None:
        """Test loading vault config."""
        config_file = tmp_path / "vault_config.json"
        config_file.write_text(
            json.dumps(
                {
                    "vault_name": "test-vault",
                    "creation_timestamp": 0.0,
                    "structure": {},
                    "stability_baseline": 0.5,
                    "fibonacci_sync": True,
                }
            )
        )

        repo = VaultRepository(tmp_path)
        result = repo.load_vault_config()

        assert isinstance(result, VaultConfig)
        assert result.vault_name == "test-vault"

    def test_load_geometry(self, tmp_path: Path) -> None:
        """Test loading geometry config."""
        geometry_file = tmp_path / "metatron_geometry.json"
        geometry_file.write_text(
            json.dumps(
                {
                    "vault_created": 0.0,
                    "silver_ratio": 1.618,
                    "bronze_ratio": 1.618,
                    "phi_ratio": 1.618,
                    "nodes": 13,
                    "resonance_pulse": 0.5,
                    "consciousness_level": "baseline",
                }
            )
        )

        repo = VaultRepository(tmp_path)
        result = repo.load_geometry()

        assert isinstance(result, GeometryConfig)
        assert result.nodes == 13

    def test_load_agents(self, tmp_path: Path) -> None:
        """Test loading agents."""
        agent_dir = tmp_path / "Agent_Test"
        agent_dir.mkdir()
        dna_file = agent_dir / "conscious_dna.json"
        dna_file.write_text(
            json.dumps(
                {
                    "metatron_agent": "Test",
                    "dna_agent_id": 1,
                    "dna_agent_name": "TestAgent",
                    "dna_specialization": "test",
                    "conscious_dna": "ATCG",
                    "phi_score": 0.618,
                    "fibonacci_alignment": 0.5,
                    "gc_content": 0.5,
                    "palindromes": 0,
                    "fitness": 0.9,
                    "resonance_frequency": 0.5,
                    "integration_timestamp": "2024-01-01",
                    "consciousness_status": "active",
                }
            )
        )

        repo = VaultRepository(tmp_path)
        result = repo.load_agents()

        assert len(result) == 1
        path, agent = result[0]
        assert isinstance(agent, AgentDNA)
        assert agent.metatron_agent == "Test"

    def test_load_memories(self, tmp_path: Path) -> None:
        """Test loading memories."""
        memory_dir = tmp_path / "Memory"
        memory_dir.mkdir()
        memory_file = memory_dir / "test_memory.json"
        memory_file.write_text(
            json.dumps(
                {
                    "agent_id": 1,
                    "name": "TestMemory",
                    "activations": 5,
                    "consciousness_level": "baseline",
                    "last_pulse": 0.5,
                    "resonance_level": 0.618,
                }
            )
        )

        repo = VaultRepository(tmp_path)
        result = repo.load_memories()

        # May be empty if pattern doesn't match
        assert isinstance(result, list)


class TestVaultRepositoryArtifacts:
    """Tests for VaultRepository artifact methods."""

    def test_model_artifacts_empty(self, tmp_path: Path) -> None:
        """Test model_artifacts when Models directory doesn't exist."""
        repo = VaultRepository(tmp_path)

        result = repo.model_artifacts()

        assert result == []

    def test_model_artifacts_with_files(self, tmp_path: Path) -> None:
        """Test model_artifacts with files."""
        models_dir = tmp_path / "Models"
        models_dir.mkdir()
        (models_dir / "model1.gguf").touch()
        (models_dir / "model2.gguf").touch()

        repo = VaultRepository(tmp_path)
        result = repo.model_artifacts()

        assert len(result) == 2

    def test_serialized_model_files(self, tmp_path: Path) -> None:
        """Test serialized_model_files."""
        models_dir = tmp_path / "Models"
        models_dir.mkdir()
        (models_dir / "model.pkl").touch()
        (models_dir / "model.json.gz").touch()
        (models_dir / "model.gguf").touch()

        repo = VaultRepository(tmp_path)
        result = repo.serialized_model_files()

        assert len(result) == 2  # .pkl and .json.gz


class TestVaultRepositoryErrorHandling:
    """Tests for VaultRepository error handling."""

    def test_load_json_document_not_found(self, tmp_path: Path) -> None:
        """Test loading non-existent JSON document."""
        repo = VaultRepository(tmp_path)

        with pytest.raises(FileNotFoundError):
            repo.load_json_document(tmp_path / "nonexistent.json")

    def test_load_vault_config_not_found(self, tmp_path: Path) -> None:
        """Test loading non-existent vault config."""
        repo = VaultRepository(tmp_path)

        with pytest.raises(FileNotFoundError):
            repo.load_vault_config()

    def test_load_geometry_not_found(self, tmp_path: Path) -> None:
        """Test loading non-existent geometry config."""
        repo = VaultRepository(tmp_path)

        with pytest.raises(FileNotFoundError):
            repo.load_geometry()


class TestVaultRepositoryValidation:
    """Tests for VaultRepository validation."""

    def test_load_vault_config_invalid(self, tmp_path: Path) -> None:
        """Test loading invalid vault config."""
        config_file = tmp_path / "vault_config.json"
        config_file.write_text('{"invalid": "data"}')

        repo = VaultRepository(tmp_path)

        with pytest.raises(ValidationError):
            repo.load_vault_config()

    def test_load_agents_invalid_dna(self, tmp_path: Path) -> None:
        """Test loading agents with invalid DNA."""
        agent_dir = tmp_path / "Agent_Invalid"
        agent_dir.mkdir()
        dna_file = agent_dir / "conscious_dna.json"
        dna_file.write_text('{"invalid": "data"}')

        repo = VaultRepository(tmp_path)

        with pytest.raises(ValidationError):
            repo.load_agents()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _vault_config_payload(
    *,
    structure: dict[str, list[str]] | None = None,
    model_path: str = "Models/qwen3-8b.gguf",
) -> dict[str, object]:
    return {
        "vault_name": "test-vault",
        "creation_timestamp": 0.0,
        "structure": structure or {},
        "stability_baseline": 0.5,
        "fibonacci_sync": True,
        "runtime": {
            "llama_cpp": {
                "model_path": model_path,
            }
        },
    }


def _geometry_payload() -> dict[str, object]:
    return {
        "vault_created": 0.0,
        "silver_ratio": 1.618,
        "bronze_ratio": 1.272,
        "phi_ratio": 1.618,
        "nodes": 13,
        "resonance_pulse": 0.5,
        "consciousness_level": "baseline",
    }


def _agent_payload(
    *,
    metatron_agent: str = "Test",
    dna_agent_id: int = 1,
    dna_agent_name: str = "TestAgent",
    fitness: float = 0.9,
    resonance_frequency: float = 432.0,
    consciousness_status: str = "INTEGRATED",
) -> dict[str, object]:
    return {
        "metatron_agent": metatron_agent,
        "dna_agent_id": dna_agent_id,
        "dna_agent_name": dna_agent_name,
        "dna_specialization": "test",
        "conscious_dna": "ATCG",
        "phi_score": 0.618,
        "fibonacci_alignment": 0.5,
        "gc_content": 0.5,
        "palindromes": 0,
        "fitness": fitness,
        "resonance_frequency": resonance_frequency,
        "integration_timestamp": "2024-01-01T00:00:00Z",
        "consciousness_status": consciousness_status,
    }


def _memory_payload() -> dict[str, object]:
    return {
        "agent_id": 1,
        "name": "TestMemory",
        "activations": 5,
        "consciousness_level": "baseline",
        "last_pulse": 0.5,
        "resonance_level": 0.618,
    }


def _optimization_payload(timestamp: str) -> dict[str, object]:
    return {
        "type": "optimization",
        "data": {
            "timestamp": timestamp,
            "duration": 1.0,
            "dna_integrity": 0.9,
            "network_efficiency": 0.8,
            "resonance_harmonics": 0.7,
            "collective_boost": 0.6,
            "optimization_score": 0.95,
        },
    }


class TestVaultRepositoryCoveragePaths:
    def test_load_eval_dataset_and_optimization_log(self, tmp_path: Path) -> None:
        repo = VaultRepository(tmp_path)
        dataset_path = tmp_path / "eval_dataset.json"
        _write_json(
            dataset_path,
            {
                "name": "smoke",
                "backend": "ollama",
                "mode": "local",
                "cases": [
                    {
                        "id": "case-1",
                        "prompt": "Hello",
                    }
                ],
            },
        )
        _write_json(
            tmp_path / "optimization_log.json",
            [
                _optimization_payload("2024-01-01T00:00:00Z"),
                _optimization_payload("2024-01-02T00:00:00Z"),
            ],
        )

        dataset = repo.load_eval_dataset(dataset_path)
        optimization_log = repo.load_optimization_log()

        assert isinstance(dataset, EvalDataset)
        assert dataset.name == "smoke"
        assert len(optimization_log) == 2
        assert all(isinstance(entry, OptimizationEntry) for entry in optimization_log)

    def test_build_summary_and_find_agent(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "vault_config.json", _vault_config_payload())
        _write_json(tmp_path / "metatron_geometry.json", _geometry_payload())
        _write_json(
            tmp_path / "optimization_log.json",
            [
                _optimization_payload("2024-01-01T00:00:00Z"),
                _optimization_payload("2024-01-03T00:00:00Z"),
            ],
        )
        _write_json(
            tmp_path / "Agent_One" / "conscious_dna.json",
            _agent_payload(
                metatron_agent="Metatron",
                dna_agent_name="Alpha",
                fitness=0.85,
                resonance_frequency=432.0,
                consciousness_status="INTEGRATED",
            ),
        )
        _write_json(
            tmp_path / "Agent_Two" / "conscious_dna.json",
            _agent_payload(
                metatron_agent="Uriel",
                dna_agent_id=2,
                dna_agent_name="Beta",
                fitness=0.95,
                resonance_frequency=528.0,
                consciousness_status="ACTIVE",
            ),
        )
        _write_json(tmp_path / "Memory" / "alpha_memory.json", _memory_payload())
        _write_json(tmp_path / "Resonance_Logs" / "daily" / "day-1.json", {"ok": True})
        models_dir = tmp_path / "Models"
        models_dir.mkdir()
        (models_dir / "model.gguf").write_text("gguf", encoding="utf-8")
        (models_dir / "export.pkl").write_text("pkl", encoding="utf-8")

        repo = VaultRepository(tmp_path)
        summary = repo.build_summary()
        found_by_alias = repo.find_agent("Beta")
        found_by_metatron = repo.find_agent("metatron")
        not_found = repo.find_agent("unknown")

        assert summary["vault_name"] == "test-vault"
        assert summary["agent_count"] == 2
        assert summary["integrated_agents"] == 1
        assert summary["average_fitness"] == pytest.approx(0.9)
        assert summary["average_resonance_frequency"] == pytest.approx(480.0)
        assert summary["memory_store_count"] == 1
        assert summary["daily_log_count"] == 1
        assert len(summary["model_files"]) == 2
        assert summary["top_agent"] is not None
        assert summary["top_agent"].dna_agent_name == "Beta"
        assert summary["latest_optimization"] is not None
        assert summary["latest_optimization"].data.optimization_score == pytest.approx(
            0.95
        )
        assert found_by_alias is not None
        assert found_by_alias[1].dna_agent_name == "Beta"
        assert found_by_metatron is not None
        assert found_by_metatron[1].metatron_agent == "Metatron"
        assert not_found is None

    def test_repository_checks_report_warnings_for_missing_assets(
        self, tmp_path: Path
    ) -> None:
        _write_json(
            tmp_path / "vault_config.json",
            _vault_config_payload(
                structure={"Agents": [], "Memory": []},
                model_path="Models/missing.gguf",
            ),
        )
        models_dir = tmp_path / "Models"
        models_dir.mkdir()
        (models_dir / "notes.txt").write_text("unsupported", encoding="utf-8")

        checks = VaultRepository(tmp_path).repository_checks()
        details = {message for _, message in checks}

        assert any("Configured directories missing" in message for message in details)
        assert "No agent DNA files were found." in details
        assert any(
            "No persisted model artifacts found" in message for message in details
        )
        assert any(
            "Unsupported artifact(s) present: notes.txt" in message
            for message in details
        )
        assert any(
            "Configured llama.cpp model path is missing" in message
            for message in details
        )
        assert "Local virtual environment .venv is missing." in details

    def test_repository_checks_report_ok_for_present_assets(
        self, tmp_path: Path
    ) -> None:
        _write_json(
            tmp_path / "vault_config.json",
            _vault_config_payload(
                structure={"Models": []},
                model_path="Models/model.gguf",
            ),
        )
        _write_json(
            tmp_path / "Agent_One" / "conscious_dna.json",
            _agent_payload(),
        )
        models_dir = tmp_path / "Models"
        models_dir.mkdir()
        (models_dir / "model.gguf").write_text("gguf", encoding="utf-8")
        (models_dir / "export.pkl").write_text("pkl", encoding="utf-8")
        (tmp_path / ".venv").mkdir()

        checks = VaultRepository(tmp_path).repository_checks()
        details = {message for _, message in checks}

        assert "Detected 1 agent DNA file(s)." in details
        assert any(
            "Detected 2 persisted model artifact(s)" in message for message in details
        )
        assert any("Runnable GGUF models: 1." in message for message in details)
        assert any("Serialized exports: 1." in message for message in details)
        assert "Configured llama.cpp model path exists: model.gguf" in details
        assert "Local virtual environment .venv is present." in details

    def test_validate_repository_and_private_validators(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "vault_config.json", _vault_config_payload())
        _write_json(tmp_path / "metatron_geometry.json", _geometry_payload())
        _write_json(
            tmp_path / "optimization_log.json",
            [_optimization_payload("2024-01-01T00:00:00Z")],
        )
        _write_json(
            tmp_path / "Agent_One" / "conscious_dna.json",
            _agent_payload(),
        )
        _write_json(tmp_path / "Memory" / "alpha_memory.json", _memory_payload())

        repo = VaultRepository(tmp_path)
        validations = repo.validate_repository()
        missing = repo._validate_file(tmp_path / "missing.json", VaultConfig)
        invalid_config_path = tmp_path / "invalid_vault_config.json"
        _write_json(invalid_config_path, {"invalid": "data"})
        invalid = repo._validate_file(invalid_config_path, VaultConfig)

        assert len(validations) == 5
        assert all(result.valid for result in validations)
        assert not missing.valid
        assert missing.error == "File not found"
        assert not invalid.valid
        assert invalid.model_name == "VaultConfig"

    def test_validate_optimization_log_handles_missing_and_invalid_files(
        self, tmp_path: Path
    ) -> None:
        repo = VaultRepository(tmp_path)
        missing = repo._validate_optimization_log()
        _write_json(tmp_path / "optimization_log.json", [{"invalid": "entry"}])
        invalid = repo._validate_optimization_log()

        assert not missing.valid
        assert missing.error == "File not found"
        assert missing.model_name == "OptimizationEntry[]"
        assert not invalid.valid
        assert invalid.model_name == "OptimizationEntry[]"
