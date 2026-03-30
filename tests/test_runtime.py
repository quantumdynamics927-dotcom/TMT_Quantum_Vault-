#!/usr/bin/env python3
"""
Tests for Runtime Inspector module.

Tests for runtime detection and status reporting.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tmt_quantum_vault.runtime import RuntimeInspector, RuntimeStatus


class TestRuntimeStatus:
    """Tests for RuntimeStatus dataclass."""
    
    def test_runtime_status_creation(self) -> None:
        """Test creating a RuntimeStatus."""
        status = RuntimeStatus(
            name="Test",
            status="ok",
            detail="Test detail",
        )
        
        assert status.name == "Test"
        assert status.status == "ok"
        assert status.detail == "Test detail"
        assert status.executable is None
        assert status.version is None
    
    def test_runtime_status_with_executable(self) -> None:
        """Test creating a RuntimeStatus with executable."""
        status = RuntimeStatus(
            name="Ollama",
            status="ok",
            detail="Found",
            executable=Path("/usr/bin/ollama"),
            version="0.1.0",
        )
        
        assert status.name == "Ollama"
        assert status.executable == Path("/usr/bin/ollama")
        assert status.version == "0.1.0"


class TestRuntimeInspector:
    """Tests for RuntimeInspector class."""
    
    def test_inspector_initialization(self, tmp_path: Path) -> None:
        """Test RuntimeInspector initialization."""
        inspector = RuntimeInspector(tmp_path)
        
        assert inspector.root == tmp_path.resolve()
        assert inspector.config is None
    
    def test_inspector_with_config(self, tmp_path: Path) -> None:
        """Test RuntimeInspector with config."""
        from tmt_quantum_vault.models import VaultConfig
        
        config = VaultConfig(
            vault_name="test",
            creation_timestamp=0.0,
            structure={},
            stability_baseline=0.5,
            fibonacci_sync=True,
        )
        inspector = RuntimeInspector(tmp_path, config)
        
        assert inspector.config == config
    
    def test_inspect_all(self, tmp_path: Path) -> None:
        """Test inspect_all returns list of statuses."""
        inspector = RuntimeInspector(tmp_path)
        
        with patch.object(inspector, 'inspect_ollama') as mock_ollama, \
             patch.object(inspector, 'inspect_ollama_cloud') as mock_cloud, \
             patch.object(inspector, 'inspect_llama_cpp') as mock_llama:
            
            mock_ollama.return_value = RuntimeStatus(
                name="Ollama", status="ok", detail="Found"
            )
            mock_cloud.return_value = RuntimeStatus(
                name="Ollama Cloud", status="warning", detail="Not configured"
            )
            mock_llama.return_value = RuntimeStatus(
                name="llama.cpp", status="warning", detail="Not found"
            )
            
            results = inspector.inspect_all()
            
            assert len(results) == 3
            assert results[0].name == "Ollama"
            assert results[1].name == "Ollama Cloud"
            assert results[2].name == "llama.cpp"
    
    def test_inspect_ollama_not_found(self, tmp_path: Path) -> None:
        """Test inspect_ollama when executable not found."""
        inspector = RuntimeInspector(tmp_path)
        
        with patch.object(inspector, '_which', return_value=None):
            result = inspector.inspect_ollama()
            
            assert result.name == "Ollama"
            assert result.status == "warning"
            assert "not found" in result.detail.lower()
    
    def test_inspect_ollama_found(self, tmp_path: Path) -> None:
        """Test inspect_ollama when executable found."""
        inspector = RuntimeInspector(tmp_path)
        
        with patch.object(inspector, '_which', return_value=Path("/usr/bin/ollama")), \
             patch.object(inspector, '_command_output', return_value="0.1.0"), \
             patch.object(inspector, '_count_ollama_models', return_value=5):
            
            result = inspector.inspect_ollama()
            
            assert result.name == "Ollama"
            assert result.status == "ok"
            assert "5" in result.detail
            assert result.executable == Path("/usr/bin/ollama")
    
    def test_inspect_llama_cpp_not_found(self, tmp_path: Path) -> None:
        """Test inspect_llama_cpp when nothing found."""
        inspector = RuntimeInspector(tmp_path)
        
        with patch.object(inspector, '_find_llama_cpp_executable', return_value=None), \
             patch.object(inspector, '_configured_model_files', return_value=[]):
            
            result = inspector.inspect_llama_cpp()
            
            assert result.name == "llama.cpp"
            assert result.status == "warning"
    
    def test_inspect_llama_cpp_with_models(self, tmp_path: Path) -> None:
        """Test inspect_llama_cpp when models found."""
        inspector = RuntimeInspector(tmp_path)
        
        mock_models = [tmp_path / "model1.gguf", tmp_path / "model2.gguf"]
        
        with patch.object(inspector, '_find_llama_cpp_executable', return_value=Path("/usr/bin/llama")), \
             patch.object(inspector, '_configured_model_files', return_value=mock_models), \
             patch.object(inspector, '_command_output', return_value="1.0.0"):
            
            result = inspector.inspect_llama_cpp()
            
            assert result.name == "llama.cpp"
            assert result.status == "ok"
            assert "2" in result.detail or "model" in result.detail.lower()


class TestRuntimeInspectorHelpers:
    """Tests for RuntimeInspector helper methods."""
    
    def test_which_found(self, tmp_path: Path) -> None:
        """Test _which when executable found."""
        inspector = RuntimeInspector(tmp_path)
        
        with patch('shutil.which', return_value='/usr/bin/test'):
            result = inspector._which('test')
            
            assert result == Path('/usr/bin/test')
    
    def test_which_not_found(self, tmp_path: Path) -> None:
        """Test _which when executable not found."""
        inspector = RuntimeInspector(tmp_path)
        
        with patch('shutil.which', return_value=None):
            result = inspector._which('nonexistent')
            
            assert result is None
    
    def test_command_output_success(self, tmp_path: Path) -> None:
        """Test _command_output with successful command."""
        inspector = RuntimeInspector(tmp_path)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout="output\n", returncode=0)
            
            result = inspector._command_output(['echo', 'test'])
            
            assert result == "output"
    
    def test_command_output_failure(self, tmp_path: Path) -> None:
        """Test _command_output with failed command."""
        inspector = RuntimeInspector(tmp_path)
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()
            
            result = inspector._command_output(['nonexistent'])
            
            assert result is None  # Returns None on failure, not empty string
    
    def test_count_ollama_models_valid(self, tmp_path: Path) -> None:
        """Test _count_ollama_models with valid output."""
        inspector = RuntimeInspector(tmp_path)
        
        output = "model1\t123B\tmodel1:latest\nmodel2\t456B\tmodel2:latest\n"
        result = inspector._count_ollama_models(output)
        
        assert result == 2
    
    def test_count_ollama_models_empty(self, tmp_path: Path) -> None:
        """Test _count_ollama_models with empty output."""
        inspector = RuntimeInspector(tmp_path)
        
        result = inspector._count_ollama_models("")
        
        assert result is None  # Returns None for empty/falsy input
    
    def test_count_ollama_models_none(self, tmp_path: Path) -> None:
        """Test _count_ollama_models with None."""
        inspector = RuntimeInspector(tmp_path)
        
        result = inspector._count_ollama_models(None)
        
        assert result is None


class TestRuntimeStatusFrozen:
    """Tests for RuntimeStatus frozen dataclass."""
    
    def test_status_is_frozen(self) -> None:
        """Test that RuntimeStatus is frozen (immutable)."""
        status = RuntimeStatus(
            name="Test",
            status="ok",
            detail="Test",
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError
            status.name = "Changed"
    
    def test_status_equality(self) -> None:
        """Test RuntimeStatus equality."""
        status1 = RuntimeStatus(
            name="Test",
            status="ok",
            detail="Test",
        )
        status2 = RuntimeStatus(
            name="Test",
            status="ok",
            detail="Test",
        )
        
        assert status1 == status2