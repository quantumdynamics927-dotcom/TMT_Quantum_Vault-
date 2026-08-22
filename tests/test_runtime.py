#!/usr/bin/env python3
"""
Tests for Runtime Inspector module.

Tests for runtime detection and status reporting.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tmt_quantum_vault.models import VaultConfig
from tmt_quantum_vault.runtime import RuntimeHealth, RuntimeInspector, RuntimeStatus


class TestRuntimeStatus:
    """Tests for RuntimeStatus dataclass."""

    def test_runtime_status_creation(self) -> None:
        """Test creating a RuntimeStatus."""
        status = RuntimeStatus(
            name="Test",
            status=RuntimeHealth.OK,
            detail="Test detail",
        )

        assert status.name == "Test"
        assert status.status == RuntimeHealth.OK
        assert status.detail == "Test detail"
        assert status.executable is None
        assert status.version is None

    def test_runtime_status_with_executable(self) -> None:
        """Test creating a RuntimeStatus with executable."""
        status = RuntimeStatus(
            name="Ollama",
            status=RuntimeHealth.OK,
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

        with (
            patch.object(inspector, "inspect_ollama") as mock_ollama,
            patch.object(inspector, "inspect_ollama_cloud") as mock_cloud,
            patch.object(inspector, "inspect_llama_cpp") as mock_llama,
        ):

            mock_ollama.return_value = RuntimeStatus(
                name="Ollama", status=RuntimeHealth.OK, detail="Found"
            )
            mock_cloud.return_value = RuntimeStatus(
                name="Ollama Cloud",
                status=RuntimeHealth.WARNING,
                detail="Not configured",
            )
            mock_llama.return_value = RuntimeStatus(
                name="llama.cpp", status=RuntimeHealth.WARNING, detail="Not found"
            )

            results = inspector.inspect_all()

            assert len(results) == 3
            assert results[0].name == "Ollama"
            assert results[1].name == "Ollama Cloud"
            assert results[2].name == "llama.cpp"

    def test_inspect_ollama_not_found(self, tmp_path: Path) -> None:
        """Test inspect_ollama when executable not found."""
        inspector = RuntimeInspector(tmp_path)

        with patch.object(inspector, "_which", return_value=None):
            result = inspector.inspect_ollama()

            assert result.name == "Ollama"
            assert result.status == RuntimeHealth.WARNING
            assert "not found" in result.detail.lower()

    def test_inspect_ollama_found(self, tmp_path: Path) -> None:
        """Test inspect_ollama when executable found."""
        inspector = RuntimeInspector(tmp_path)

        with (
            patch.object(inspector, "_which", return_value=Path("/usr/bin/ollama")),
            patch.object(inspector, "_command_output", return_value="0.1.0"),
            patch.object(inspector, "_count_ollama_models", return_value=5),
        ):

            result = inspector.inspect_ollama()

            assert result.name == "Ollama"
            assert result.status == RuntimeHealth.OK
            assert "5" in result.detail
            assert result.executable == Path("/usr/bin/ollama")

    def test_inspect_llama_cpp_not_found(self, tmp_path: Path) -> None:
        """Test inspect_llama_cpp when nothing found."""
        inspector = RuntimeInspector(tmp_path)

        with (
            patch.object(inspector, "_find_llama_cpp_executable", return_value=None),
            patch.object(inspector, "_configured_model_files", return_value=[]),
        ):

            result = inspector.inspect_llama_cpp()

            assert result.name == "llama.cpp"
            assert result.status == RuntimeHealth.WARNING

    def test_inspect_llama_cpp_with_models(self, tmp_path: Path) -> None:
        """Test inspect_llama_cpp when models found."""
        inspector = RuntimeInspector(tmp_path)

        mock_models = [tmp_path / "model1.gguf", tmp_path / "model2.gguf"]

        with (
            patch.object(
                inspector,
                "_find_llama_cpp_executable",
                return_value=Path("/usr/bin/llama"),
            ),
            patch.object(
                inspector, "_configured_model_files", return_value=mock_models
            ),
            patch.object(inspector, "_command_output", return_value="1.0.0"),
        ):

            result = inspector.inspect_llama_cpp()

            assert result.name == "llama.cpp"
            assert result.status == RuntimeHealth.OK
            assert "2" in result.detail or "model" in result.detail.lower()


class TestRuntimeInspectorHelpers:
    """Tests for RuntimeInspector helper methods."""

    def test_which_found(self, tmp_path: Path) -> None:
        """Test _which when executable found."""
        inspector = RuntimeInspector(tmp_path)

        with patch("shutil.which", return_value="/usr/bin/test"):
            result = inspector._which("test")

            assert result == Path("/usr/bin/test")

    def test_which_not_found(self, tmp_path: Path) -> None:
        """Test _which when executable not found."""
        inspector = RuntimeInspector(tmp_path)

        with patch("shutil.which", return_value=None):
            result = inspector._which("nonexistent")

            assert result is None

    def test_command_output_success(self, tmp_path: Path) -> None:
        """Test _command_output with successful command."""
        inspector = RuntimeInspector(tmp_path)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="output\n", returncode=0)

            result = inspector._command_output(["echo", "test"])

            assert result == "output"

    def test_command_output_failure(self, tmp_path: Path) -> None:
        """Test _command_output with failed command."""
        inspector = RuntimeInspector(tmp_path)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = inspector._command_output(["nonexistent"])

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
            status=RuntimeHealth.OK,
            detail="Test",
        )

        with pytest.raises(FrozenInstanceError):
            status.name = "Changed"

    def test_status_equality(self) -> None:
        """Test RuntimeStatus equality."""
        status1 = RuntimeStatus(
            name="Test",
            status=RuntimeHealth.OK,
            detail="Test",
        )
        status2 = RuntimeStatus(
            name="Test",
            status=RuntimeHealth.OK,
            detail="Test",
        )

        assert status1 == status2


class TestRuntimeHealth:
    """Tests for RuntimeHealth StrEnum."""

    def test_health_members_compare_to_strings(self) -> None:
        """StrEnum members compare equal to their string values."""
        assert RuntimeHealth.OK == "ok"
        assert RuntimeHealth.WARNING == "warning"
        assert RuntimeHealth.ERROR == "error"

    def test_health_serializes_to_plain_string(self) -> None:
        """JSON serialization yields a plain string, not an enum object."""
        import json

        assert json.dumps({"status": RuntimeHealth.OK}) == '{"status": "ok"}'


def _runtime_config(
    *,
    cloud_model: str = "qwen3.5:397b-cloud",
    executable_path: str | None = None,
    model_path: str = "Models/model.gguf",
) -> VaultConfig:
    return VaultConfig(
        vault_name="test",
        creation_timestamp=0.0,
        structure={},
        stability_baseline=0.5,
        fibonacci_sync=True,
        runtime={
            "ollama": {"cloud_model": cloud_model},
            "llama_cpp": {
                "executable_path": executable_path,
                "model_path": model_path,
            },
        },
    )


class TestRuntimeInspectorCoveragePaths:
    def test_inspect_ollama_handles_unreadable_inventory(self, tmp_path: Path) -> None:
        inspector = RuntimeInspector(tmp_path)

        with (
            patch.object(inspector, "_which", return_value=Path("/usr/bin/ollama")),
            patch.object(
                inspector,
                "_command_output",
                side_effect=["ollama version is 0.1.0\nbuild info", None],
            ),
            patch.object(inspector, "_count_ollama_models", return_value=None),
        ):
            result = inspector.inspect_ollama()

        assert result.status == RuntimeHealth.OK
        assert "could not be read" in result.detail.lower()
        assert result.version == "ollama version is 0.1.0"

    def test_inspect_llama_cpp_reports_missing_configured_path_and_artifacts(
        self, tmp_path: Path
    ) -> None:
        inspector = RuntimeInspector(
            tmp_path, _runtime_config(model_path="Models/missing.gguf")
        )

        with (
            patch.object(inspector, "_find_llama_cpp_executable", return_value=None),
            patch.object(inspector, "_configured_model_files", return_value=[]),
            patch.object(
                inspector,
                "_configured_model_path",
                return_value=tmp_path / "Models" / "missing.gguf",
            ),
            patch.object(
                inspector,
                "_serialized_model_artifacts",
                return_value=[tmp_path / "Models" / "agent.pkl"],
            ),
            patch.object(
                inspector,
                "_unsupported_model_artifacts",
                return_value=[tmp_path / "Models" / "notes.txt"],
            ),
        ):
            result = inspector.inspect_llama_cpp()

        assert result.status == RuntimeHealth.WARNING
        assert "configured model path is missing" in result.detail.lower()
        assert "agent.pkl" in result.detail
        assert "notes.txt" in result.detail

    def test_inspect_llama_cpp_warns_when_models_exist_without_executable(
        self, tmp_path: Path
    ) -> None:
        inspector = RuntimeInspector(
            tmp_path, _runtime_config(model_path="Models/missing.gguf")
        )
        model_files = [tmp_path / "Models" / "a.gguf", tmp_path / "Models" / "b.gguf"]

        with (
            patch.object(inspector, "_find_llama_cpp_executable", return_value=None),
            patch.object(
                inspector, "_configured_model_files", return_value=model_files
            ),
            patch.object(
                inspector,
                "_configured_model_path",
                return_value=tmp_path / "Models" / "missing.gguf",
            ),
            patch.object(
                inspector,
                "_serialized_model_artifacts",
                return_value=[tmp_path / "Models" / "agent.pkl"],
            ),
            patch.object(inspector, "_unsupported_model_artifacts", return_value=[]),
        ):
            result = inspector.inspect_llama_cpp()

        assert result.status == RuntimeHealth.WARNING
        assert "Detected 2 GGUF model(s)" in result.detail
        assert "no llama.cpp executable was found" in result.detail
        assert "agent.pkl" in result.detail

    def test_inspect_llama_cpp_with_executable_and_no_models(
        self, tmp_path: Path
    ) -> None:
        inspector = RuntimeInspector(
            tmp_path, _runtime_config(model_path="Models/missing.gguf")
        )

        with (
            patch.object(
                inspector,
                "_find_llama_cpp_executable",
                return_value=Path("/usr/bin/llama-cli"),
            ),
            patch.object(inspector, "_configured_model_files", return_value=[]),
            patch.object(
                inspector,
                "_configured_model_path",
                return_value=tmp_path / "Models" / "missing.gguf",
            ),
            patch.object(
                inspector,
                "_serialized_model_artifacts",
                return_value=[tmp_path / "Models" / "agent.pkl"],
            ),
            patch.object(
                inspector,
                "_unsupported_model_artifacts",
                return_value=[tmp_path / "Models" / "notes.txt"],
            ),
            patch.object(
                inspector,
                "_command_output",
                return_value="version: 1.2.3\nbuilt with avx2",
            ),
        ):
            result = inspector.inspect_llama_cpp()

        assert result.status == RuntimeHealth.WARNING
        assert "no GGUF models were found" in result.detail
        assert result.version == "1.2.3 | avx2"

    def test_inspect_ollama_cloud_branches(self, tmp_path: Path) -> None:
        no_executable = RuntimeInspector(tmp_path, _runtime_config())
        with patch.object(no_executable, "_which", return_value=None):
            assert no_executable.inspect_ollama_cloud().detail == (
                "Ollama executable not found on PATH."
            )

        no_config = RuntimeInspector(tmp_path)
        with patch.object(no_config, "_which", return_value=Path("/usr/bin/ollama")):
            assert no_config.inspect_ollama_cloud().detail == (
                "Vault runtime configuration is not available."
            )

        invalid_tag = RuntimeInspector(
            tmp_path, _runtime_config(cloud_model="qwen3:8b")
        )
        with patch.object(invalid_tag, "_which", return_value=Path("/usr/bin/ollama")):
            assert (
                "does not use a cloud tag" in invalid_tag.inspect_ollama_cloud().detail
            )

    @pytest.mark.parametrize(
        ("model_list", "expected_status", "expected_detail"),
        [
            (None, RuntimeHealth.WARNING, "Could not read Ollama model inventory."),
            (
                "NAME SIZE\nqwen3.5:397b-cloud 1GB\n",
                RuntimeHealth.OK,
                "Configured cloud model is visible",
            ),
            (
                "NAME SIZE\nother-cloud 1GB\n",
                RuntimeHealth.WARNING,
                "Visible cloud model(s): other-cloud",
            ),
            (
                "NAME SIZE\nqwen3:8b 1GB\n",
                RuntimeHealth.WARNING,
                "No cloud-tagged models are visible",
            ),
        ],
    )
    def test_inspect_ollama_cloud_inventory_outcomes(
        self,
        tmp_path: Path,
        model_list: str | None,
        expected_status: RuntimeHealth,
        expected_detail: str,
    ) -> None:
        inspector = RuntimeInspector(tmp_path, _runtime_config())

        with (
            patch.object(inspector, "_which", return_value=Path("/usr/bin/ollama")),
            patch.object(inspector, "_command_output", return_value=model_list),
        ):
            result = inspector.inspect_ollama_cloud()

        assert result.status == expected_status
        assert expected_detail in result.detail

    def test_find_llama_cpp_executable_prefers_configured_path(
        self, tmp_path: Path
    ) -> None:
        configured_binary = tmp_path / "bin" / "llama-cli"
        configured_binary.parent.mkdir(parents=True)
        configured_binary.write_text("binary", encoding="utf-8")
        configured = RuntimeInspector(
            tmp_path,
            _runtime_config(executable_path="bin/llama-cli"),
        )

        assert configured._find_llama_cpp_executable() == configured_binary.resolve()

    def test_find_llama_cpp_executable_searches_roots_when_which_fails(
        self, tmp_path: Path
    ) -> None:
        discovered = RuntimeInspector(tmp_path)

        discovered_binary = tmp_path / "tools" / "llama-server"
        discovered_binary.parent.mkdir(exist_ok=True)
        discovered_binary.write_text("binary", encoding="utf-8")
        with patch.object(discovered, "_which", return_value=None):
            assert discovered._find_llama_cpp_executable() == discovered_binary

    def test_model_artifact_helpers_and_cloud_model_parsing(
        self, tmp_path: Path
    ) -> None:
        models_dir = tmp_path / "Models"
        models_dir.mkdir()
        gguf_model = models_dir / "base.gguf"
        gguf_model.write_text("gguf", encoding="utf-8")
        external_model = tmp_path / "external.gguf"
        external_model.write_text("gguf", encoding="utf-8")
        (models_dir / "agent.pkl").write_text("pkl", encoding="utf-8")
        (models_dir / "snapshot.json.gz").write_text("json", encoding="utf-8")
        (models_dir / "notes.txt").write_text("txt", encoding="utf-8")

        default_inspector = RuntimeInspector(tmp_path)
        configured_inspector = RuntimeInspector(
            tmp_path,
            _runtime_config(model_path="external.gguf"),
        )

        assert set(default_inspector._configured_model_files()) == {gguf_model}
        assert configured_inspector._configured_model_path() == external_model
        assert set(configured_inspector._configured_model_files()) == {
            gguf_model,
            external_model,
        }
        assert set(configured_inspector._serialized_model_artifacts()) == {
            models_dir / "agent.pkl",
            models_dir / "snapshot.json.gz",
        }
        assert set(configured_inspector._unsupported_model_artifacts()) == {
            models_dir / "notes.txt"
        }
        assert configured_inspector._parse_ollama_models(
            "NAME ID\nqwen3.5:397b-cloud 1\n"
        ) == ["qwen3.5:397b-cloud"]
        assert configured_inspector._is_cloud_model_tag("qwen3.5:397b-cloud") is True
        assert configured_inspector._is_cloud_model_tag("qwen3:8b") is False
        assert configured_inspector._count_ollama_models("NAME ID\n") == 0
        assert (
            configured_inspector._summarize_version(
                "llama.cpp",
                "version: 1.2.3\nbuilt with avx2",
            )
            == "1.2.3 | avx2"
        )
        assert (
            configured_inspector._summarize_version("llama.cpp", "plain text")
            == "plain text"
        )

    def test_command_output_prefers_stderr_and_handles_empty_output(
        self, tmp_path: Path
    ) -> None:
        inspector = RuntimeInspector(tmp_path)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="warning\n")
            assert inspector._command_output(["tool"]) == "warning"

            mock_run.return_value = MagicMock(stdout="", stderr="")
            assert inspector._command_output(["tool"]) is None
