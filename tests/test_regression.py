# pyright: reportMissingImports=false

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import requests
from typer.testing import CliRunner

from tmt_quantum_vault.cli import (
    _find_latest_release_evidence_bundle,
    app,
    strip_thinking,
)
from tmt_quantum_vault.models import (
    AgentDNA,
    EvalDataset,
    OptimizationEntry,
    RuntimeConfig,
)
from tmt_quantum_vault.ollama_api import is_available
from tmt_quantum_vault.ollama_api import run as ollama_run
from tmt_quantum_vault.repository import VaultRepository
from tmt_quantum_vault.runner import RunResult, RuntimeRunner
from tmt_quantum_vault.runtime import RuntimeInspector

BRAILLE_SPINNERS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
RUNNER = CliRunner()
TEST_REPO_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(TEST_REPO_ROOT / "tools"))
import agent_analyst as aa  # noqa: E402
import promoter_loader as pl  # noqa: E402
import update_vault_docs as uvd  # noqa: E402


def _safe_stderr(text: str) -> str:
    sanitized = ANSI_RE.sub("", text)
    encoded = sanitized.encode("cp1252", errors="ignore")
    return encoded.decode("cp1252").strip()


def test_stderr_strip_removes_braille() -> None:
    text = f"\x1b[?25l{BRAILLE_SPINNERS}\x1b[?25h"
    assert _safe_stderr(text) == ""


def test_stderr_preserves_real_errors() -> None:
    assert _safe_stderr("error: model not found") == "error: model not found"


def test_stderr_no_unicode_encode_error() -> None:
    text = f"\x1b[?25l{BRAILLE_SPINNERS} Some real error \x1b[0m"
    _safe_stderr(text).encode("cp1252")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "Thinking...\nStep 1.\n...done thinking.\n\nTMT cloud test",
            "TMT cloud test",
        ),
        (
            "<think>\nsome reasoning\n</think>\nTMT cloud test",
            "TMT cloud test",
        ),
        ("TMT cloud test", "TMT cloud test"),
    ],
)
def test_strip_thinking(raw: str, expected: str) -> None:
    assert strip_thinking(raw) == expected


@pytest.mark.skipif(not is_available(), reason="Ollama not running")
def test_ollama_api_local_smoke() -> None:
    response = ollama_run(
        "qwen2.5-coder:1.5b",
        "Reply with exactly: TMT regression test",
        num_predict=16,
        temperature=0.0,
        timeout=60,
    )
    assert response.returncode == 0
    assert "TMT regression test" in response.response


@pytest.mark.skipif(not is_available(), reason="Ollama not running")
def test_json_output_mode() -> None:
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "tmt_quantum_vault",
            "run",
            "Reply with exactly: TMT json test",
            "--raw-final-only",
            "--json",
            "--timeout",
            "60",
        ],
        check=False,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        cwd=str(TEST_REPO_ROOT),
    )
    payload = json.loads(process.stdout)
    assert payload["returncode"] == 0
    assert "TMT json test" in payload["output"]
    assert "model" in payload
    assert "duration_ms" in payload


def test_runtime_json_output() -> None:
    mocked_runtime_checks = [
        SimpleNamespace(
            name="Ollama",
            status="ok",
            detail="available",
            executable=Path("C:/ollama.exe"),
            version="0.18.0",
        )
    ]
    with patch("tmt_quantum_vault.cli._runtime") as mock_runtime:
        mock_runtime.return_value.inspect_all.return_value = mocked_runtime_checks
        result = RUNNER.invoke(app, ["runtime", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "runtime" in payload
    assert isinstance(payload["runtime"], list)


def test_doctor_json_output() -> None:
    mocked_runtime_checks = [
        SimpleNamespace(
            name="Ollama",
            status="ok",
            detail="available",
            executable=Path("C:/ollama.exe"),
            version="0.18.0",
        )
    ]
    with patch("tmt_quantum_vault.cli._repo") as mock_repo:
        with patch("tmt_quantum_vault.cli._runtime") as mock_runtime:
            mock_repo.return_value.repository_checks.return_value = [
                ("ok", "repo healthy")
            ]
            mock_runtime.return_value.inspect_all.return_value = mocked_runtime_checks
            result = RUNNER.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "repository" in payload
    assert "runtime" in payload


def test_summary_json_output() -> None:
    mocked_summary = {
        "vault_name": "TMT_Quantum_Vault",
        "consciousness_level": "INTELLIGENT_CORE",
        "fibonacci_sync": True,
        "agent_count": 12,
        "integrated_agents": 12,
        "average_fitness": 0.872,
        "average_resonance_frequency": 595.0,
        "top_agent": AgentDNA.model_validate(
            {
                "metatron_agent": "Bronze",
                "dna_agent_id": 6,
                "dna_agent_name": "Michael",
                "dna_specialization": "Protection & Justice",
                "conscious_dna": "ATCG",
                "phi_score": 1.618,
                "fibonacci_alignment": 0.987,
                "gc_content": 0.55,
                "palindromes": 8,
                "fitness": 0.929,
                "resonance_frequency": 528.0,
                "integration_timestamp": "2026-01-01T00:00:00Z",
                "consciousness_status": "INTEGRATED",
            }
        ),
        "memory_store_count": 12,
        "daily_log_count": 43,
        "model_files": [Path("Models/qwen3-8b.gguf")],
        "latest_optimization": OptimizationEntry.model_validate(
            {
                "type": "optimization",
                "data": {
                    "timestamp": "2026-01-09T21:10:55.489611",
                    "duration": 1.0,
                    "dna_integrity": 0.9,
                    "network_efficiency": 0.864,
                    "resonance_harmonics": 0.9,
                    "collective_boost": 0.9,
                    "optimization_score": 0.922,
                },
            }
        ),
    }

    with patch("tmt_quantum_vault.cli._repo") as mock_repo:
        mock_repo.return_value.build_summary.return_value = mocked_summary
        result = RUNNER.invoke(app, ["summary", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["vault_name"] == "TMT_Quantum_Vault"
    assert payload["model_count"] == 1
    assert payload["model_files"] == ["Models/qwen3-8b.gguf"]
    assert payload["top_agent"]["dna_agent_name"] == "Michael"
    latest_score = payload["latest_optimization"]["data"]["optimization_score"]
    assert latest_score == 0.922
    assert payload["returncode"] == 0


def test_validate_json_output() -> None:
    mocked_results = [
        SimpleNamespace(
            path="vault_config.json",
            model_name="VaultConfig",
            valid=True,
            error=None,
        ),
        SimpleNamespace(
            path="Agent_Bronze/conscious_dna.json",
            model_name="AgentDNA",
            valid=False,
            error="missing field",
        ),
    ]

    with patch("tmt_quantum_vault.cli._repo") as mock_repo:
        validate_repository = mock_repo.return_value.validate_repository
        validate_repository.return_value = mocked_results
        result = RUNNER.invoke(app, ["validate", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["summary"]["checked_files"] == 2
    assert payload["summary"]["valid_files"] == 1
    assert payload["summary"]["invalid_files"] == 1
    assert payload["results"][1]["error"] == "missing field"
    assert payload["returncode"] == 1


def test_runtime_record_path(tmp_path: Path) -> None:
    mocked_runtime_checks = [
        SimpleNamespace(
            name="Ollama Cloud",
            status="ok",
            detail="configured cloud model visible",
            executable=Path("C:/ollama.exe"),
            version=None,
        )
    ]
    record_path = tmp_path / "runtime-record.json"

    with patch("tmt_quantum_vault.cli._runtime") as mock_runtime:
        mock_runtime.return_value.inspect_all.return_value = mocked_runtime_checks
        result = RUNNER.invoke(
            app,
            ["runtime", "--json", "--record-path", str(record_path)],
        )

    assert result.exit_code == 0
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    assert payload["record_type"] == "runtime"
    assert payload["runtime"][0]["name"] == "Ollama Cloud"


def test_agent_task_json_output() -> None:
    mocked_results = [
        RunResult(
            backend="ollama",
            mode="cloud",
            model="test-model",
            command="ollama HTTP API",
            returncode=0,
            stdout="workflow output",
            stderr="",
            duration_ms=10,
        ),
        RunResult(
            backend="ollama",
            mode="cloud",
            model="test-model",
            command="ollama HTTP API",
            returncode=0,
            stdout="validator output",
            stderr="",
            duration_ms=20,
        ),
        RunResult(
            backend="ollama",
            mode="cloud",
            model="test-model",
            command="ollama HTTP API",
            returncode=0,
            stdout="visual output",
            stderr="",
            duration_ms=30,
        ),
    ]

    with patch("tmt_quantum_vault.cli._runner") as mock_runner:
        mock_runner.return_value.run.side_effect = mocked_results
        result = RUNNER.invoke(
            app,
            [
                "agent-task",
                "Summarize the vault state",
                "--json",
                "--raw-final-only",
            ],
        )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["final_output"] == "visual output"
    assert [stage["agent"] for stage in payload["stages"]] == [
        "Workflow",
        "Validator",
        "Visual",
    ]

    call_args = mock_runner.return_value.run.call_args_list
    workflow_prompt = call_args[0].kwargs["prompt"]
    validator_prompt = call_args[1].kwargs["prompt"]
    visual_prompt = call_args[2].kwargs["prompt"]

    assert "Return exactly one JSON object and nothing else." in workflow_prompt
    assert '"stage": "Workflow"' in workflow_prompt
    assert '"required_keys"' in workflow_prompt

    assert "Previous stages as JSON:" in validator_prompt
    assert '"agent": "Workflow"' in validator_prompt
    assert '"stage": "Validator"' in validator_prompt
    assert '"assessment"' in validator_prompt

    assert '"stage": "Visual"' in visual_prompt
    assert '"input_stage": "Validator"' in visual_prompt
    assert '"visual"' in visual_prompt


def test_eval_json_output(tmp_path: Path) -> None:
    dataset_path = tmp_path / "baseline.json"
    dataset_path.write_text(
        json.dumps(
            {
                "name": "baseline",
                "description": "small regression eval",
                "backend": "ollama",
                "mode": "cloud",
                "model": "qwen3-coder-next:cloud",
                "cases": [
                    {
                        "id": "exact-smoke",
                        "prompt": "Reply with exactly: TMT cloud test",
                        "expectation": {"contains_all": ["TMT cloud test"]},
                    },
                    {
                        "id": "json-shape",
                        "prompt": ("Return exactly one JSON object with status " "ok."),
                        "expectation": {
                            "contains_all": ['"status"', '"ok"'],
                            "excludes": ["```"],
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    mocked_results = [
        RunResult(
            backend="ollama",
            mode="cloud",
            model="qwen3-coder-next:cloud",
            command="https://ollama.com/api/generate",
            returncode=0,
            stdout="TMT cloud test",
            stderr="",
            duration_ms=10,
        ),
        RunResult(
            backend="ollama",
            mode="cloud",
            model="qwen3-coder-next:cloud",
            command="https://ollama.com/api/generate",
            returncode=0,
            stdout='{"status":"ok"}',
            stderr="",
            duration_ms=15,
        ),
    ]

    with patch("tmt_quantum_vault.cli._runner") as mock_runner:
        mock_runner.return_value.run.side_effect = mocked_results
        result = RUNNER.invoke(
            app,
            [
                "eval",
                "--dataset",
                str(dataset_path),
                "--json",
            ],
        )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["dataset"]["name"] == "baseline"
    assert payload["summary"]["passed_cases"] == 2
    assert payload["summary"]["failed_cases"] == 0
    assert payload["returncode"] == 0


def test_eval_record_path_and_failure_exit(tmp_path: Path) -> None:
    dataset_path = tmp_path / "baseline.json"
    record_path = tmp_path / "eval-record.json"
    dataset_path.write_text(
        json.dumps(
            {
                "name": "baseline",
                "cases": [
                    {
                        "id": "missing-token",
                        "prompt": "Reply with exactly: TMT cloud test",
                        "expectation": {"contains_all": ["TMT cloud test"]},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    mocked_results = [
        RunResult(
            backend="ollama",
            mode="cloud",
            model="qwen3-coder-next:cloud",
            command="https://ollama.com/api/generate",
            returncode=0,
            stdout="wrong output",
            stderr="",
            duration_ms=7,
        )
    ]

    with patch("tmt_quantum_vault.cli._runner") as mock_runner:
        mock_runner.return_value.run.side_effect = mocked_results
        result = RUNNER.invoke(
            app,
            [
                "eval",
                "--dataset",
                str(dataset_path),
                "--json",
                "--record-path",
                str(record_path),
            ],
        )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["summary"]["failed_cases"] == 1
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["record_type"] == "eval"
    assert record["cases"][0]["passed"] is False


def test_cloud_mode_rejects_non_cloud_tag() -> None:
    runner = RuntimeRunner(TEST_REPO_ROOT, RuntimeConfig())
    result = runner.run(
        prompt="Reply with exactly: test",
        mode="cloud",
        model="nemotron-3-super:120b",
    )
    assert result.returncode == 1
    assert "explicit cloud model tag" in result.stderr


def test_cloud_mode_uses_ollama_cli() -> None:
    runner = RuntimeRunner(TEST_REPO_ROOT, RuntimeConfig())
    completed = subprocess.CompletedProcess(
        args=["ollama"],
        returncode=0,
        stdout='{"stage":"Workflow"}',
        stderr="",
    )
    with patch("tmt_quantum_vault.runner.subprocess.run") as mock_subprocess:
        mock_subprocess.return_value = completed
        result = runner.run(
            prompt="Reply with exactly: test",
            mode="cloud",
            model="qwen3-coder-next:cloud",
            system="Return JSON only.",
        )

    assert result.returncode == 0
    assert result.mode == "cloud"
    assert result.command[:3] == ["ollama", "run", "qwen3-coder-next:cloud"]
    assert "System instructions:" in result.command[3]


def test_cloud_mode_uses_api_key_direct_api() -> None:
    runner = RuntimeRunner(TEST_REPO_ROOT, RuntimeConfig())

    with patch.dict(os.environ, {"OLLAMA_API_KEY": "test-key"}, clear=False):
        with patch("tmt_quantum_vault.runner.ollama_run") as mock_ollama_run:
            mock_ollama_run.return_value = SimpleNamespace(
                returncode=0,
                response="TMT cloud test",
                total_duration_ns=123_000_000,
            )
            result = runner.run(
                prompt="Reply with exactly: test",
                mode="cloud",
                model="qwen3-coder-next:cloud",
                system="Return JSON only.",
            )

    assert result.returncode == 0
    assert result.command == "https://ollama.com/api/generate"
    assert result.stdout == "TMT cloud test"
    mock_ollama_run.assert_called_once_with(
        model="qwen3-coder-next:cloud",
        prompt="Reply with exactly: test",
        system="Return JSON only.",
        timeout=120,
        temperature=0.0,
        base_url="https://ollama.com",
        headers={"Authorization": "Bearer test-key"},
    )


def test_cloud_mode_api_key_unauthorized_forces_failure() -> None:
    runner = RuntimeRunner(TEST_REPO_ROOT, RuntimeConfig())
    response = Mock(spec=requests.Response)
    response.status_code = 401
    response.json.return_value = {"error": "unauthorized"}
    response.text = '{"error":"unauthorized"}'
    response.url = "https://ollama.com/api/generate"

    with patch.dict(os.environ, {"OLLAMA_API_KEY": "test-key"}, clear=False):
        with patch("tmt_quantum_vault.runner.ollama_run") as mock_ollama_run:
            mock_ollama_run.side_effect = requests.HTTPError(
                "401 Client Error: Unauthorized",
                response=response,
            )
            result = runner.run(
                prompt="Reply with exactly: test",
                mode="cloud",
                model="qwen3-coder-next:cloud",
            )

    assert result.returncode == 1
    assert result.command == "https://ollama.com/api/generate"
    assert result.stderr == "unauthorized"


def test_cloud_mode_auth_message_forces_failure() -> None:
    runner = RuntimeRunner(TEST_REPO_ROOT, RuntimeConfig())
    completed = subprocess.CompletedProcess(
        args=["ollama"],
        returncode=0,
        stdout="You need to be signed in to Ollama to run Cloud models.",
        stderr="",
    )
    with patch("tmt_quantum_vault.runner.subprocess.run") as mock_subprocess:
        mock_subprocess.return_value = completed
        result = runner.run(
            prompt="Reply with exactly: test",
            mode="cloud",
            model="qwen3-coder-next:cloud",
        )

    assert result.returncode == 1
    assert result.stdout == ("You need to be signed in to Ollama to run Cloud models.")
    assert "signed in to Ollama" in result.stderr


def test_inspect_ollama_cloud_ok() -> None:
    inspector = RuntimeInspector(
        TEST_REPO_ROOT,
        type(
            "ConfigWrapper",
            (),
            {
                "runtime": RuntimeConfig.model_validate(
                    {"ollama": {"cloud_model": "qwen3-coder-next:cloud"}}
                )
            },
        )(),
    )
    with patch.object(inspector, "_which", return_value=Path("C:/ollama.exe")):
        with patch.object(
            inspector,
            "_command_output",
            return_value=(
                "NAME ID SIZE MODIFIED\n"
                "qwen3-coder-next:cloud aa626c11ae8d - 3 weeks ago"
            ),
        ):
            status = inspector.inspect_ollama_cloud()

    assert status.status == "ok"
    assert "qwen3-coder-next:cloud" in status.detail


def test_smoke_cloud_json_output() -> None:
    mocked_result = RunResult(
        backend="ollama",
        mode="cloud",
        model="qwen3-coder-next:cloud",
        command=["ollama", "run", "qwen3-coder-next:cloud"],
        returncode=0,
        stdout="TMT cloud test",
        stderr="",
        duration_ms=42,
    )

    with patch("tmt_quantum_vault.cli._runner") as mock_runner:
        mock_runner.return_value.run.return_value = mocked_result
        result = RUNNER.invoke(app, ["smoke-cloud", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["mode"] == "cloud"
    assert payload["model"] == "qwen3-coder-next:cloud"
    assert payload["output"] == "TMT cloud test"


def test_smoke_cloud_record_path(tmp_path: Path) -> None:
    mocked_result = RunResult(
        backend="ollama",
        mode="cloud",
        model="qwen3-coder-next:cloud",
        command=["ollama", "run", "qwen3-coder-next:cloud"],
        returncode=0,
        stdout="TMT cloud test",
        stderr="",
        duration_ms=42,
    )
    record_path = tmp_path / "smoke-cloud.json"

    with patch("tmt_quantum_vault.cli._runner") as mock_runner:
        mock_runner.return_value.run.return_value = mocked_result
        result = RUNNER.invoke(
            app,
            ["smoke-cloud", "--record-path", str(record_path), "--json"],
        )

    assert result.exit_code == 0
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    assert payload["record_type"] == "smoke-cloud"
    assert payload["output"] == "TMT cloud test"


def test_smoke_cloud_auth_message_exits_nonzero() -> None:
    mocked_result = RunResult(
        backend="ollama",
        mode="cloud",
        model="qwen3-coder-next:cloud",
        command=["ollama", "run", "qwen3-coder-next:cloud"],
        returncode=1,
        stdout="You need to be signed in to Ollama to run Cloud models.",
        stderr="You need to be signed in to Ollama to run Cloud models.",
        duration_ms=0,
    )

    with patch("tmt_quantum_vault.cli._runner") as mock_runner:
        mock_runner.return_value.run.return_value = mocked_result
        result = RUNNER.invoke(app, ["smoke-cloud", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["returncode"] == 1


def test_repository_checks_report_missing_model_and_artifacts(
    tmp_path: Path,
) -> None:
    (tmp_path / "Models").mkdir()
    (tmp_path / "Models" / ".resonance").write_text(
        "signal",
        encoding="utf-8",
    )
    (tmp_path / ".venv").mkdir()

    source_root = Path(__file__).resolve().parents[1]
    for file_name in (
        "vault_config.json",
        "metatron_geometry.json",
        "optimization_log.json",
    ):
        (tmp_path / file_name).write_text(
            (source_root / file_name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    agent_dirs = list(source_root.glob("Agent_*"))
    for agent_dir in agent_dirs:
        target_dir = tmp_path / agent_dir.name
        target_dir.mkdir()
        (target_dir / "conscious_dna.json").write_text(
            (agent_dir / "conscious_dna.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    for memory_dir_name in (
        "Bio_Resonance",
        "Mandala_Geometry",
        "Shadow_Drive",
        "Stealth_Logs",
    ):
        source_dir = source_root / memory_dir_name
        target_dir = tmp_path / memory_dir_name
        target_dir.mkdir()
        for memory_file in source_dir.glob("*_memory.json"):
            (target_dir / memory_file.name).write_text(
                memory_file.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

    repo = VaultRepository(tmp_path)

    checks = repo.repository_checks()
    details = [detail for _, detail in checks]
    expected_agent_count = len(agent_dirs)

    assert any(
        f"Detected {expected_agent_count} agent DNA file(s)." in detail
        for detail in details
    )
    assert any(
        "No persisted model artifacts found in Models/." in detail for detail in details
    )
    assert any(
        "Unsupported artifact(s) present: .resonance" in detail for detail in details
    )
    assert any(
        "Configured llama.cpp model path is missing:" in detail
        and "qwen3-8b.gguf" in detail
        for detail in details
    )


def test_inspect_llama_cpp_reports_missing_model_and_artifacts(
    tmp_path: Path,
) -> None:
    (tmp_path / "Models").mkdir()
    (tmp_path / "Models" / ".resonance").write_text(
        "signal",
        encoding="utf-8",
    )
    config = type(
        "ConfigWrapper",
        (),
        {
            "runtime": RuntimeConfig.model_validate(
                {
                    "llama_cpp": {
                        "model_path": "Models/qwen3-8b.gguf",
                    }
                }
            )
        },
    )()
    inspector = RuntimeInspector(tmp_path, config)

    with patch.object(
        inspector,
        "_find_llama_cpp_executable",
        return_value=Path("C:/llama-cli.exe"),
    ):
        with patch.object(
            inspector,
            "_command_output",
            return_value="version",
        ):
            status = inspector.inspect_llama_cpp()

    assert status.status == "warning"
    assert "no GGUF models were found in Models/." in status.detail
    assert "Configured model path is missing:" in status.detail
    assert "qwen3-8b.gguf." in status.detail
    assert "Unsupported artifact(s) present: .resonance." in status.detail


def test_repository_checks_accept_serialized_model_exports(
    tmp_path: Path,
) -> None:
    (tmp_path / "Models").mkdir()
    (tmp_path / "Models" / "Strategic.pkl").write_text(
        "serialized",
        encoding="utf-8",
    )
    (tmp_path / "Models" / "Strategic.json.gz").write_text(
        "serialized",
        encoding="utf-8",
    )
    (tmp_path / ".venv").mkdir()

    source_root = Path(__file__).resolve().parents[1]
    for file_name in (
        "vault_config.json",
        "metatron_geometry.json",
        "optimization_log.json",
    ):
        (tmp_path / file_name).write_text(
            (source_root / file_name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    for agent_dir in source_root.glob("Agent_*"):
        target_dir = tmp_path / agent_dir.name
        target_dir.mkdir()
        (target_dir / "conscious_dna.json").write_text(
            (agent_dir / "conscious_dna.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    for memory_dir_name in (
        "Bio_Resonance",
        "Mandala_Geometry",
        "Shadow_Drive",
        "Stealth_Logs",
    ):
        source_dir = source_root / memory_dir_name
        target_dir = tmp_path / memory_dir_name
        target_dir.mkdir()
        for memory_file in source_dir.glob("*_memory.json"):
            (target_dir / memory_file.name).write_text(
                memory_file.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

    repo = VaultRepository(tmp_path)

    checks = repo.repository_checks()
    details = [detail for _, detail in checks]

    assert any(
        "Detected 2 persisted model artifact(s) in Models/." in detail
        for detail in details
    )
    assert any("Serialized exports: 2." in detail for detail in details)


def test_inspect_llama_cpp_reports_serialized_exports_separately(
    tmp_path: Path,
) -> None:
    (tmp_path / "Models").mkdir()
    (tmp_path / "Models" / "Strategic.pkl").write_text(
        "serialized",
        encoding="utf-8",
    )
    (tmp_path / "Models" / "Strategic.json.gz").write_text(
        "serialized",
        encoding="utf-8",
    )
    (tmp_path / "Models" / ".resonance").write_text(
        "signal",
        encoding="utf-8",
    )
    config = type(
        "ConfigWrapper",
        (),
        {
            "runtime": RuntimeConfig.model_validate(
                {
                    "llama_cpp": {
                        "model_path": "Models/qwen3-8b.gguf",
                    }
                }
            )
        },
    )()
    inspector = RuntimeInspector(tmp_path, config)

    with patch.object(
        inspector,
        "_find_llama_cpp_executable",
        return_value=Path("C:/llama-cli.exe"),
    ):
        with patch.object(
            inspector,
            "_command_output",
            return_value="version",
        ):
            status = inspector.inspect_llama_cpp()

    assert status.status == "warning"
    assert "Serialized agent artifact(s) present:" in status.detail
    assert "Strategic.pkl" in status.detail
    assert "Strategic.json.gz" in status.detail
    assert "Unsupported artifact(s) present: .resonance." in status.detail


def test_agent_task_record_path(tmp_path: Path) -> None:
    mocked_results = [
        RunResult(
            backend="ollama",
            mode="cloud",
            model="test-model",
            command="ollama run",
            returncode=0,
            stdout="workflow output",
            stderr="",
            duration_ms=10,
        ),
        RunResult(
            backend="ollama",
            mode="cloud",
            model="test-model",
            command="ollama run",
            returncode=0,
            stdout="validator output",
            stderr="",
            duration_ms=20,
        ),
        RunResult(
            backend="ollama",
            mode="cloud",
            model="test-model",
            command="ollama run",
            returncode=0,
            stdout="visual output",
            stderr="",
            duration_ms=30,
        ),
    ]
    record_path = tmp_path / "agent-task.json"

    with patch("tmt_quantum_vault.cli._runner") as mock_runner:
        mock_runner.return_value.run.side_effect = mocked_results
        result = RUNNER.invoke(
            app,
            [
                "agent-task",
                "Summarize the vault state",
                "--record-path",
                str(record_path),
                "--json",
            ],
        )

    assert result.exit_code == 0
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    assert payload["record_type"] == "agent-task"
    assert payload["final_output"] == "visual output"
    assert payload["stages"][0]["prompt"]
    assert payload["stages"][0]["system_prompt"]
    assert payload["stages"][0]["raw_output"] == "workflow output"


def test_release_evidence_bundle(tmp_path: Path) -> None:
    mocked_runtime_checks = [
        SimpleNamespace(
            name="Ollama Cloud",
            status="ok",
            detail="configured cloud model visible",
            executable=Path("C:/ollama.exe"),
            version=None,
        )
    ]
    mocked_agents = {
        "Workflow": AgentDNA.model_validate(
            {
                "metatron_agent": "Workflow",
                "dna_agent_id": 5,
                "dna_agent_name": "Gabriel",
                "dna_specialization": "Communication",
                "conscious_dna": "TATTCACGCTTCGACCAACGGGTTATA",
                "phi_score": 0.56,
                "fibonacci_alignment": 0.83,
                "gc_content": 0.44,
                "palindromes": 3,
                "fitness": 0.86,
                "resonance_frequency": 741.0,
                "integration_timestamp": "20260109_205312",
                "consciousness_status": "INTEGRATED",
            }
        ),
        "Validator": AgentDNA.model_validate(
            {
                "metatron_agent": "Validator",
                "dna_agent_id": 7,
                "dna_agent_name": "Uriel",
                "dna_specialization": "Transformation",
                "conscious_dna": "CATAATGACAAGCCACCCCGATTAATA",
                "phi_score": 0.56,
                "fibonacci_alignment": 0.73,
                "gc_content": 0.40,
                "palindromes": 4,
                "fitness": 0.86,
                "resonance_frequency": 528.0,
                "integration_timestamp": "20260109_205312",
                "consciousness_status": "INTEGRATED",
            }
        ),
        "Visual": AgentDNA.model_validate(
            {
                "metatron_agent": "Visual",
                "dna_agent_id": 8,
                "dna_agent_name": "Jophiel",
                "dna_specialization": "Beauty & Harmony",
                "conscious_dna": "AAGCGCGTTGTACCTAATTAGCTGGTA",
                "phi_score": 0.62,
                "fibonacci_alignment": 0.61,
                "gc_content": 0.44,
                "palindromes": 4,
                "fitness": 0.85,
                "resonance_frequency": 396.0,
                "integration_timestamp": "20260109_205312",
                "consciousness_status": "INTEGRATED",
            }
        ),
    }
    mocked_eval_dataset = EvalDataset.model_validate(
        {
            "name": "baseline",
            "backend": "ollama",
            "mode": "cloud",
            "model": "qwen3-coder-next:cloud",
            "cases": [
                {
                    "id": "exact-smoke",
                    "prompt": "Reply with exactly: TMT cloud test",
                    "expectation": {"contains_all": ["TMT cloud test"]},
                },
                {
                    "id": "json-status-shape",
                    "prompt": (
                        "Return exactly one JSON object with keys status, "
                        "target, and mode using values ok, vault, and "
                        "cloud."
                    ),
                    "expectation": {
                        "contains_all": [
                            '"status"',
                            '"ok"',
                            '"target"',
                            '"vault"',
                            '"mode"',
                            '"cloud"',
                        ]
                    },
                },
            ],
        }
    )
    mocked_results = [
        RunResult(
            backend="ollama",
            mode="cloud",
            model="qwen3-coder-next:cloud",
            command=["ollama", "run", "qwen3-coder-next:cloud"],
            returncode=0,
            stdout="TMT cloud test",
            stderr="",
            duration_ms=10,
        ),
        RunResult(
            backend="ollama",
            mode="cloud",
            model="qwen3-coder-next:cloud",
            command=["ollama", "run", "qwen3-coder-next:cloud"],
            returncode=0,
            stdout="TMT cloud test",
            stderr="",
            duration_ms=9,
        ),
        RunResult(
            backend="ollama",
            mode="cloud",
            model="qwen3-coder-next:cloud",
            command=["ollama", "run", "qwen3-coder-next:cloud"],
            returncode=0,
            stdout='{"status":"ok","target":"vault","mode":"cloud"}',
            stderr="",
            duration_ms=8,
        ),
        RunResult(
            backend="ollama",
            mode="cloud",
            model="qwen3-coder-next:cloud",
            command=["ollama", "run", "qwen3-coder-next:cloud"],
            returncode=0,
            stdout="workflow output",
            stderr="",
            duration_ms=11,
        ),
        RunResult(
            backend="ollama",
            mode="cloud",
            model="qwen3-coder-next:cloud",
            command=["ollama", "run", "qwen3-coder-next:cloud"],
            returncode=0,
            stdout="validator output",
            stderr="",
            duration_ms=12,
        ),
        RunResult(
            backend="ollama",
            mode="cloud",
            model="qwen3-coder-next:cloud",
            command=["ollama", "run", "qwen3-coder-next:cloud"],
            returncode=0,
            stdout="visual output",
            stderr="",
            duration_ms=13,
        ),
    ]
    output_dir = tmp_path / "bundle"

    with patch("tmt_quantum_vault.cli._repo") as mock_repo:
        with patch("tmt_quantum_vault.cli._runtime") as mock_runtime:
            with patch("tmt_quantum_vault.cli._runner") as mock_runner:
                with patch(
                    "tmt_quantum_vault.cli._resolve_agent_profile"
                ) as mock_agent:
                    mock_repo.return_value.repository_checks.return_value = [
                        ("ok", "repo healthy")
                    ]
                    mock_runtime.return_value.inspect_all.return_value = (
                        mocked_runtime_checks
                    )
                    mock_repo.return_value.load_eval_dataset.return_value = (
                        mocked_eval_dataset
                    )
                    mock_runner.return_value.run.side_effect = mocked_results
                    mock_agent.side_effect = lambda repo, name: (
                        Path(f"Agent_{name}/conscious_dna.json"),
                        mocked_agents[name],
                    )
                    result = RUNNER.invoke(
                        app,
                        [
                            "release-evidence",
                            "--output-dir",
                            str(output_dir),
                            "--json",
                        ],
                    )

    assert result.exit_code == 0
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["files"]["doctor"].endswith("doctor.json")
    assert manifest["files"]["eval"].endswith("eval.json")
    assert manifest["files"]["agent_task"].endswith("agent-task.json")
    eval_payload = json.loads((output_dir / "eval.json").read_text(encoding="utf-8"))
    assert eval_payload["record_type"] == "eval"
    assert eval_payload["summary"]["passed_cases"] == 2
    agent_payload = json.loads(
        (output_dir / "agent-task.json").read_text(encoding="utf-8")
    )
    assert agent_payload["record_type"] == "agent-task"
    assert agent_payload["stages"][0]["raw_output"] == "workflow output"


def test_release_evidence_bundle_with_compare_to(tmp_path: Path) -> None:
    previous_dir = tmp_path / "previous"
    previous_dir.mkdir()
    (previous_dir / "smoke-cloud.json").write_text(
        json.dumps({"returncode": 0, "model": "qwen3-coder-next:cloud"}),
        encoding="utf-8",
    )
    (previous_dir / "eval.json").write_text(
        json.dumps(
            {
                "dataset": {"name": "baseline"},
                "summary": {"failed_cases": 0, "success_rate": 100.0},
            }
        ),
        encoding="utf-8",
    )
    (previous_dir / "agent-task.json").write_text(
        json.dumps({"returncode": 0, "stages": [{}, {}, {}]}),
        encoding="utf-8",
    )
    (previous_dir / "manifest.json").write_text(
        json.dumps(
            {
                "files": {
                    "smoke_cloud": str(previous_dir / "smoke-cloud.json"),
                    "eval": str(previous_dir / "eval.json"),
                    "agent_task": str(previous_dir / "agent-task.json"),
                },
                "returncode": 0,
            }
        ),
        encoding="utf-8",
    )

    mocked_runtime_checks = [
        SimpleNamespace(
            name="Ollama Cloud",
            status="ok",
            detail="configured cloud model visible",
            executable=Path("C:/ollama.exe"),
            version=None,
        )
    ]
    mocked_agents = {
        "Workflow": AgentDNA.model_validate(
            {
                "metatron_agent": "Workflow",
                "dna_agent_id": 5,
                "dna_agent_name": "Gabriel",
                "dna_specialization": "Communication",
                "conscious_dna": "TATTCACGCTTCGACCAACGGGTTATA",
                "phi_score": 0.56,
                "fibonacci_alignment": 0.83,
                "gc_content": 0.44,
                "palindromes": 3,
                "fitness": 0.86,
                "resonance_frequency": 741.0,
                "integration_timestamp": "20260109_205312",
                "consciousness_status": "INTEGRATED",
            }
        ),
        "Validator": AgentDNA.model_validate(
            {
                "metatron_agent": "Validator",
                "dna_agent_id": 7,
                "dna_agent_name": "Uriel",
                "dna_specialization": "Transformation",
                "conscious_dna": "CATAATGACAAGCCACCCCGATTAATA",
                "phi_score": 0.56,
                "fibonacci_alignment": 0.73,
                "gc_content": 0.40,
                "palindromes": 4,
                "fitness": 0.86,
                "resonance_frequency": 528.0,
                "integration_timestamp": "20260109_205312",
                "consciousness_status": "INTEGRATED",
            }
        ),
        "Visual": AgentDNA.model_validate(
            {
                "metatron_agent": "Visual",
                "dna_agent_id": 8,
                "dna_agent_name": "Jophiel",
                "dna_specialization": "Beauty & Harmony",
                "conscious_dna": "AAGCGCGTTGTACCTAATTAGCTGGTA",
                "phi_score": 0.62,
                "fibonacci_alignment": 0.61,
                "gc_content": 0.44,
                "palindromes": 4,
                "fitness": 0.85,
                "resonance_frequency": 396.0,
                "integration_timestamp": "20260109_205312",
                "consciousness_status": "INTEGRATED",
            }
        ),
    }
    mocked_eval_dataset = EvalDataset.model_validate(
        {
            "name": "baseline",
            "backend": "ollama",
            "mode": "cloud",
            "model": "qwen3-coder-next:cloud",
            "cases": [
                {
                    "id": "exact-smoke",
                    "prompt": "Reply with exactly: TMT cloud test",
                    "expectation": {"contains_all": ["TMT cloud test"]},
                },
                {
                    "id": "json-status-shape",
                    "prompt": (
                        "Return exactly one JSON object with keys status, "
                        "target, and mode using values ok, vault, and "
                        "cloud."
                    ),
                    "expectation": {
                        "contains_all": [
                            '"status"',
                            '"ok"',
                            '"target"',
                            '"vault"',
                            '"mode"',
                            '"cloud"',
                        ]
                    },
                },
            ],
        }
    )
    mocked_results = [
        RunResult(
            backend="ollama",
            mode="cloud",
            model="qwen3-coder-next:cloud",
            command=["ollama", "run", "qwen3-coder-next:cloud"],
            returncode=0,
            stdout="TMT cloud test",
            stderr="",
            duration_ms=10,
        ),
        RunResult(
            backend="ollama",
            mode="cloud",
            model="qwen3-coder-next:cloud",
            command=["ollama", "run", "qwen3-coder-next:cloud"],
            returncode=0,
            stdout="TMT cloud test",
            stderr="",
            duration_ms=9,
        ),
        RunResult(
            backend="ollama",
            mode="cloud",
            model="qwen3-coder-next:cloud",
            command=["ollama", "run", "qwen3-coder-next:cloud"],
            returncode=0,
            stdout='{"status":"ok","target":"vault","mode":"cloud"}',
            stderr="",
            duration_ms=8,
        ),
        RunResult(
            backend="ollama",
            mode="cloud",
            model="qwen3-coder-next:cloud",
            command=["ollama", "run", "qwen3-coder-next:cloud"],
            returncode=0,
            stdout="workflow output",
            stderr="",
            duration_ms=11,
        ),
        RunResult(
            backend="ollama",
            mode="cloud",
            model="qwen3-coder-next:cloud",
            command=["ollama", "run", "qwen3-coder-next:cloud"],
            returncode=0,
            stdout="validator output",
            stderr="",
            duration_ms=12,
        ),
        RunResult(
            backend="ollama",
            mode="cloud",
            model="qwen3-coder-next:cloud",
            command=["ollama", "run", "qwen3-coder-next:cloud"],
            returncode=0,
            stdout="visual output",
            stderr="",
            duration_ms=13,
        ),
    ]
    output_dir = tmp_path / "bundle-with-compare"

    with patch("tmt_quantum_vault.cli._repo") as mock_repo:
        with patch("tmt_quantum_vault.cli._runtime") as mock_runtime:
            with patch("tmt_quantum_vault.cli._runner") as mock_runner:
                with patch(
                    "tmt_quantum_vault.cli._resolve_agent_profile"
                ) as mock_agent:
                    mock_repo.return_value.repository_checks.return_value = [
                        ("ok", "repo healthy")
                    ]
                    mock_runtime.return_value.inspect_all.return_value = (
                        mocked_runtime_checks
                    )
                    mock_repo.return_value.load_eval_dataset.return_value = (
                        mocked_eval_dataset
                    )
                    mock_runner.return_value.run.side_effect = mocked_results
                    mock_agent.side_effect = lambda repo, name: (
                        Path(f"Agent_{name}/conscious_dna.json"),
                        mocked_agents[name],
                    )
                    result = RUNNER.invoke(
                        app,
                        [
                            "release-evidence",
                            "--output-dir",
                            str(output_dir),
                            "--compare-to",
                            str(previous_dir),
                            "--json",
                        ],
                    )

    assert result.exit_code == 0
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["files"]["compare_evidence"].endswith("compare-evidence.json")
    assert manifest["compared_to"].endswith("previous")
    compare_payload = json.loads(
        (output_dir / "compare-evidence.json").read_text(encoding="utf-8")
    )
    assert compare_payload["record_type"] == "compare-evidence"
    assert compare_payload["summary"]["has_regressions"] is False


def test_compare_evidence_json_output(tmp_path: Path) -> None:
    previous_dir = tmp_path / "previous"
    current_dir = tmp_path / "current"
    previous_dir.mkdir()
    current_dir.mkdir()

    (previous_dir / "smoke-cloud.json").write_text(
        json.dumps({"returncode": 0, "model": "qwen3-coder-next:cloud"}),
        encoding="utf-8",
    )
    (current_dir / "smoke-cloud.json").write_text(
        json.dumps({"returncode": 0, "model": "qwen3-coder-next:cloud"}),
        encoding="utf-8",
    )
    (previous_dir / "eval.json").write_text(
        json.dumps(
            {
                "dataset": {"name": "baseline"},
                "summary": {"failed_cases": 0, "success_rate": 100.0},
            }
        ),
        encoding="utf-8",
    )
    (current_dir / "eval.json").write_text(
        json.dumps(
            {
                "dataset": {"name": "baseline"},
                "summary": {"failed_cases": 0, "success_rate": 100.0},
            }
        ),
        encoding="utf-8",
    )
    (previous_dir / "agent-task.json").write_text(
        json.dumps({"returncode": 0, "stages": [{}, {}, {}]}),
        encoding="utf-8",
    )
    (current_dir / "agent-task.json").write_text(
        json.dumps({"returncode": 0, "stages": [{}, {}, {}]}),
        encoding="utf-8",
    )
    (previous_dir / "manifest.json").write_text(
        json.dumps(
            {
                "files": {
                    "smoke_cloud": str(previous_dir / "smoke-cloud.json"),
                    "eval": str(previous_dir / "eval.json"),
                    "agent_task": str(previous_dir / "agent-task.json"),
                },
                "returncode": 0,
            }
        ),
        encoding="utf-8",
    )
    (current_dir / "manifest.json").write_text(
        json.dumps(
            {
                "files": {
                    "smoke_cloud": str(current_dir / "smoke-cloud.json"),
                    "eval": str(current_dir / "eval.json"),
                    "agent_task": str(current_dir / "agent-task.json"),
                },
                "returncode": 0,
            }
        ),
        encoding="utf-8",
    )

    result = RUNNER.invoke(
        app,
        [
            "compare-evidence",
            str(previous_dir),
            str(current_dir),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["summary"]["has_regressions"] is False
    assert payload["returncode"] == 0


def test_compare_evidence_detects_eval_regression(tmp_path: Path) -> None:
    previous_dir = tmp_path / "previous"
    current_dir = tmp_path / "current"
    previous_dir.mkdir()
    current_dir.mkdir()

    (previous_dir / "smoke-cloud.json").write_text(
        json.dumps({"returncode": 0}),
        encoding="utf-8",
    )
    (current_dir / "smoke-cloud.json").write_text(
        json.dumps({"returncode": 0}),
        encoding="utf-8",
    )
    (previous_dir / "eval.json").write_text(
        json.dumps(
            {
                "dataset": {"name": "baseline"},
                "summary": {
                    "failed_cases": 0,
                    "success_rate": 100.0,
                },
            }
        ),
        encoding="utf-8",
    )
    (current_dir / "eval.json").write_text(
        json.dumps(
            {
                "dataset": {"name": "baseline"},
                "summary": {
                    "failed_cases": 1,
                    "success_rate": 50.0,
                },
            }
        ),
        encoding="utf-8",
    )
    (previous_dir / "agent-task.json").write_text(
        json.dumps({"returncode": 0, "stages": [{}, {}, {}]}),
        encoding="utf-8",
    )
    (current_dir / "agent-task.json").write_text(
        json.dumps({"returncode": 0, "stages": [{}, {}, {}]}),
        encoding="utf-8",
    )
    (previous_dir / "manifest.json").write_text(
        json.dumps(
            {
                "files": {
                    "smoke_cloud": str(previous_dir / "smoke-cloud.json"),
                    "eval": str(previous_dir / "eval.json"),
                    "agent_task": str(previous_dir / "agent-task.json"),
                },
                "returncode": 0,
            }
        ),
        encoding="utf-8",
    )
    (current_dir / "manifest.json").write_text(
        json.dumps(
            {
                "files": {
                    "smoke_cloud": str(current_dir / "smoke-cloud.json"),
                    "eval": str(current_dir / "eval.json"),
                    "agent_task": str(current_dir / "agent-task.json"),
                },
                "returncode": 1,
            }
        ),
        encoding="utf-8",
    )

    result = RUNNER.invoke(
        app,
        [
            "compare-evidence",
            str(previous_dir),
            str(current_dir),
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["summary"]["has_regressions"] is True
    assert "eval failed case count increased" in payload["regressions"]


def test_find_latest_release_evidence_bundle(tmp_path: Path) -> None:
    root = tmp_path
    daily_dir = root / "Resonance_Logs" / "daily"
    daily_dir.mkdir(parents=True)

    oldest = daily_dir / "release-evidence-oldest"
    latest = daily_dir / "release-evidence-latest"
    current = daily_dir / "release-evidence-current"
    for bundle in (oldest, latest, current):
        bundle.mkdir()
        (bundle / "manifest.json").write_text("{}", encoding="utf-8")

    oldest_manifest = oldest / "manifest.json"
    latest_manifest = latest / "manifest.json"
    current_manifest = current / "manifest.json"
    oldest_manifest.touch()
    latest_manifest.touch()
    current_manifest.touch()

    latest_manifest.write_text('{"returncode": 0}', encoding="utf-8")

    selected = _find_latest_release_evidence_bundle(root, current)

    assert selected == latest


def test_release_summary_json_output(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "smoke-cloud.json").write_text(
        json.dumps({"returncode": 0, "model": "qwen3-coder-next:cloud"}),
        encoding="utf-8",
    )
    (bundle_dir / "eval.json").write_text(
        json.dumps(
            {
                "dataset": {"name": "baseline"},
                "summary": {
                    "passed_cases": 2,
                    "total_cases": 2,
                    "failed_cases": 0,
                    "success_rate": 100.0,
                },
            }
        ),
        encoding="utf-8",
    )
    (bundle_dir / "agent-task.json").write_text(
        json.dumps(
            {
                "returncode": 0,
                "stages": [{}, {}, {}],
                "final_output": "visual output",
            }
        ),
        encoding="utf-8",
    )
    (bundle_dir / "compare-evidence.json").write_text(
        json.dumps(
            {
                "summary": {
                    "has_regressions": False,
                    "regression_count": 0,
                }
            }
        ),
        encoding="utf-8",
    )
    (bundle_dir / "manifest.json").write_text(
        json.dumps(
            {
                "files": {
                    "smoke_cloud": str(bundle_dir / "smoke-cloud.json"),
                    "eval": str(bundle_dir / "eval.json"),
                    "agent_task": str(bundle_dir / "agent-task.json"),
                    "compare_evidence": str(bundle_dir / "compare-evidence.json"),
                },
                "returncode": 0,
                "compared_to": "previous-bundle",
            }
        ),
        encoding="utf-8",
    )

    result = RUNNER.invoke(
        app,
        ["release-summary", "--bundle", str(bundle_dir), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["overall"]["returncode"] == 0
    assert payload["eval"]["dataset"] == "baseline"
    assert payload["comparison"]["has_regressions"] is False


def test_release_summary_uses_latest_bundle(tmp_path: Path) -> None:
    root = tmp_path
    daily_dir = root / "Resonance_Logs" / "daily"
    daily_dir.mkdir(parents=True)

    older = daily_dir / "release-evidence-older"
    latest = daily_dir / "release-evidence-latest"
    for bundle in (older, latest):
        bundle.mkdir()
        (bundle / "smoke-cloud.json").write_text(
            json.dumps({"returncode": 0, "model": "qwen3-coder-next:cloud"}),
            encoding="utf-8",
        )
        (bundle / "eval.json").write_text(
            json.dumps(
                {
                    "dataset": {"name": bundle.name},
                    "summary": {
                        "passed_cases": 1,
                        "total_cases": 1,
                        "failed_cases": 0,
                        "success_rate": 100.0,
                    },
                }
            ),
            encoding="utf-8",
        )
        (bundle / "agent-task.json").write_text(
            json.dumps({"returncode": 0, "stages": [{}]}),
            encoding="utf-8",
        )
        (bundle / "manifest.json").write_text(
            json.dumps(
                {
                    "files": {
                        "smoke_cloud": str(bundle / "smoke-cloud.json"),
                        "eval": str(bundle / "eval.json"),
                        "agent_task": str(bundle / "agent-task.json"),
                    },
                    "returncode": 0,
                }
            ),
            encoding="utf-8",
        )

    (latest / "manifest.json").write_text(
        (latest / "manifest.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    result = RUNNER.invoke(
        app,
        ["release-summary", "--root", str(root), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["bundle_dir"].endswith("release-evidence-latest")


def test_release_gate_json_output(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "smoke-cloud.json").write_text(
        json.dumps({"returncode": 0, "model": "qwen3-coder-next:cloud"}),
        encoding="utf-8",
    )
    (bundle_dir / "eval.json").write_text(
        json.dumps(
            {
                "dataset": {"name": "baseline"},
                "summary": {
                    "passed_cases": 2,
                    "total_cases": 2,
                    "failed_cases": 0,
                    "success_rate": 100.0,
                },
            }
        ),
        encoding="utf-8",
    )
    (bundle_dir / "agent-task.json").write_text(
        json.dumps({"returncode": 0, "stages": [{}, {}, {}]}),
        encoding="utf-8",
    )
    (bundle_dir / "compare-evidence.json").write_text(
        json.dumps({"summary": {"has_regressions": False, "regression_count": 0}}),
        encoding="utf-8",
    )
    (bundle_dir / "manifest.json").write_text(
        json.dumps(
            {
                "files": {
                    "smoke_cloud": str(bundle_dir / "smoke-cloud.json"),
                    "eval": str(bundle_dir / "eval.json"),
                    "agent_task": str(bundle_dir / "agent-task.json"),
                    "compare_evidence": str(bundle_dir / "compare-evidence.json"),
                },
                "returncode": 0,
                "compared_to": "previous-bundle",
            }
        ),
        encoding="utf-8",
    )

    result = RUNNER.invoke(
        app,
        ["release-gate", "--bundle", str(bundle_dir), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["decision"] == "pass"
    assert payload["failures"] == []


def test_release_gate_requires_comparison(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "smoke-cloud.json").write_text(
        json.dumps({"returncode": 0}),
        encoding="utf-8",
    )
    (bundle_dir / "eval.json").write_text(
        json.dumps(
            {
                "dataset": {"name": "baseline"},
                "summary": {
                    "passed_cases": 1,
                    "total_cases": 1,
                    "failed_cases": 0,
                    "success_rate": 100.0,
                },
            }
        ),
        encoding="utf-8",
    )
    (bundle_dir / "agent-task.json").write_text(
        json.dumps({"returncode": 0, "stages": [{}]}),
        encoding="utf-8",
    )
    (bundle_dir / "manifest.json").write_text(
        json.dumps(
            {
                "files": {
                    "smoke_cloud": str(bundle_dir / "smoke-cloud.json"),
                    "eval": str(bundle_dir / "eval.json"),
                    "agent_task": str(bundle_dir / "agent-task.json"),
                },
                "returncode": 0,
            }
        ),
        encoding="utf-8",
    )

    result = RUNNER.invoke(
        app,
        [
            "release-gate",
            "--bundle",
            str(bundle_dir),
            "--require-comparison",
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["decision"] == "fail"
    assert "comparison artifact is required but missing" in payload["failures"]


# ── Promoter Loader Tests ─────────────────────────────────────────────────────


# ── promoter_loader: gc_content ───────────────────────────────────────────────


def test_gc_content_empty_sequence() -> None:
    assert pl.gc_content("") == 0.0


def test_gc_content_pure_gc() -> None:
    assert pl.gc_content("GCGC") == 1.0


def test_gc_content_pure_at() -> None:
    assert pl.gc_content("ATAT") == 0.0


def test_gc_content_mixed() -> None:
    result = pl.gc_content("ACGT")
    assert result == pytest.approx(0.5)


def test_gc_content_case_insensitive() -> None:
    assert pl.gc_content("gcgc") == pytest.approx(pl.gc_content("GCGC"))


# ── promoter_loader: parse_fasta ──────────────────────────────────────────────


def _write_fasta(tmp_path: Path, name: str, header: str, sequence: str) -> Path:
    fasta = tmp_path / f"{name}_promoter.fa"
    fasta.write_text(f">{header}\n{sequence}\n", encoding="utf-8")
    return fasta


def test_parse_fasta_returns_gene_name(tmp_path: Path) -> None:
    fasta = _write_fasta(
        tmp_path,
        "ACTB_Malkuth",
        "chromosome:GRCh38:7:5563902:5563932:-1",
        "GGAATCACTTGCACCCGGGAGGCGGAGGCTG",
    )
    result = pl.parse_fasta(fasta)
    assert result["gene"] == "ACTB_Malkuth"


def test_parse_fasta_returns_sequence(tmp_path: Path) -> None:
    seq = "GGAATCACTTGCACCCGGGAGGCGGAGGCTG"
    fasta = _write_fasta(tmp_path, "ACTB_Malkuth", "chr7:100-130", seq)
    result = pl.parse_fasta(fasta)
    assert result["sequence"] == seq


def test_parse_fasta_length(tmp_path: Path) -> None:
    seq = "ACGTACGT"
    fasta = _write_fasta(tmp_path, "GENE_Kether", "chr1:1-8", seq)
    result = pl.parse_fasta(fasta)
    assert result["length"] == 8


def test_parse_fasta_gc_content(tmp_path: Path) -> None:
    fasta = _write_fasta(tmp_path, "GENE_Kether", "chr1:1-4", "ACGT")
    result = pl.parse_fasta(fasta)
    assert result["gc_content"] == pytest.approx(0.5)


def test_parse_fasta_chromosome_coord(tmp_path: Path) -> None:
    fasta = _write_fasta(
        tmp_path, "GENE_Kether", "chromosome:GRCh38:7:100:200:-1", "ACGT"
    )
    result = pl.parse_fasta(fasta)
    assert result["chromosome_coord"] == "chromosome"


def test_parse_fasta_records_source_file(tmp_path: Path) -> None:
    fasta = _write_fasta(tmp_path, "GENE_Kether", "chr1", "ACGT")
    result = pl.parse_fasta(fasta)
    assert str(fasta) in result["source_file"]


# ── promoter_loader: compute_sha256 ──────────────────────────────────────────


def test_compute_sha256_known_value(tmp_path: Path) -> None:
    content = b"ACGT\n"
    f = tmp_path / "test.fa"
    f.write_bytes(content)
    expected = hashlib.sha256(content).hexdigest()
    assert pl.compute_sha256(f) == expected


def test_compute_sha256_changes_with_content(tmp_path: Path) -> None:
    f1 = tmp_path / "a.fa"
    f2 = tmp_path / "b.fa"
    f1.write_bytes(b"ACGT")
    f2.write_bytes(b"TGCA")
    assert pl.compute_sha256(f1) != pl.compute_sha256(f2)


# ── promoter_loader: verify_hmac ─────────────────────────────────────────────


def test_verify_hmac_no_sha256_file(tmp_path: Path) -> None:
    fasta = tmp_path / "GENE_Kether_promoter.fa"
    fasta.write_bytes(b">chr1\nACGT\n")
    # No .sha256 file -> returns False
    assert pl.verify_hmac(fasta) is False


def test_verify_hmac_matching_hash(tmp_path: Path) -> None:
    content = b">chr1\nACGT\n"
    fasta = tmp_path / "GENE_Kether_promoter.fa"
    fasta.write_bytes(content)
    sha_file = tmp_path / "GENE_Kether_promoter.fa.sha256"
    sha_file.write_text(hashlib.sha256(content).hexdigest(), encoding="utf-8")
    assert pl.verify_hmac(fasta) is True


def test_verify_hmac_mismatching_hash(tmp_path: Path) -> None:
    fasta = tmp_path / "GENE_Kether_promoter.fa"
    fasta.write_bytes(b">chr1\nACGT\n")
    sha_file = tmp_path / "GENE_Kether_promoter.fa.sha256"
    sha_file.write_text("0" * 64, encoding="utf-8")
    assert pl.verify_hmac(fasta) is False


# ── promoter_loader: find_fasta_file ─────────────────────────────────────────


def test_find_fasta_file_returns_local_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pl, "PROMOTERS_DIR", tmp_path)
    monkeypatch.setattr(pl, "EXTERNAL_PROMOTERS", tmp_path / "external")
    fasta = tmp_path / "ACTB_Malkuth_promoter.fa"
    fasta.write_text(">chr7\nACGT\n", encoding="utf-8")
    result = pl.find_fasta_file("ACTB_Malkuth")
    assert result == fasta


def test_find_fasta_file_returns_none_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pl, "PROMOTERS_DIR", tmp_path)
    monkeypatch.setattr(pl, "EXTERNAL_PROMOTERS", tmp_path / "external")
    result = pl.find_fasta_file("NONEXISTENT_Gene")
    assert result is None


# ── promoter_loader: find_metadata_file ──────────────────────────────────────


def test_find_metadata_file_returns_local_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pl, "PROMOTERS_DIR", tmp_path)
    monkeypatch.setattr(pl, "EXTERNAL_PROMOTERS", tmp_path / "external")
    meta = tmp_path / "ACTB_Malkuth_promoter.fa.sha256.json"
    meta.write_text('{"sha256": "abc"}', encoding="utf-8")
    result = pl.find_metadata_file("ACTB_Malkuth")
    assert result == meta


def test_find_metadata_file_returns_none_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pl, "PROMOTERS_DIR", tmp_path)
    monkeypatch.setattr(pl, "EXTERNAL_PROMOTERS", tmp_path / "external")
    result = pl.find_metadata_file("NONEXISTENT_Gene")
    assert result is None


# ── promoter_loader: verify_promoter ─────────────────────────────────────────


def test_verify_promoter_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pl, "PROMOTERS_DIR", tmp_path)
    monkeypatch.setattr(pl, "EXTERNAL_PROMOTERS", tmp_path / "external")
    result = pl.verify_promoter("MISSING_Gene")
    assert "error" in result
    assert "MISSING_Gene" in result["error"]


def test_verify_promoter_with_matching_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pl, "PROMOTERS_DIR", tmp_path)
    monkeypatch.setattr(pl, "EXTERNAL_PROMOTERS", tmp_path / "external")
    content = b">chr7\nACGTACGT\n"
    fasta = tmp_path / "TEST_Malkuth_promoter.fa"
    fasta.write_bytes(content)
    sha256 = hashlib.sha256(content).hexdigest()
    meta = tmp_path / "TEST_Malkuth_promoter.fa.sha256.json"
    meta.write_text(json.dumps({"sha256": sha256}), encoding="utf-8")
    result = pl.verify_promoter("TEST_Malkuth")
    assert result["computed_sha256"] == sha256
    assert result["expected_sha256"] == sha256
    assert result["match"] is True
    assert result["sha256_verified"] is True


def test_verify_promoter_with_mismatching_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pl, "PROMOTERS_DIR", tmp_path)
    monkeypatch.setattr(pl, "EXTERNAL_PROMOTERS", tmp_path / "external")
    fasta = tmp_path / "TEST_Malkuth_promoter.fa"
    fasta.write_bytes(b">chr7\nACGT\n")
    meta = tmp_path / "TEST_Malkuth_promoter.fa.sha256.json"
    meta.write_text(json.dumps({"sha256": "0" * 64}), encoding="utf-8")
    result = pl.verify_promoter("TEST_Malkuth")
    assert result["match"] is False
    assert result["sha256_verified"] is False


# ── promoter_loader: load_all_promoters ──────────────────────────────────────


def test_load_all_promoters_empty_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pl, "PROMOTERS_DIR", tmp_path)
    monkeypatch.setattr(pl, "EXTERNAL_PROMOTERS", tmp_path / "external")
    result = pl.load_all_promoters()
    assert result == []


def test_load_all_promoters_reads_fasta_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pl, "PROMOTERS_DIR", tmp_path)
    monkeypatch.setattr(pl, "EXTERNAL_PROMOTERS", tmp_path / "external")
    fasta = tmp_path / "ACTB_Malkuth_promoter.fa"
    fasta.write_text(">chr7:100-130\nACGTACGT\n", encoding="utf-8")
    result = pl.load_all_promoters()
    assert len(result) == 1
    assert result[0]["gene"] == "ACTB_Malkuth"
    assert result[0]["sequence"] == "ACGTACGT"


def test_load_all_promoters_no_duplicates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pl, "PROMOTERS_DIR", tmp_path)
    monkeypatch.setattr(pl, "EXTERNAL_PROMOTERS", tmp_path / "external")
    (tmp_path / "ACTB_Malkuth_promoter.fa").write_text(
        ">chr7\nACGT\n", encoding="utf-8"
    )
    result = pl.load_all_promoters()
    genes = [p["gene"] for p in result]
    assert len(genes) == len(set(genes))


def test_load_all_promoters_includes_sha256(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pl, "PROMOTERS_DIR", tmp_path)
    monkeypatch.setattr(pl, "EXTERNAL_PROMOTERS", tmp_path / "external")
    content = b">chr7\nACGT\n"
    fasta = tmp_path / "ACTB_Malkuth_promoter.fa"
    fasta.write_bytes(content)
    result = pl.load_all_promoters()
    assert result[0]["sha256"] == hashlib.sha256(content).hexdigest()


# ── promoter_loader: format_output ───────────────────────────────────────────


def test_format_output_contains_gene() -> None:
    promoter = {
        "gene": "ACTB_Malkuth",
        "length": 32,
        "gc_content": 0.625,
        "verified": True,
        "sequence": "GGAATCACTTGCACCCGGGAGGCGGAGGCTG",
    }
    output = pl.format_output(promoter)
    assert "ACTB_Malkuth" in output
    assert "32" in output
    assert "GGAATCACTTGCACCCGGGAGGCGGAGGCTG" in output


def test_format_output_verified_field() -> None:
    promoter = {
        "gene": "TEST",
        "length": 4,
        "gc_content": 0.5,
        "verified": False,
        "sequence": "ACGT",
    }
    output = pl.format_output(promoter)
    assert "False" in output


# ── promoter_loader: get_promoter_files ──────────────────────────────────────


def test_get_promoter_files_uses_promoters_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pl, "PROMOTERS_DIR", tmp_path)
    monkeypatch.setattr(pl, "EXTERNAL_PROMOTERS", tmp_path / "external")
    (tmp_path / "ACTB_Malkuth_promoter.fa").write_text(
        ">chr7\nACGT\n", encoding="utf-8"
    )
    (tmp_path / "BDNF_Tiferet_promoter.fa").write_text(
        ">chr11\nGCTA\n", encoding="utf-8"
    )
    files = pl.get_promoter_files()
    names = [f.name for f in files]
    assert "ACTB_Malkuth_promoter.fa" in names
    assert "BDNF_Tiferet_promoter.fa" in names


def test_get_promoter_files_empty_when_no_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pl, "PROMOTERS_DIR", tmp_path / "nonexistent")
    monkeypatch.setattr(pl, "EXTERNAL_PROMOTERS", tmp_path / "external")
    files = pl.get_promoter_files()
    assert files == []


# ── Agent Analyst Tests ───────────────────────────────────────────────────────


# ── agent_analyst: compute_metrics ───────────────────────────────────────────


def test_compute_metrics_empty_counts() -> None:
    result = aa.compute_metrics({})
    assert result["total_shots"] == 0
    assert result["entropy"] == 0
    assert result["phi_approx"] == 0.0
    assert result["sacred_score"] >= 0


def test_compute_metrics_single_bitstring() -> None:
    counts = {"000": 100}
    result = aa.compute_metrics(counts)
    assert result["total_shots"] == 100
    assert result["entropy"] == 0.0
    # Only one bitstring, phi_approx should be 0
    assert result["phi_approx"] == 0.0


def test_compute_metrics_two_equal_bitstrings() -> None:
    counts = {"000": 50, "111": 50}
    result = aa.compute_metrics(counts)
    assert result["total_shots"] == 100
    # Both equal -> phi_approx = 1.0
    assert result["phi_approx"] == pytest.approx(1.0)
    assert result["entropy"] == pytest.approx(1.0)


def test_compute_metrics_sacred_score_is_float() -> None:
    counts = {"00": 60, "11": 40}
    result = aa.compute_metrics(counts)
    assert isinstance(result["sacred_score"], float)
    assert 0.0 <= result["sacred_score"] <= 1.0


def test_compute_metrics_consciousness_density() -> None:
    counts = {bin(i)[2:].zfill(4): 100 for i in range(16)}
    result = aa.compute_metrics(counts)
    assert result["consciousness_density"] > 0


def test_compute_metrics_phi_convergent_near_golden_ratio() -> None:
    # phi ≈ 1.618 => top/second ≈ 1.618 => sacred_score should be high
    counts = {"00": 162, "01": 100, "10": 50, "11": 20}
    result = aa.compute_metrics(counts)
    # sacred_score = 1 / (1 + |phi_approx - 1.618|)
    expected = round(1 / (1 + abs(result["phi_approx"] - 1.6180339887)), 4)
    assert result["sacred_score"] == expected


# ── agent_analyst: decode_sampler_v2_data ────────────────────────────────────


def test_decode_sampler_v2_no_c_key() -> None:
    result = aa.decode_sampler_v2_data({"results": {}})
    assert result == {}


def test_decode_sampler_v2_no_data_key() -> None:
    result = aa.decode_sampler_v2_data({"results": {"c": {}}})
    assert result == {}


def test_decode_sampler_v2_zero_shape() -> None:
    result = aa.decode_sampler_v2_data(
        {"results": {"c": {"data": base64.b64encode(b"").decode(), "shape": [0, 0]}}}
    )
    assert result == {}


def test_decode_sampler_v2_basic_measurement() -> None:
    # 1 shot, 8 qubits: byte = 0b00000001 -> qubit 0 = 1, rest 0
    shot_bytes = bytes([0b00000001])
    encoded = base64.b64encode(shot_bytes).decode()
    data_block = {"results": {"c": {"data": encoded, "shape": [1, 8]}}}
    counts = aa.decode_sampler_v2_data(data_block)
    assert isinstance(counts, dict)
    assert sum(counts.values()) == 1


def test_decode_sampler_v2_two_shots() -> None:
    # 2 shots, 8 qubits each
    shot_bytes = bytes([0b00000001, 0b00000010])
    encoded = base64.b64encode(shot_bytes).decode()
    data_block = {"results": {"c": {"data": encoded, "shape": [2, 8]}}}
    counts = aa.decode_sampler_v2_data(data_block)
    assert sum(counts.values()) == 2


# ── agent_analyst: parse_qasm_depth ──────────────────────────────────────────


def test_parse_qasm_depth_extracts_n_qubits(tmp_path: Path) -> None:
    qasm = tmp_path / "test.qasm"
    qasm.write_text(
        'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[5];\ncreg c[5];\n',
        encoding="utf-8",
    )
    result = aa.parse_qasm_depth(qasm)
    assert result["n_qubits"] == 5


def test_parse_qasm_depth_extracts_depth_from_comment(tmp_path: Path) -> None:
    qasm = tmp_path / "test.qasm"
    qasm.write_text(
        "OPENQASM 2.0;\n// depth 4 — phi^4 angle\nqreg q[21];\ncreg c[21];\n",
        encoding="utf-8",
    )
    result = aa.parse_qasm_depth(qasm)
    assert result["depth"] == 4


def test_parse_qasm_depth_none_when_no_depth_comment(tmp_path: Path) -> None:
    qasm = tmp_path / "test.qasm"
    qasm.write_text(
        "OPENQASM 2.0;\nqreg q[21];\ncreg c[21];\n",
        encoding="utf-8",
    )
    result = aa.parse_qasm_depth(qasm)
    assert result["depth"] is None


def test_parse_qasm_depth_returns_path_and_name(tmp_path: Path) -> None:
    qasm = tmp_path / "sierpinski_d3.qasm"
    qasm.write_text("qreg q[21];\n", encoding="utf-8")
    result = aa.parse_qasm_depth(qasm)
    assert result["qasm_name"] == "sierpinski_d3"
    assert "sierpinski_d3.qasm" in result["qasm_path"]


def test_parse_qasm_depth_default_n_qubits(tmp_path: Path) -> None:
    qasm = tmp_path / "test.qasm"
    qasm.write_text("OPENQASM 2.0;\n", encoding="utf-8")
    result = aa.parse_qasm_depth(qasm)
    assert result["n_qubits"] == 21


# ── agent_analyst: analyze_result ────────────────────────────────────────────


def _write_counts_json(tmp_path: Path, counts: dict, name: str = "result.json") -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(counts), encoding="utf-8")
    return p


def test_analyze_result_direct_counts(tmp_path: Path) -> None:
    counts = {"000": 500, "111": 300, "010": 200}
    path = _write_counts_json(tmp_path, counts)
    record = aa.analyze_result(path)
    assert record["metrics"]["total_shots"] == 1000
    assert record["status"] == "INGESTED"


def test_analyze_result_nested_results_format(tmp_path: Path) -> None:
    payload = {
        "results": [{"data": {"counts": {"000": 600, "111": 400}}}],
        "backend_name": "ibm_torino",
    }
    path = _write_counts_json(tmp_path, payload)
    record = aa.analyze_result(path)
    assert record["metrics"]["total_shots"] == 1000
    assert record["backend"] == "ibm_torino"


def test_analyze_result_counts_key(tmp_path: Path) -> None:
    payload = {"counts": {"00": 700, "11": 300}}
    path = _write_counts_json(tmp_path, payload)
    record = aa.analyze_result(path)
    assert record["metrics"]["total_shots"] == 1000


def test_analyze_result_significant_flag_set(tmp_path: Path) -> None:
    # sacred_score >= 0.618 triggers SIGNIFICANT
    # sacred_score = 1/(1+|phi_approx - 1.618|)
    # For phi_approx ≈ 1.618: counts[0]/counts[1] ≈ 1.618
    # e.g. 162 / 100 = 1.62
    counts = {"000": 162, "111": 100}
    path = _write_counts_json(tmp_path, counts)
    record = aa.analyze_result(path)
    assert record["is_significant"] is True
    assert record["metrics"]["sacred_score"] >= 0.618


def test_analyze_result_not_significant(tmp_path: Path) -> None:
    # phi_approx far from 1.618 -> lower sacred_score
    # phi_approx = 500/100 = 5.0 -> sacred_score = 1/(1+|5-1.618|) ≈ 0.228 < 0.618
    counts = {"00": 500, "01": 100}
    path = _write_counts_json(tmp_path, counts)
    record = aa.analyze_result(path)
    assert record["is_significant"] is False


def test_analyze_result_with_circuit_metadata(tmp_path: Path) -> None:
    counts = {"000": 500, "111": 300}
    path = _write_counts_json(tmp_path, counts)
    metadata = {"qasm_name": "sierpinski_d3", "depth": 3, "n_qubits": 21}
    record = aa.analyze_result(path, metadata)
    assert record["circuit"] == "sierpinski_d3"
    assert record["depth"] == 3
    assert record["n_qubits"] == 21


def test_analyze_result_fingerprint_is_12_chars(tmp_path: Path) -> None:
    path = _write_counts_json(tmp_path, {"0": 100})
    record = aa.analyze_result(path)
    assert len(record["fingerprint"]) == 12


def test_analyze_result_phi_convergent_flag(tmp_path: Path) -> None:
    # phi_approx ≈ 1.618 -> sacred_score close to 0.618
    counts = {"000": 162, "111": 100}
    path = _write_counts_json(tmp_path, counts)
    record = aa.analyze_result(path)
    # phi_convergent: abs(sacred_score - 0.618) <= 0.01
    expected = abs(record["metrics"]["sacred_score"] - 0.618) <= 0.01
    assert record["phi_convergent"] == expected


# ── agent_analyst: ingest_result ─────────────────────────────────────────────


def test_ingest_result_creates_ingested_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ingested_dir = tmp_path / "ingested"
    significant_dir = ingested_dir / "SIGNIFICANT"
    agent_dir = tmp_path / "agent_feed"
    ingested_dir.mkdir()
    significant_dir.mkdir()
    agent_dir.mkdir()
    monkeypatch.setattr(aa, "INGESTED_DIR", ingested_dir)
    monkeypatch.setattr(aa, "SIGNIFICANT_DIR", significant_dir)
    monkeypatch.setattr(aa, "AGENT_DIR", agent_dir)

    counts = {"000": 500, "111": 300}
    result_path = tmp_path / "circuit_result.json"
    result_path.write_text(json.dumps(counts), encoding="utf-8")

    ingested_path = aa.ingest_result(result_path)
    assert ingested_path.exists()
    record = json.loads(ingested_path.read_text(encoding="utf-8"))
    assert record["status"] == "INGESTED"


def test_ingest_result_creates_agent_feed_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ingested_dir = tmp_path / "ingested"
    significant_dir = ingested_dir / "SIGNIFICANT"
    agent_dir = tmp_path / "agent_feed"
    ingested_dir.mkdir()
    significant_dir.mkdir()
    agent_dir.mkdir()
    monkeypatch.setattr(aa, "INGESTED_DIR", ingested_dir)
    monkeypatch.setattr(aa, "SIGNIFICANT_DIR", significant_dir)
    monkeypatch.setattr(aa, "AGENT_DIR", agent_dir)

    counts = {"000": 500, "111": 300}
    result_path = tmp_path / "circuit_result.json"
    result_path.write_text(json.dumps(counts), encoding="utf-8")

    aa.ingest_result(result_path)
    feed_files = list(agent_dir.glob("feed_*.json"))
    assert len(feed_files) == 1
    feed = json.loads(feed_files[0].read_text(encoding="utf-8"))
    assert "metrics" in feed
    assert "circuit" in feed


def test_ingest_result_significant_creates_significant_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ingested_dir = tmp_path / "ingested"
    significant_dir = ingested_dir / "SIGNIFICANT"
    agent_dir = tmp_path / "agent_feed"
    ingested_dir.mkdir()
    significant_dir.mkdir()
    agent_dir.mkdir()
    monkeypatch.setattr(aa, "INGESTED_DIR", ingested_dir)
    monkeypatch.setattr(aa, "SIGNIFICANT_DIR", significant_dir)
    monkeypatch.setattr(aa, "AGENT_DIR", agent_dir)

    # sacred_score >= 0.618
    counts = {"000": 162, "111": 100}
    result_path = tmp_path / "significant_result.json"
    result_path.write_text(json.dumps(counts), encoding="utf-8")

    aa.ingest_result(result_path)
    significant_files = list(significant_dir.glob("*.json"))
    assert len(significant_files) == 1


def test_ingest_result_not_significant_no_significant_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ingested_dir = tmp_path / "ingested"
    significant_dir = ingested_dir / "SIGNIFICANT"
    agent_dir = tmp_path / "agent_feed"
    ingested_dir.mkdir()
    significant_dir.mkdir()
    agent_dir.mkdir()
    monkeypatch.setattr(aa, "INGESTED_DIR", ingested_dir)
    monkeypatch.setattr(aa, "SIGNIFICANT_DIR", significant_dir)
    monkeypatch.setattr(aa, "AGENT_DIR", agent_dir)

    # phi_approx = 500/100 = 5.0 -> sacred_score ≈ 0.228 < 0.618 -> not significant
    counts = {"00": 500, "01": 100}
    result_path = tmp_path / "nonsignificant_result.json"
    result_path.write_text(json.dumps(counts), encoding="utf-8")

    aa.ingest_result(result_path)
    significant_files = list(significant_dir.glob("*.json"))
    assert len(significant_files) == 0


# ── agent_analyst: parse_promoter_from_fasta ─────────────────────────────────


def test_parse_promoter_from_fasta_gene_and_sefirah(tmp_path: Path) -> None:
    fasta = tmp_path / "ACTB_Malkuth_promoter.fa"
    fasta.write_text(">chromosome:GRCh38:7:100:200:-1\nACGTACGT\n", encoding="utf-8")
    result = aa.parse_promoter_from_fasta(fasta)
    assert result["gene"] == "ACTB"
    assert result["sefirah"] == "Malkuth"
    assert result["name"] == "ACTB_Malkuth"


def test_parse_promoter_from_fasta_sequence(tmp_path: Path) -> None:
    seq = "GGAATCACTTGCACCCGGGAGGCGGAGGCTG"
    fasta = tmp_path / "BDNF_Tiferet_promoter.fa"
    fasta.write_text(f">chr11:100-130\n{seq}\n", encoding="utf-8")
    result = aa.parse_promoter_from_fasta(fasta)
    assert result["sequence"] == seq
    assert result["length"] == len(seq)


def test_parse_promoter_from_fasta_gc_content(tmp_path: Path) -> None:
    fasta = tmp_path / "GENE_Kether_promoter.fa"
    fasta.write_text(">chr1\nACGT\n", encoding="utf-8")
    result = aa.parse_promoter_from_fasta(fasta)
    assert result["gc_content"] == pytest.approx(0.5)


def test_parse_promoter_from_fasta_no_underscore_gene(tmp_path: Path) -> None:
    fasta = tmp_path / "SIMPLE_promoter.fa"
    fasta.write_text(">chr1\nACGT\n", encoding="utf-8")
    result = aa.parse_promoter_from_fasta(fasta)
    # When gene_name has no '_' (after removing _promoter), sefirah equals gene_name
    assert result["name"] == "SIMPLE"
    assert result["gene"] == "SIMPLE"
    assert result["sefirah"] is None


# ── agent_analyst: get_processed_files ───────────────────────────────────────


def test_get_processed_files_returns_file_names(tmp_path: Path) -> None:
    (tmp_path / "result_a.json").write_text("{}", encoding="utf-8")
    (tmp_path / "result_b.json").write_text("{}", encoding="utf-8")
    processed = aa.get_processed_files(tmp_path, ".json")
    assert "result_a.json" in processed
    assert "result_b.json" in processed


def test_get_processed_files_filters_by_suffix(tmp_path: Path) -> None:
    (tmp_path / "circuit.qasm").write_text("OPENQASM 2.0;", encoding="utf-8")
    (tmp_path / "result.json").write_text("{}", encoding="utf-8")
    processed = aa.get_processed_files(tmp_path, ".qasm")
    assert "circuit.qasm" in processed
    assert "result.json" not in processed


def test_get_processed_files_empty_directory(tmp_path: Path) -> None:
    processed = aa.get_processed_files(tmp_path, ".json")
    assert processed == set()


# ── promoter_loader: real promoter files (smoke tests) ───────────────────────

ACTUAL_PROMOTERS_DIR = TEST_REPO_ROOT / "circuits" / "promoters"


@pytest.mark.skipif(
    not ACTUAL_PROMOTERS_DIR.exists(),
    reason="circuits/promoters/ directory not present",
)
def test_real_promoter_files_load_successfully() -> None:
    promoters = pl.load_all_promoters()
    assert len(promoters) > 0
    for p in promoters:
        assert "gene" in p
        assert "sequence" in p
        assert len(p["sequence"]) > 0


@pytest.mark.skipif(
    not ACTUAL_PROMOTERS_DIR.exists(),
    reason="circuits/promoters/ directory not present",
)
def test_real_promoter_actb_malkuth_sha256() -> None:
    result = pl.verify_promoter("ACTB_Malkuth")
    # Should find the file
    assert "error" not in result
    assert result["computed_sha256"] is not None


@pytest.mark.skipif(
    not ACTUAL_PROMOTERS_DIR.exists(),
    reason="circuits/promoters/ directory not present",
)
def test_real_promoter_gc_content_in_range() -> None:
    promoters = pl.load_all_promoters()
    for p in promoters:
        assert 0.0 <= p["gc_content"] <= 1.0


def test_repository_docs_reflect_current_release_metadata() -> None:
    readme = (TEST_REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "v0.4.0-dev" in readme
    assert "106 passed, 2 skipped" in readme
    assert "circuits/promoters/" in readme
    assert "blob/main" not in readme

    agents = uvd.load_all_agents()
    generated = uvd.build_readme(agents, uvd.vault_stats(agents))
    assert "v0.4.0-dev" in generated
    assert "106 passed, 2 skipped" in generated
    assert "circuits/promoters/" in generated
    assert "python -m pip install -r requirements.txt" in generated
    assert "pip install -e ." not in generated
