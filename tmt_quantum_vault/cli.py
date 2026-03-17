# pyright: reportMissingImports=false

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import time
from typing import Any, cast

import requests
import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .ollama_api import run as ollama_run
from .models import AgentDNA, OptimizationEntry, SummarySnapshot
from .output import (
    emit_json_document,
    emit_json_result,
    render_run_result,
    strip_thinking,
)
from .repository import VaultRepository
from .runner import RuntimeRunner
from .runtime import RuntimeInspector

app = typer.Typer(
    help="Inspect and validate the TMT Quantum Vault JSON dataset."
)
console = Console()


def _repo(root: Path) -> VaultRepository:
    return VaultRepository(root)


def _runtime(root: Path) -> RuntimeInspector:
    repo = _repo(root)
    return RuntimeInspector(root, repo.load_vault_config())


def _runner(root: Path) -> RuntimeRunner:
    repo = _repo(root)
    return RuntimeRunner(root, repo.load_vault_config().runtime)


def _json_runtime_check(runtime_check: Any) -> dict[str, Any]:
    return {
        "name": runtime_check.name,
        "status": runtime_check.status,
        "detail": runtime_check.detail,
        "executable": (
            str(runtime_check.executable)
            if runtime_check.executable is not None
            else None
        ),
        "version": runtime_check.version,
    }


def _resolve_agent_profile(
    repo: VaultRepository,
    name: str,
) -> tuple[Path, AgentDNA]:
    match = repo.find_agent(name)
    if match is None:
        raise typer.BadParameter(f"Agent '{name}' was not found.")
    return match


def _agent_system_prompt(agent_profile: AgentDNA) -> str:
    return (
        f"You are {agent_profile.metatron_agent} / "
        f"{agent_profile.dna_agent_name}. "
        f"Specialization: {agent_profile.dna_specialization}. "
        f"Resonance frequency: {agent_profile.resonance_frequency:.1f} Hz. "
        "Return concise, actionable output only. "
        "Do not include markdown fences or commentary outside the required "
        "JSON object."
    )


def _agent_stage_contract(stage_name: str) -> dict[str, Any]:
    if stage_name == "Workflow":
        return {
            "stage": "Workflow",
            "required_keys": [
                "stage",
                "task",
                "objective",
                "plan",
                "handoff",
            ],
            "notes": [
                "plan must contain 1 to 3 short steps",
                "handoff must be one sentence for Validator",
            ],
            "example": {
                "stage": "Workflow",
                "task": "original user task",
                "objective": "short execution objective",
                "plan": ["step one", "step two"],
                "handoff": "validator should verify the plan and risks",
            },
        }

    if stage_name == "Validator":
        return {
            "stage": "Validator",
            "required_keys": [
                "stage",
                "input_stage",
                "assessment",
                "issues",
                "handoff",
            ],
            "notes": [
                "assessment must be one of: pass, revise, fail",
                "issues must be an array of short strings and may be empty",
                "handoff must direct Visual on what to present",
            ],
            "example": {
                "stage": "Validator",
                "input_stage": "Workflow",
                "assessment": "pass",
                "issues": [],
                "handoff": "visual should present the approved result clearly",
            },
        }

    if stage_name == "Visual":
        return {
            "stage": "Visual",
            "required_keys": [
                "stage",
                "input_stage",
                "format",
                "visual",
                "summary",
            ],
            "notes": [
                "format should describe the representation type",
                "visual should be compact and presentation-ready",
                "summary must be one sentence",
            ],
            "example": {
                "stage": "Visual",
                "input_stage": "Validator",
                "format": "status-card",
                "visual": "Workflow approved | Validator pass | Visual ready",
                "summary": "approved result prepared for display",
            },
        }

    return {
        "stage": stage_name,
        "required_keys": ["stage", "input_stage", "result", "handoff"],
        "notes": [
            "result must be concise",
            "handoff must state what the next stage should do",
        ],
        "example": {
            "stage": stage_name,
            "input_stage": "previous stage",
            "result": "short stage result",
            "handoff": "next stage should continue from this result",
        },
    }


def _agent_task_context(prior_outputs: list[dict[str, Any]]) -> str:
    if not prior_outputs:
        return "[]"

    compact_stages = [
        {
            "agent": stage["agent"],
            "persona": stage["persona"],
            "specialization": stage["specialization"],
            "output": stage["output"],
        }
        for stage in prior_outputs
    ]
    return json.dumps(compact_stages, ensure_ascii=False, indent=2)


def _normalize_agent_stage_output(output: str) -> str:
    stripped = output.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return stripped


def _agent_task_prompt(
    *,
    task: str,
    prior_outputs: list[dict[str, Any]],
    stage_name: str,
) -> str:
    contract = _agent_stage_contract(stage_name)
    contract_json = json.dumps(contract, ensure_ascii=False, indent=2)
    if not prior_outputs:
        return (
            f"Task: {task}\n\n"
            f"Stage: {stage_name}\n\n"
            "Return exactly one JSON object and nothing else.\n"
            "Do not use markdown fences.\n\n"
            "Required contract:\n"
            f"{contract_json}\n\n"
            "Previous stages: []"
        )

    previous_stage = prior_outputs[-1]
    prior_context = _agent_task_context(prior_outputs)
    return (
        f"Task: {task}\n\n"
        f"Stage: {stage_name}\n\n"
        "Return exactly one JSON object and nothing else.\n"
        "Do not use markdown fences.\n\n"
        "Required contract:\n"
        f"{contract_json}\n\n"
        "Previous stages as JSON:\n"
        f"{prior_context}\n\n"
        f"Use the most recent stage, {previous_stage['agent']}, as the "
        "primary input. Preserve its intent, but rewrite the response to "
        "match this stage contract exactly."
    )


def _emit_agent_task_json(
    *,
    task: str,
    backend: str | None,
    mode: str | None,
    model: str | None,
    stages: list[dict[str, Any]],
) -> str:
    return emit_json_document(
        {
            "task": task,
            "backend": backend,
            "mode": mode,
            "model": model,
            "stages": stages,
            "final_output": stages[-1]["output"] if stages else "",
            "returncode": next(
                (
                    stage["returncode"]
                    for stage in stages
                    if stage["returncode"] != 0
                ),
                0,
            ),
        }
    )


@app.command("summary")
def summary_command(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
) -> None:
    repo = _repo(root)
    summary_data: SummarySnapshot = repo.build_summary()
    top_agent = cast(AgentDNA | None, summary_data["top_agent"])
    latest_optimization = cast(
        OptimizationEntry | None,
        summary_data["latest_optimization"],
    )
    model_files = cast(list[Path], summary_data["model_files"])

    console.print(
        Panel.fit(
            f"{summary_data['vault_name']}\n"
            f"Consciousness: {summary_data['consciousness_level']}\n"
            f"Fibonacci sync: {summary_data['fibonacci_sync']}",
            title="Vault Summary",
        )
    )

    metrics = Table(box=box.SIMPLE_HEAVY)
    metrics.add_column("Metric")
    metrics.add_column("Value", justify="right")
    metrics.add_row("Agents", str(summary_data["agent_count"]))
    metrics.add_row(
        "Integrated agents",
        str(summary_data["integrated_agents"]),
    )
    metrics.add_row("Memory stores", str(summary_data["memory_store_count"]))
    metrics.add_row("Daily logs", str(summary_data["daily_log_count"]))
    metrics.add_row(
        "Average fitness",
        f"{summary_data['average_fitness']:.3f}",
    )
    metrics.add_row(
        "Average resonance frequency",
        f"{summary_data['average_resonance_frequency']:.1f} Hz",
    )
    metrics.add_row("Models detected", str(len(model_files)))
    console.print(metrics)

    if top_agent is not None:
        console.print(
            Panel.fit(
                f"{top_agent.metatron_agent} / {top_agent.dna_agent_name}\n"
                f"Specialization: {top_agent.dna_specialization}\n"
                f"Fitness: {top_agent.fitness:.3f}\n"
                f"Frequency: {top_agent.resonance_frequency:.1f} Hz",
                title="Top Agent",
            )
        )

    if latest_optimization is not None:
        optimization_timestamp = latest_optimization.data.timestamp.isoformat()
        network_efficiency = latest_optimization.data.network_efficiency
        optimization_score = latest_optimization.data.optimization_score
        console.print(
            Panel.fit(
                f"Timestamp: {optimization_timestamp}\n"
                f"Network efficiency: {network_efficiency:.3f}\n"
                f"Optimization score: {optimization_score:.3f}",
                title="Latest Optimization",
            )
        )


@app.command()
def validate(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
) -> None:
    repo = _repo(root)
    results = repo.validate_repository()
    failures = [result for result in results if not result.valid]

    table = Table(box=box.SIMPLE_HEAVY)
    table.add_column("File")
    table.add_column("Schema")
    table.add_column("Status")

    for result in results:
        status = "ok" if result.valid else "invalid"
        table.add_row(result.path, result.model_name, status)

    console.print(table)

    if failures:
        console.print("\nValidation failures:")
        for failure in failures:
            console.print(f"- {failure.path}: {failure.error}")
        raise typer.Exit(code=1)


@app.command()
def doctor(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
) -> None:
    repo = _repo(root)
    runtime_inspector = _runtime(root)
    checks = repo.repository_checks()
    runtime_checks = runtime_inspector.inspect_all()

    has_repository_warnings = any(status == "warning" for status, _ in checks)
    has_runtime_warnings = any(
        runtime_check.status == "warning"
        for runtime_check in runtime_checks
    )

    if json_out:
        typer.echo(
            emit_json_document(
                {
                    "repository": [
                        {"status": status, "detail": detail}
                        for status, detail in checks
                    ],
                    "runtime": [
                        _json_runtime_check(runtime_check)
                        for runtime_check in runtime_checks
                    ],
                    "has_warnings": (
                        has_repository_warnings or has_runtime_warnings
                    ),
                }
            )
        )
        if has_repository_warnings or has_runtime_warnings:
            raise typer.Exit(code=1)
        return

    table = Table(box=box.SIMPLE_HEAVY)
    table.add_column("Status")
    table.add_column("Source")
    table.add_column("Detail")
    for status, detail in checks:
        table.add_row(status, "repository", detail)
    for runtime_check in runtime_checks:
        runtime_detail = runtime_check.detail
        if runtime_check.executable is not None:
            runtime_detail += f" Executable: {runtime_check.executable}"
        if runtime_check.version:
            runtime_detail += f" Version: {runtime_check.version}"
        table.add_row(runtime_check.status, runtime_check.name, runtime_detail)
    console.print(table)

    if has_repository_warnings or has_runtime_warnings:
        raise typer.Exit(code=1)


@app.command()
def runtime(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
) -> None:
    runtime_inspector = _runtime(root)
    runtime_checks = runtime_inspector.inspect_all()

    all_warnings = all(
        runtime_check.status == "warning"
        for runtime_check in runtime_checks
    )

    if json_out:
        typer.echo(
            emit_json_document(
                {
                    "runtime": [
                        _json_runtime_check(runtime_check)
                        for runtime_check in runtime_checks
                    ],
                    "all_warnings": all_warnings,
                }
            )
        )
        if all_warnings:
            raise typer.Exit(code=1)
        return

    table = Table(box=box.SIMPLE_HEAVY)
    table.add_column("Runtime")
    table.add_column("Status")
    table.add_column("Executable")
    table.add_column("Version")
    table.add_column("Detail")

    for runtime_check in runtime_checks:
        executable = (
            str(runtime_check.executable)
            if runtime_check.executable is not None
            else "-"
        )
        version = runtime_check.version or "-"
        table.add_row(
            runtime_check.name,
            runtime_check.status,
            executable,
            version,
            runtime_check.detail,
        )

    console.print(table)

    if all_warnings:
        raise typer.Exit(code=1)


@app.command()
def run(
    prompt: str = typer.Argument(
        ...,
        help="Prompt to send to the configured runtime.",
    ),
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    backend: str | None = typer.Option(
        None,
        "--backend",
        help="Override the configured backend: ollama or llama.cpp.",
    ),
    mode: str | None = typer.Option(
        None,
        "--mode",
        help="Override the configured Ollama mode: local or cloud.",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Override the configured model name.",
    ),
    raw_final_only: bool = typer.Option(
        False,
        "--raw-final-only",
        help="Strip model thinking blocks from displayed stdout.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
    timeout: int = typer.Option(
        120,
        "--timeout",
        help="Maximum runtime in seconds for the model invocation.",
    ),
) -> None:
    runtime_runner = _runner(root)
    result = runtime_runner.run(
        prompt=prompt,
        backend=backend,
        mode=mode,
        model=model,
        timeout=timeout,
    )
    output = strip_thinking(result.stdout) if raw_final_only else result.stdout
    if json_out:
        typer.echo(
            emit_json_result(
                backend=result.backend,
                mode=result.mode,
                model=result.model,
                returncode=result.returncode,
                output=output,
                duration_ms=result.duration_ms,
            )
        )
        if result.returncode != 0:
            raise typer.Exit(code=result.returncode)
        return

    render_run_result(
        console,
        backend=result.backend,
        mode=result.mode,
        model=result.model,
        command=result.command,
        returncode=result.returncode,
        output=output,
        stderr=result.stderr,
    )

    if result.returncode != 0:
        raise typer.Exit(code=result.returncode)


@app.command("smoke-local")
def smoke_local(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    timeout: int = typer.Option(
        120,
        "--timeout",
        help="Maximum runtime in seconds for the smoke test.",
    ),
    raw_final_only: bool = typer.Option(
        False,
        "--raw-final-only",
        help="Strip model thinking blocks from displayed stdout.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
    force_ollama: bool = typer.Option(
        False,
        "--force-ollama",
        help="Skip llama.cpp and run the local smoke test with Ollama.",
    ),
) -> None:
    repo = _repo(root)
    runtime_config = repo.load_vault_config().runtime
    prompt = "Reply with exactly: TMT local test"

    gguf = next(iter(repo.model_files()), None)
    llama_cpp_path = repo.resolve_path(
        runtime_config.llama_cpp.executable_path
    )

    can_use_llama_cpp = (
        not force_ollama
        and gguf is not None
        and llama_cpp_path is not None
        and llama_cpp_path.exists()
    )

    def _execute(
        command_to_run: list[str],
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command_to_run,
            check=False,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=root.resolve(),
            timeout=timeout,
        )

    render_command: list[str] | str
    subprocess_command: list[str] | None = None
    if can_use_llama_cpp:
        assert gguf is not None
        assert llama_cpp_path is not None
        resolved_gguf = gguf
        resolved_llama_cpp_path = llama_cpp_path
        subprocess_command = [
            str(resolved_llama_cpp_path),
            "--model",
            str(resolved_gguf),
            "--prompt",
            prompt,
            "--n-predict",
            "32",
            "--n-gpu-layers",
            "15",
            "--log-disable",
        ]
        render_command = subprocess_command
        backend = "llama.cpp"
        model = resolved_gguf.name
    else:
        render_command = "ollama HTTP API"
        backend = "ollama-local"
        model = runtime_config.ollama.local_model
        subprocess_command = None

    timeout_note = ""
    completed: subprocess.CompletedProcess[str] | None = None
    duration_ms = 0
    if can_use_llama_cpp:
        try:
            started_at = time.perf_counter()
            assert subprocess_command is not None
            completed = _execute(subprocess_command)
            duration_ms = int((time.perf_counter() - started_at) * 1000)
        except subprocess.TimeoutExpired:
            completed = None
            timeout_note = (
                "Primary local runtime timed out; falling back to local "
                "Ollama."
            )
    else:
        try:
            response = ollama_run(
                model=runtime_config.ollama.local_model,
                prompt=prompt,
                timeout=timeout,
                temperature=0.0,
                num_predict=64,
            )
            completed = subprocess.CompletedProcess(
                args=["ollama-http-api"],
                returncode=response.returncode,
                stdout=response.response,
                stderr="",
            )
            duration_ms = response.total_duration_ns // 1_000_000
        except requests.RequestException as exc:
            completed = subprocess.CompletedProcess(
                args=["ollama-http-api"],
                returncode=1,
                stdout="",
                stderr=str(exc),
            )

    gpu_oom = (
        completed is not None
        and completed.returncode != 0
        and "OutOfDeviceMemory" in (completed.stderr or "")
    )
    if can_use_llama_cpp and gpu_oom:
        subprocess_command = [
            str(resolved_llama_cpp_path),
            "--model",
            str(resolved_gguf),
            "--prompt",
            prompt,
            "--n-predict",
            "32",
            "--n-gpu-layers",
            "0",
            "--log-disable",
        ]
        render_command = subprocess_command
        try:
            started_at = time.perf_counter()
            assert subprocess_command is not None
            completed = _execute(subprocess_command)
            duration_ms = int((time.perf_counter() - started_at) * 1000)
        except subprocess.TimeoutExpired:
            completed = None
            timeout_note = (
                "llama.cpp CPU fallback timed out; falling back to local "
                "Ollama."
            )
        backend = "llama.cpp"

    llama_cpp_failed = (
        can_use_llama_cpp
        and completed is not None
        and completed.returncode != 0
    )
    if llama_cpp_failed:
        timeout_note = (
            "llama.cpp local smoke test failed; falling back to local "
            "Ollama."
        )

    if completed is None or llama_cpp_failed:
        render_command = "ollama HTTP API"
        backend = "ollama-local"
        model = runtime_config.ollama.local_model
        try:
            response = ollama_run(
                model=runtime_config.ollama.local_model,
                prompt=prompt,
                timeout=timeout,
                temperature=0.0,
                num_predict=64,
            )
            completed = subprocess.CompletedProcess(
                args=["ollama-http-api"],
                returncode=response.returncode,
                stdout=response.response,
                stderr="",
            )
            duration_ms = response.total_duration_ns // 1_000_000
        except requests.RequestException as exc:
            completed = subprocess.CompletedProcess(
                args=["ollama-http-api"],
                returncode=1,
                stdout="",
                stderr=str(exc),
            )
            duration_ms = 0

    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    if timeout_note:
        stderr = f"{timeout_note}\n\n{stderr}".strip()
    output = strip_thinking(stdout) if raw_final_only else stdout

    if json_out:
        typer.echo(
            emit_json_result(
                backend=backend,
                mode="local",
                model=model,
                returncode=completed.returncode,
                output=output,
                duration_ms=duration_ms,
            )
        )
        if completed.returncode != 0:
            raise typer.Exit(code=completed.returncode)
        return

    render_run_result(
        console,
        backend=backend,
        mode="local",
        model=model,
        command=render_command,
        returncode=completed.returncode,
        output=output,
        stderr=stderr,
    )

    if completed.returncode != 0:
        raise typer.Exit(code=completed.returncode)


@app.command()
def agent(
    name: str = typer.Argument(
        ...,
        help="Metatron agent name or DNA agent name.",
    ),
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
) -> None:
    repo = _repo(root)
    match = repo.find_agent(name)
    if match is None:
        raise typer.BadParameter(f"Agent '{name}' was not found.")

    path, agent_profile = match
    title = path.relative_to(root.resolve()).as_posix()
    table = Table(title=title, box=box.SIMPLE_HEAVY)
    table.add_column("Field")
    table.add_column("Value")
    for field_name, value in agent_profile.model_dump().items():
        table.add_row(field_name, str(value))
    console.print(table)


@app.command("agent-task")
def agent_task(
    task: str = typer.Argument(
        ...,
        help="Task to execute through the configured agent chain.",
    ),
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    agent_name: str = typer.Option(
        "Workflow",
        "--agent",
        help="Entry agent for the chain.",
    ),
    chain: str = typer.Option(
        "Validator,Visual",
        "--chain",
        help="Comma-separated downstream agents.",
    ),
    backend: str | None = typer.Option(
        None,
        "--backend",
        help="Override the configured backend: ollama or llama.cpp.",
    ),
    mode: str | None = typer.Option(
        None,
        "--mode",
        help="Override the configured Ollama mode: local or cloud.",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Override the configured model name.",
    ),
    raw_final_only: bool = typer.Option(
        False,
        "--raw-final-only",
        help="Strip model thinking blocks from each stage output.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
    timeout: int = typer.Option(
        120,
        "--timeout",
        help="Maximum runtime in seconds for each stage invocation.",
    ),
) -> None:
    repo = _repo(root)
    runtime_runner = _runner(root)
    stage_names = [agent_name] + [
        item.strip() for item in chain.split(",") if item.strip()
    ]

    stages: list[dict[str, Any]] = []
    for stage_name in stage_names:
        _, agent_profile = _resolve_agent_profile(repo, stage_name)
        result = runtime_runner.run(
            prompt=_agent_task_prompt(
                task=task,
                prior_outputs=stages,
                stage_name=agent_profile.metatron_agent,
            ),
            backend=backend,
            mode=mode,
            model=model,
            system=_agent_system_prompt(agent_profile),
            timeout=timeout,
        )
        output = (
            strip_thinking(result.stdout)
            if raw_final_only
            else result.stdout
        )
        output = _normalize_agent_stage_output(output)
        stage_payload = {
            "agent": agent_profile.metatron_agent,
            "persona": agent_profile.dna_agent_name,
            "specialization": agent_profile.dna_specialization,
            "backend": result.backend,
            "mode": result.mode,
            "model": result.model,
            "returncode": result.returncode,
            "duration_ms": result.duration_ms,
            "output": output,
            "stderr": result.stderr,
        }
        stages.append(stage_payload)
        if result.returncode != 0:
            break

    final_returncode = next(
        (stage["returncode"] for stage in stages if stage["returncode"] != 0),
        0,
    )

    if json_out:
        typer.echo(
            _emit_agent_task_json(
                task=task,
                backend=backend,
                mode=mode,
                model=model,
                stages=stages,
            )
        )
        if final_returncode != 0:
            raise typer.Exit(code=final_returncode)
        return

    summary_table = Table(box=box.SIMPLE_HEAVY)
    summary_table.add_column("Agent")
    summary_table.add_column("Persona")
    summary_table.add_column("Status")
    summary_table.add_column("Runtime")
    summary_table.add_column("Duration")
    for stage in stages:
        summary_table.add_row(
            stage["agent"],
            stage["persona"],
            str(stage["returncode"]),
            f"{stage['backend']} / {stage['model']}",
            f"{stage['duration_ms']} ms",
        )
    console.print(summary_table)

    for stage in stages:
        console.print(
            Panel(
                stage["output"] or "",
                title=f"{stage['agent']} Output",
            )
        )
        if stage["stderr"]:
            console.print(
                Panel(stage["stderr"], title=f"{stage['agent']} stderr")
            )

    if final_returncode != 0:
        raise typer.Exit(code=final_returncode)
