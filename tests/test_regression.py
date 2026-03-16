# pyright: reportMissingImports=false

from __future__ import annotations

import json
import re
import subprocess
import sys
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from tmt_quantum_vault.cli import app, strip_thinking
from tmt_quantum_vault.ollama_api import is_available, run as ollama_run
from tmt_quantum_vault.runner import RunResult

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
    import json

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
    result = RUNNER.invoke(app, ["runtime", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "runtime" in payload
    assert isinstance(payload["runtime"], list)


def test_doctor_json_output() -> None:
    result = RUNNER.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "repository" in payload
    assert "runtime" in payload


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
