from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def strip_thinking(output: str) -> str:
    output = re.sub(r"<think>.*?</think>", "", output, flags=re.DOTALL)
    output = re.sub(
        r"Thinking\.{0,3}\n.*?(?:\.{3}done thinking\.?|\Z)",
        "",
        output,
        flags=re.DOTALL,
    )
    return output.strip()


def sanitize_console_text(output: str) -> str:
    ansi_pattern = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
    high_ascii_pattern = re.compile(r"[\u0080-\uffff]+")
    cleaned = ansi_pattern.sub("", output)
    cleaned = high_ascii_pattern.sub("", cleaned)
    cleaned = re.sub(r"[^\x09\x0A\x0D\x20-\x7E]", "", cleaned)
    return cleaned.strip()


def render_run_result(
    console: Console,
    *,
    backend: str,
    mode: str,
    model: str,
    command: list[str] | str,
    returncode: int,
    output: str,
    stderr: str,
) -> None:
    safe_output = sanitize_console_text(output)
    safe_stderr = sanitize_console_text(stderr)

    metadata = Table(box=box.SIMPLE_HEAVY)
    metadata.add_column("Field")
    metadata.add_column("Value")
    metadata.add_row("Backend", backend)
    metadata.add_row("Mode", mode)
    metadata.add_row("Model", model)
    metadata.add_row("Return code", str(returncode))
    rendered_command = (
        command if isinstance(command, str) else " ".join(command)
    )
    metadata.add_row("Command", rendered_command)
    console.print(metadata)

    if safe_output:
        console.print(Panel(safe_output, title="Model Output"))
    if safe_stderr:
        console.print(Panel(safe_stderr, title="Runtime stderr"))


def emit_json_result(
    *,
    backend: str,
    mode: str,
    model: str,
    returncode: int,
    output: str,
    duration_ms: int,
) -> str:
    payload = {
        "backend": backend,
        "mode": mode,
        "model": model,
        "returncode": returncode,
        "output": output,
        "duration_ms": duration_ms,
    }
    return json.dumps(payload, ensure_ascii=False)


def emit_json_document(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def write_json_record(record_path: Path, payload: dict[str, Any]) -> None:
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
