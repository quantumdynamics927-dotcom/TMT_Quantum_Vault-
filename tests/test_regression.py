# pyright: reportMissingImports=false

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from tmt_quantum_vault.cli import app, strip_thinking
from tmt_quantum_vault.models import AgentDNA, RuntimeConfig
from tmt_quantum_vault.ollama_api import is_available, run as ollama_run
from tmt_quantum_vault.runner import RunResult, RuntimeRunner
from tmt_quantum_vault.runtime import RuntimeInspector

BRAILLE_SPINNERS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
RUNNER = CliRunner()


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
        cwd="D:/TMT_Quantum_Vault-",
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
        mock_runtime.return_value.inspect_all.return_value = (
            mocked_runtime_checks
        )
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
            mock_runtime.return_value.inspect_all.return_value = (
                mocked_runtime_checks
            )
            result = RUNNER.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "repository" in payload
    assert "runtime" in payload


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
        mock_runtime.return_value.inspect_all.return_value = (
            mocked_runtime_checks
        )
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

    assert (
        "Return exactly one JSON object and nothing else."
        in workflow_prompt
    )
    assert '"stage": "Workflow"' in workflow_prompt
    assert '"required_keys"' in workflow_prompt

    assert "Previous stages as JSON:" in validator_prompt
    assert '"agent": "Workflow"' in validator_prompt
    assert '"stage": "Validator"' in validator_prompt
    assert '"assessment"' in validator_prompt

    assert '"stage": "Visual"' in visual_prompt
    assert '"input_stage": "Validator"' in visual_prompt
    assert '"visual"' in visual_prompt


def test_cloud_mode_rejects_non_cloud_tag() -> None:
    runner = RuntimeRunner(Path("D:/TMT_Quantum_Vault-"), RuntimeConfig())
    result = runner.run(
        prompt="Reply with exactly: test",
        mode="cloud",
        model="nemotron-3-super:120b",
    )
    assert result.returncode == 1
    assert "explicit cloud model tag" in result.stderr


def test_cloud_mode_uses_ollama_cli() -> None:
    runner = RuntimeRunner(Path("D:/TMT_Quantum_Vault-"), RuntimeConfig())
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


def test_inspect_ollama_cloud_ok() -> None:
    inspector = RuntimeInspector(
        Path("D:/TMT_Quantum_Vault-"),
        type(
            "ConfigWrapper",
            (),
            {
                "runtime": RuntimeConfig.model_validate(
                    {
                        "ollama": {
                            "cloud_model": "qwen3-coder-next:cloud"
                        }
                    }
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
    manifest = json.loads(
        (output_dir / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["files"]["doctor"].endswith("doctor.json")
    assert manifest["files"]["agent_task"].endswith("agent-task.json")
    agent_payload = json.loads(
        (output_dir / "agent-task.json").read_text(encoding="utf-8")
    )
    assert agent_payload["record_type"] == "agent-task"
    assert agent_payload["stages"][0]["raw_output"] == "workflow output"
