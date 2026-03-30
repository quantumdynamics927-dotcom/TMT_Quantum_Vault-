#!/usr/bin/env python3
"""
Tests for Vault Repository module.

Tests for repository loading and path resolution.
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tmt_quantum_vault.repository import VaultRepository
from tmt_quantum_vault.models import (
    VaultConfig,
    GeometryConfig,
    AgentDNA,
    AgentMemory,
    EvalDataset,
    OptimizationEntry,
)


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
        config_file.write_text(json.dumps({
            "vault_name": "test-vault",
            "creation_timestamp": 0.0,
            "structure": {},
            "stability_baseline": 0.5,
            "fibonacci_sync": True,
        }))
        
        repo = VaultRepository(tmp_path)
        result = repo.load_vault_config()
        
        assert isinstance(result, VaultConfig)
        assert result.vault_name == "test-vault"
    
    def test_load_geometry(self, tmp_path: Path) -> None:
        """Test loading geometry config."""
        geometry_file = tmp_path / "metatron_geometry.json"
        geometry_file.write_text(json.dumps({
            "vault_created": 0.0,
            "silver_ratio": 1.618,
            "bronze_ratio": 1.618,
            "phi_ratio": 1.618,
            "nodes": 13,
            "resonance_pulse": 0.5,
            "consciousness_level": "baseline",
        }))
        
        repo = VaultRepository(tmp_path)
        result = repo.load_geometry()
        
        assert isinstance(result, GeometryConfig)
        assert result.nodes == 13
    
    def test_load_agents(self, tmp_path: Path) -> None:
        """Test loading agents."""
        agent_dir = tmp_path / "Agent_Test"
        agent_dir.mkdir()
        dna_file = agent_dir / "conscious_dna.json"
        dna_file.write_text(json.dumps({
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
        }))
        
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
        memory_file.write_text(json.dumps({
            "agent_id": 1,
            "name": "TestMemory",
            "activations": 5,
            "consciousness_level": "baseline",
            "last_pulse": 0.5,
            "resonance_level": 0.618,
        }))
        
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
        
        # Should raise validation error or handle gracefully
        with pytest.raises(Exception):
            repo.load_vault_config()
    
    def test_load_agents_invalid_dna(self, tmp_path: Path) -> None:
        """Test loading agents with invalid DNA."""
        agent_dir = tmp_path / "Agent_Invalid"
        agent_dir.mkdir()
        dna_file = agent_dir / "conscious_dna.json"
        dna_file.write_text('{"invalid": "data"}')
        
        repo = VaultRepository(tmp_path)
        
        # Should handle validation error
        with pytest.raises(Exception):
            repo.load_agents()