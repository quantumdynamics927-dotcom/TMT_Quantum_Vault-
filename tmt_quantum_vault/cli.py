# pyright: reportMissingImports=false

from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import requests
import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .models import (
    AgentDNA,
    SummarySnapshot,
    ValidationResult,
)
from .ollama_api import run as ollama_run
from .output import (
    emit_json_document,
    emit_json_result,
    render_run_result,
    strip_thinking,
    write_json_record,
)
from .repository import VaultRepository
from .runner import RuntimeRunner
from .runtime import RuntimeHealth, RuntimeInspector

app = typer.Typer(help="Inspect and validate the TMT Quantum Vault JSON dataset.")
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


def _resolved_record_path(root: Path, record_path: Path) -> Path:
    if record_path.is_absolute():
        return record_path
    return (root.resolve() / record_path).resolve()


def _write_record(
    *,
    root: Path,
    record_path: Path | None,
    record_type: str,
    payload: dict[str, Any],
) -> None:
    if record_path is None:
        return
    resolved_path = _resolved_record_path(root, record_path)
    write_json_record(
        resolved_path,
        {
            "record_type": record_type,
            "recorded_at": datetime.now(UTC).isoformat(),
            **payload,
        },
    )


def _doctor_payload(
    checks: list[tuple[str, str]],
    runtime_checks: list[Any],
) -> dict[str, Any]:
    has_repository_warnings = any(status == "warning" for status, _ in checks)
    has_runtime_warnings = any(
        runtime_check.status == RuntimeHealth.WARNING
        for runtime_check in runtime_checks
    )
    return {
        "repository": [
            {"status": status, "detail": detail} for status, detail in checks
        ],
        "runtime": [
            _json_runtime_check(runtime_check) for runtime_check in runtime_checks
        ],
        "has_warnings": has_repository_warnings or has_runtime_warnings,
    }


def _runtime_payload(runtime_checks: list[Any]) -> dict[str, Any]:
    all_warnings = all(
        runtime_check.status == RuntimeHealth.WARNING
        for runtime_check in runtime_checks
    )
    return {
        "runtime": [
            _json_runtime_check(runtime_check) for runtime_check in runtime_checks
        ],
        "all_warnings": all_warnings,
    }


def _json_validation_result(result: ValidationResult) -> dict[str, Any]:
    return {
        "path": result.path,
        "model_name": result.model_name,
        "valid": result.valid,
        "error": result.error,
    }


def _summary_payload(summary_data: SummarySnapshot) -> dict[str, Any]:
    top_agent = summary_data["top_agent"]
    latest_optimization = summary_data["latest_optimization"]
    model_files = summary_data["model_files"]
    return {
        "vault_name": summary_data["vault_name"],
        "consciousness_level": summary_data["consciousness_level"],
        "fibonacci_sync": summary_data["fibonacci_sync"],
        "agent_count": summary_data["agent_count"],
        "integrated_agents": summary_data["integrated_agents"],
        "memory_store_count": summary_data["memory_store_count"],
        "daily_log_count": summary_data["daily_log_count"],
        "average_fitness": summary_data["average_fitness"],
        "average_resonance_frequency": summary_data["average_resonance_frequency"],
        "model_count": len(model_files),
        "model_files": [path.as_posix() for path in model_files],
        "top_agent": (
            top_agent.model_dump(mode="json") if top_agent is not None else None
        ),
        "latest_optimization": (
            latest_optimization.model_dump(mode="json")
            if latest_optimization is not None
            else None
        ),
        "returncode": 0,
    }


def _validate_payload(
    results: list[ValidationResult],
) -> tuple[dict[str, Any], int]:
    failures = [result for result in results if not result.valid]
    return (
        {
            "results": [_json_validation_result(result) for result in results],
            "summary": {
                "checked_files": len(results),
                "valid_files": len(results) - len(failures),
                "invalid_files": len(failures),
            },
            "returncode": 1 if failures else 0,
        },
        1 if failures else 0,
    )


def _run_result_payload(
    *,
    backend: str,
    mode: str,
    model: str,
    returncode: int,
    output: str,
    duration_ms: int,
    stderr: str = "",
    command: list[str] | str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "backend": backend,
        "mode": mode,
        "model": model,
        "returncode": returncode,
        "output": output,
        "duration_ms": duration_ms,
    }
    if stderr:
        payload["stderr"] = stderr
    if command is not None:
        payload["command"] = command
    return payload


def _resolve_eval_dataset_path(root: Path, dataset_path: Path) -> Path:
    if dataset_path.is_absolute():
        return dataset_path
    return (root.resolve() / dataset_path).resolve()


def _eval_case_payload(
    *,
    case_id: str,
    prompt: str,
    output: str,
    backend: str,
    mode: str,
    model: str,
    returncode: int,
    duration_ms: int,
    stderr: str,
    command: list[str] | str,
    passed: bool,
    failures: list[str],
) -> dict[str, Any]:
    payload = {
        "id": case_id,
        "prompt": prompt,
        "backend": backend,
        "mode": mode,
        "model": model,
        "returncode": returncode,
        "duration_ms": duration_ms,
        "output": output,
        "passed": passed,
        "failures": failures,
        "command": command,
    }
    if stderr:
        payload["stderr"] = stderr
    return payload


def _evaluate_case_output(
    output: str,
    case: Any,
) -> list[str]:
    failures: list[str] = []
    lowered_output = output.casefold()

    missing_required = [
        token
        for token in case.expectation.contains_all
        if token.casefold() not in lowered_output
    ]
    if missing_required:
        failures.append("missing required tokens: " + ", ".join(missing_required))

    if case.expectation.contains_any and not any(
        token.casefold() in lowered_output for token in case.expectation.contains_any
    ):
        failures.append(
            "missing any-of tokens: " + ", ".join(case.expectation.contains_any)
        )

    present_excluded = [
        token
        for token in case.expectation.excludes
        if token.casefold() in lowered_output
    ]
    if present_excluded:
        failures.append("found excluded tokens: " + ", ".join(present_excluded))

    return failures


def _execute_eval(
    *,
    root: Path,
    dataset_path: Path,
    backend: str | None,
    mode: str | None,
    model: str | None,
    raw_final_only: bool,
    timeout: int,
) -> tuple[dict[str, Any], int]:
    repo = _repo(root)
    resolved_dataset_path = _resolve_eval_dataset_path(root, dataset_path)
    dataset = repo.load_eval_dataset(resolved_dataset_path)
    runtime_runner = _runner(root)

    selected_backend = backend or dataset.backend
    selected_mode = mode or dataset.mode
    selected_model = model or dataset.model

    case_payloads: list[dict[str, Any]] = []
    for case in dataset.cases:
        result = runtime_runner.run(
            prompt=case.prompt,
            backend=selected_backend,
            mode=selected_mode,
            model=selected_model,
            system=case.system,
            timeout=timeout,
        )
        raw_output = result.stdout
        output = strip_thinking(raw_output) if raw_final_only else raw_output
        failures = []
        if result.returncode != 0:
            failures.append("runtime invocation failed")
        failures.extend(_evaluate_case_output(output, case))
        case_payloads.append(
            _eval_case_payload(
                case_id=case.id,
                prompt=case.prompt,
                output=output,
                backend=result.backend,
                mode=result.mode,
                model=result.model,
                returncode=result.returncode,
                duration_ms=result.duration_ms,
                stderr=result.stderr,
                command=result.command,
                passed=not failures,
                failures=failures,
            )
        )

    passed_cases = sum(case["passed"] for case in case_payloads)
    failed_cases = len(case_payloads) - passed_cases
    total_duration_ms = sum(case["duration_ms"] for case in case_payloads)
    payload = {
        "dataset": {
            "name": dataset.name,
            "path": str(resolved_dataset_path),
            "description": dataset.description,
        },
        "backend": selected_backend,
        "mode": selected_mode,
        "model": selected_model,
        "summary": {
            "total_cases": len(case_payloads),
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "success_rate": round(
                (passed_cases / len(case_payloads)) * 100,
                2,
            ),
            "total_duration_ms": total_duration_ms,
        },
        "cases": case_payloads,
        "returncode": 0 if failed_cases == 0 else 1,
    }
    return payload, cast(int, payload["returncode"])


def _resolve_evidence_manifest_path(bundle_path: Path) -> Path:
    if bundle_path.is_dir():
        return bundle_path / "manifest.json"
    return bundle_path


def _load_json_path(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _load_evidence_artifact(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    artifact_path = Path(path)
    if not artifact_path.exists():
        return None
    return _load_json_path(artifact_path)


def _compare_smoke_payloads(
    previous_payload: dict[str, Any] | None,
    current_payload: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    previous_returncode = (
        cast(int, previous_payload.get("returncode", 1))
        if previous_payload is not None
        else None
    )
    current_returncode = (
        cast(int, current_payload.get("returncode", 1))
        if current_payload is not None
        else None
    )
    if current_payload is None:
        failures.append("current smoke-cloud artifact missing")
    elif previous_payload is None:
        failures.append("previous smoke-cloud artifact missing")
    elif previous_returncode == 0 and current_returncode != 0:
        failures.append("smoke-cloud regressed from pass to fail")

    return (
        {
            "previous_returncode": previous_returncode,
            "current_returncode": current_returncode,
            "previous_model": (
                previous_payload.get("model") if previous_payload else None
            ),
            "current_model": (
                current_payload.get("model") if current_payload else None
            ),
        },
        failures,
    )


def _compare_eval_payloads(
    previous_payload: dict[str, Any] | None,
    current_payload: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    previous_summary = (
        cast(dict[str, Any], previous_payload.get("summary", {}))
        if previous_payload is not None
        else {}
    )
    current_summary = (
        cast(dict[str, Any], current_payload.get("summary", {}))
        if current_payload is not None
        else {}
    )
    if current_payload is None:
        failures.append("current eval artifact missing")
    elif previous_payload is None:
        failures.append("previous eval artifact missing")
    else:
        previous_failed = cast(int, previous_summary.get("failed_cases", 0))
        current_failed = cast(int, current_summary.get("failed_cases", 0))
        previous_success = cast(
            float,
            previous_summary.get("success_rate", 0.0),
        )
        current_success = cast(
            float,
            current_summary.get("success_rate", 0.0),
        )
        if current_failed > previous_failed:
            failures.append("eval failed case count increased")
        if current_success < previous_success:
            failures.append("eval success rate decreased")

    return (
        {
            "previous_dataset": (
                cast(dict[str, Any], previous_payload.get("dataset", {})).get("name")
                if previous_payload is not None
                else None
            ),
            "current_dataset": (
                cast(dict[str, Any], current_payload.get("dataset", {})).get("name")
                if current_payload is not None
                else None
            ),
            "previous_summary": previous_summary,
            "current_summary": current_summary,
        },
        failures,
    )


def _compare_agent_task_payloads(
    previous_payload: dict[str, Any] | None,
    current_payload: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    previous_returncode = (
        cast(int, previous_payload.get("returncode", 1))
        if previous_payload is not None
        else None
    )
    current_returncode = (
        cast(int, current_payload.get("returncode", 1))
        if current_payload is not None
        else None
    )
    previous_stages = (
        cast(list[dict[str, Any]], previous_payload.get("stages", []))
        if previous_payload is not None
        else []
    )
    current_stages = (
        cast(list[dict[str, Any]], current_payload.get("stages", []))
        if current_payload is not None
        else []
    )
    if current_payload is None:
        failures.append("current agent-task artifact missing")
    elif previous_payload is None:
        failures.append("previous agent-task artifact missing")
    elif previous_returncode == 0 and current_returncode != 0:
        failures.append("agent-task regressed from pass to fail")

    return (
        {
            "previous_returncode": previous_returncode,
            "current_returncode": current_returncode,
            "previous_stage_count": len(previous_stages),
            "current_stage_count": len(current_stages),
        },
        failures,
    )


def _execute_compare_evidence(
    *,
    previous_bundle: Path,
    current_bundle: Path,
) -> tuple[dict[str, Any], int]:
    previous_manifest_path = _resolve_evidence_manifest_path(previous_bundle)
    current_manifest_path = _resolve_evidence_manifest_path(current_bundle)
    previous_manifest = _load_json_path(previous_manifest_path)
    current_manifest = _load_json_path(current_manifest_path)

    previous_files = cast(dict[str, str], previous_manifest.get("files", {}))
    current_files = cast(dict[str, str], current_manifest.get("files", {}))

    smoke_summary, smoke_failures = _compare_smoke_payloads(
        _load_evidence_artifact(previous_files.get("smoke_cloud")),
        _load_evidence_artifact(current_files.get("smoke_cloud")),
    )
    eval_summary, eval_failures = _compare_eval_payloads(
        _load_evidence_artifact(previous_files.get("eval")),
        _load_evidence_artifact(current_files.get("eval")),
    )
    agent_task_summary, agent_task_failures = _compare_agent_task_payloads(
        _load_evidence_artifact(previous_files.get("agent_task")),
        _load_evidence_artifact(current_files.get("agent_task")),
    )

    regressions = [
        *smoke_failures,
        *eval_failures,
        *agent_task_failures,
    ]
    previous_returncode = cast(int, previous_manifest.get("returncode", 1))
    current_returncode = cast(int, current_manifest.get("returncode", 1))
    if previous_returncode == 0 and current_returncode != 0:
        regressions.append("overall bundle returncode regressed from pass to fail")

    payload = {
        "previous_bundle": str(previous_manifest_path.parent),
        "current_bundle": str(current_manifest_path.parent),
        "summary": {
            "previous_returncode": previous_returncode,
            "current_returncode": current_returncode,
            "regression_count": len(regressions),
            "has_regressions": bool(regressions),
        },
        "components": {
            "smoke_cloud": smoke_summary,
            "eval": eval_summary,
            "agent_task": agent_task_summary,
        },
        "regressions": regressions,
        "returncode": 1 if regressions else 0,
    }
    return payload, cast(int, payload["returncode"])


def _default_release_evidence_dir(root: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return root / "Resonance_Logs" / "daily" / f"release-evidence-{timestamp}"


def _find_latest_release_evidence_bundle(
    root: Path,
    current_bundle: Path | None = None,
) -> Path | None:
    daily_dir = root.resolve() / "Resonance_Logs" / "daily"
    if not daily_dir.exists():
        return None

    candidates: list[Path] = []
    resolved_current = current_bundle.resolve() if current_bundle else None
    for candidate in daily_dir.glob("release-evidence*"):
        if not candidate.is_dir():
            continue
        if resolved_current is not None and candidate.resolve() == resolved_current:
            continue
        manifest_path = candidate / "manifest.json"
        if manifest_path.exists():
            candidates.append(candidate)

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda candidate: (candidate / "manifest.json").stat().st_mtime_ns,
    )


def _execute_release_summary(
    *,
    root: Path,
    bundle: Path | None,
) -> tuple[dict[str, Any], int]:
    selected_bundle = bundle
    if selected_bundle is None:
        selected_bundle = _find_latest_release_evidence_bundle(root)
        if selected_bundle is None:
            raise typer.BadParameter(
                "No release-evidence bundle with a manifest was found in "
                "Resonance_Logs/daily."
            )

    manifest_path = _resolve_evidence_manifest_path(selected_bundle)
    manifest = _load_json_path(manifest_path)
    files = cast(dict[str, str], manifest.get("files", {}))

    smoke_payload = _load_evidence_artifact(files.get("smoke_cloud")) or {}
    eval_payload = _load_evidence_artifact(files.get("eval")) or {}
    agent_task_payload = _load_evidence_artifact(files.get("agent_task")) or {}
    compare_payload = _load_evidence_artifact(files.get("compare_evidence"))

    eval_summary = cast(dict[str, Any], eval_payload.get("summary", {}))
    compare_summary = (
        cast(dict[str, Any], compare_payload.get("summary", {}))
        if compare_payload is not None
        else None
    )
    stages = cast(list[dict[str, Any]], agent_task_payload.get("stages", []))

    payload = {
        "bundle_dir": str(manifest_path.parent),
        "compared_to": manifest.get("compared_to"),
        "overall": {
            "returncode": cast(int, manifest.get("returncode", 1)),
            "has_comparison": compare_payload is not None,
        },
        "smoke_cloud": {
            "returncode": smoke_payload.get("returncode"),
            "model": smoke_payload.get("model"),
        },
        "eval": {
            "dataset": cast(
                dict[str, Any],
                eval_payload.get("dataset", {}),
            ).get("name"),
            "passed_cases": eval_summary.get("passed_cases"),
            "total_cases": eval_summary.get("total_cases"),
            "failed_cases": eval_summary.get("failed_cases"),
            "success_rate": eval_summary.get("success_rate"),
        },
        "agent_task": {
            "returncode": agent_task_payload.get("returncode"),
            "stage_count": len(stages),
            "final_output": agent_task_payload.get("final_output"),
        },
        "comparison": {
            "has_regressions": (
                compare_summary.get("has_regressions")
                if compare_summary is not None
                else None
            ),
            "regression_count": (
                compare_summary.get("regression_count")
                if compare_summary is not None
                else None
            ),
        },
        "returncode": cast(int, manifest.get("returncode", 1)),
    }
    return payload, cast(int, payload["returncode"])


def _execute_release_gate(
    *,
    root: Path,
    bundle: Path | None,
    require_comparison: bool,
) -> tuple[dict[str, Any], int]:
    summary_payload, _ = _execute_release_summary(root=root, bundle=bundle)

    overall = cast(dict[str, Any], summary_payload["overall"])
    smoke_summary = cast(dict[str, Any], summary_payload["smoke_cloud"])
    eval_summary = cast(dict[str, Any], summary_payload["eval"])
    agent_task_summary = cast(dict[str, Any], summary_payload["agent_task"])
    comparison_summary = cast(dict[str, Any], summary_payload["comparison"])

    failures: list[str] = []
    if overall["returncode"] != 0:
        failures.append("bundle manifest returncode is non-zero")
    if smoke_summary["returncode"] != 0:
        failures.append("smoke-cloud check failed")
    if eval_summary["failed_cases"] not in {0, None}:
        failures.append("eval contains failed cases")
    if agent_task_summary["returncode"] != 0:
        failures.append("agent-task check failed")

    has_comparison = bool(overall["has_comparison"])
    if require_comparison and not has_comparison:
        failures.append("comparison artifact is required but missing")
    if comparison_summary["has_regressions"] is True:
        failures.append("comparison detected regressions")

    payload = {
        "bundle_dir": summary_payload["bundle_dir"],
        "compared_to": summary_payload["compared_to"],
        "policy": {
            "require_comparison": require_comparison,
        },
        "checks": {
            "overall": overall,
            "smoke_cloud": smoke_summary,
            "eval": eval_summary,
            "agent_task": agent_task_summary,
            "comparison": comparison_summary,
        },
        "decision": "pass" if not failures else "fail",
        "failures": failures,
        "returncode": 0 if not failures else 1,
    }
    return payload, cast(int, payload["returncode"])


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
                (stage["returncode"] for stage in stages if stage["returncode"] != 0),
                0,
            ),
        }
    )


def _execute_smoke_cloud(
    *,
    root: Path,
    model: str | None,
    timeout: int,
    raw_final_only: bool,
) -> tuple[dict[str, Any], int]:
    runtime_runner = _runner(root)
    result = runtime_runner.run(
        prompt="Reply with exactly: TMT cloud test",
        backend="ollama",
        mode="cloud",
        model=model,
        timeout=timeout,
    )
    output = strip_thinking(result.stdout) if raw_final_only else result.stdout
    output = _normalize_agent_stage_output(output)
    payload = _run_result_payload(
        backend=result.backend,
        mode=result.mode,
        model=result.model,
        returncode=result.returncode,
        output=output,
        duration_ms=result.duration_ms,
        stderr=result.stderr,
        command=result.command,
    )
    return payload, result.returncode


def _execute_agent_task(
    *,
    root: Path,
    task: str,
    agent_name: str,
    chain: str,
    backend: str | None,
    mode: str | None,
    model: str | None,
    raw_final_only: bool,
    timeout: int,
) -> tuple[dict[str, Any], int]:
    repo = _repo(root)
    runtime_runner = _runner(root)
    stage_names = [agent_name] + [
        item.strip() for item in chain.split(",") if item.strip()
    ]

    stages: list[dict[str, Any]] = []
    for current_stage_name in stage_names:
        _, agent_profile = _resolve_agent_profile(repo, current_stage_name)
        system_prompt = _agent_system_prompt(agent_profile)
        stage_prompt = _agent_task_prompt(
            task=task,
            prior_outputs=stages,
            stage_name=agent_profile.metatron_agent,
        )
        result = runtime_runner.run(
            prompt=stage_prompt,
            backend=backend,
            mode=mode,
            model=model,
            system=system_prompt,
            timeout=timeout,
        )
        raw_output = result.stdout
        output = strip_thinking(raw_output) if raw_final_only else raw_output
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
            "command": result.command,
            "system_prompt": system_prompt,
            "prompt": stage_prompt,
            "raw_output": raw_output,
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
    payload = json.loads(
        _emit_agent_task_json(
            task=task,
            backend=backend,
            mode=mode,
            model=model,
            stages=stages,
        )
    )
    return payload, final_returncode


def _resolve_agi_root(root: Path, agi_root: Path | None) -> Path:
    if agi_root is not None:
        if agi_root.is_absolute():
            return agi_root.resolve()
        return (agi_root.resolve()).resolve()
    return (root.resolve().parent / "AGI-model").resolve()


def _resolve_agi_artifact_paths(
    agi_root: Path,
    artifacts: list[Path] | None,
) -> list[Path]:
    if artifacts:
        resolved_artifacts = [
            (
                artifact.resolve()
                if artifact.is_absolute()
                else (agi_root / artifact).resolve()
            )
            for artifact in artifacts
        ]
    else:
        resolved_artifacts = [
            (agi_root / "phi_agent_report_20260310_231439.json").resolve(),
            (agi_root / "dna_quantum_analysis_results.json").resolve(),
            (agi_root / "ibm_hardware_aggregate_20260202_040836.json").resolve(),
        ]

    missing = [str(path) for path in resolved_artifacts if not path.exists()]
    if missing:
        raise typer.BadParameter(
            "AGI eval artifacts are missing: " + ", ".join(missing)
        )

    return resolved_artifacts


def _resolve_agi_dataset_output(
    agi_root: Path,
    dataset_output: Path | None,
) -> tuple[Path, bool]:
    if dataset_output is None:
        with tempfile.NamedTemporaryFile(
            prefix="agi-vault-eval-",
            suffix=".json",
            delete=False,
        ) as handle:
            return Path(handle.name).resolve(), True

    resolved_output = (
        dataset_output.resolve()
        if dataset_output.is_absolute()
        else (agi_root / dataset_output).resolve()
    )
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    return resolved_output, False


def _agi_stage_output(title: str, lines: list[str]) -> dict[str, Any]:
    return {
        "agent": title,
        "persona": title,
        "specialization": "deterministic-contract",
        "returncode": 0,
        "output": "\n".join(lines).strip(),
        "stderr": "",
    }


def _render_metric_lines(metrics: dict[str, Any], limit: int = 6) -> list[str]:
    selected_items = list(metrics.items())[:limit]
    return [f"{key}: {value}" for key, value in selected_items]


def _execute_agi_validate(
    *,
    root: Path,
    agi_root: Path | None,
    operation: str,
    artifact: Path | None,
    python_executable: str | None,
    timeout: int,
) -> tuple[dict[str, Any], int]:
    resolved_agi_root = _resolve_agi_root(root, agi_root)
    executable = python_executable or sys.executable
    command = [executable, "-m", "agi_model.validate_run", operation]
    if artifact is not None:
        resolved_artifact = artifact
        if not artifact.is_absolute():
            resolved_artifact = (resolved_agi_root / artifact).resolve()
        command.extend(["--artifact", str(resolved_artifact)])

    started_at = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=resolved_agi_root,
            timeout=timeout,
        )
        duration_ms = int((time.perf_counter() - started_at) * 1000)
    except subprocess.TimeoutExpired as exc:
        timeout_payload = {
            "operation": operation,
            "passed": False,
            "agi_root": str(resolved_agi_root),
            "command": command,
            "duration_ms": int((time.perf_counter() - started_at) * 1000),
            "error": f"Validation timed out after {timeout} seconds.",
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "stages": [
                _agi_stage_output(
                    "Workflow",
                    [
                        f"Attempted operation: {operation}",
                        f"AGI root: {resolved_agi_root}",
                    ],
                ),
                _agi_stage_output(
                    "Validator",
                    [f"Timed out after {timeout} seconds."],
                ),
                _agi_stage_output(
                    "Visual",
                    ["No metrics available because the subprocess timed out."],
                ),
            ],
        }
        return timeout_payload, 1

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    contract_result: dict[str, Any]
    try:
        contract_result = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        contract_result = {
            "passed": False,
            "error": "AGI contract output was not valid JSON.",
            "raw_stdout": stdout,
        }

    checks = cast(list[dict[str, Any]], contract_result.get("checks", []))
    metrics = cast(dict[str, Any], contract_result.get("metrics", {}))
    passed = bool(contract_result.get("passed")) and completed.returncode == 0
    failed_checks = [
        check.get("name", "unknown")
        for check in checks
        if not check.get("passed", False)
    ]
    stages = [
        _agi_stage_output(
            "Workflow",
            [
                f"Executed AGI contract operation: {operation}",
                f"AGI root: {resolved_agi_root}",
                f"Command: {' '.join(command)}",
                f"Contract version: {contract_result.get('contract_version', 'unknown')}",
            ],
        ),
        _agi_stage_output(
            "Validator",
            [
                f"Subprocess return code: {completed.returncode}",
                f"Contract passed: {bool(contract_result.get('passed'))}",
                (
                    "Failed checks: " + ", ".join(failed_checks)
                    if failed_checks
                    else f"Checks passed: {len(checks)} / {len(checks) if checks else 0}"
                ),
                (
                    f"Error: {contract_result.get('error')}"
                    if contract_result.get("error")
                    else "No contract error reported."
                ),
            ],
        ),
        _agi_stage_output(
            "Visual",
            _render_metric_lines(metrics)
            or ["No metrics were returned by the AGI contract."],
        ),
    ]
    for stage in stages:
        stage["returncode"] = (
            completed.returncode if stage["agent"] == "Validator" else 0
        )

    payload = {
        "operation": operation,
        "passed": passed,
        "agi_root": str(resolved_agi_root),
        "command": command,
        "duration_ms": duration_ms,
        "subprocess_returncode": completed.returncode,
        "result": contract_result,
        "stdout": stdout,
        "stderr": stderr,
        "stages": stages,
    }
    return payload, 0 if passed else max(completed.returncode, 1)


def _execute_agi_eval_smoke(
    *,
    root: Path,
    agi_root: Path | None,
    artifacts: list[Path] | None,
    dataset_output: Path | None,
    dataset_name: str,
    description: str,
    backend: str | None,
    mode: str | None,
    model: str | None,
    raw_final_only: bool,
    python_executable: str | None,
    timeout: int,
) -> tuple[dict[str, Any], int]:
    resolved_agi_root = _resolve_agi_root(root, agi_root)
    resolved_artifacts = _resolve_agi_artifact_paths(
        resolved_agi_root,
        artifacts,
    )
    resolved_dataset_output, used_temporary_path = _resolve_agi_dataset_output(
        resolved_agi_root, dataset_output
    )
    converter_path = (
        resolved_agi_root / "convert_agi_results_to_tmt_eval.py"
    ).resolve()
    executable = python_executable or sys.executable
    generation_command = [
        executable,
        str(converter_path),
        *(str(path) for path in resolved_artifacts),
        "--output",
        str(resolved_dataset_output),
        "--name",
        dataset_name,
        "--description",
        description,
    ]
    if backend is not None:
        generation_command.extend(["--backend", backend])
    if mode is not None:
        generation_command.extend(["--mode", mode])
    if model is not None:
        generation_command.extend(["--model", model])

    started_at = time.perf_counter()
    try:
        generation = subprocess.run(
            generation_command,
            check=False,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=resolved_agi_root,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        generation_duration_ms = int((time.perf_counter() - started_at) * 1000)
        return (
            {
                "agi_root": str(resolved_agi_root),
                "artifacts": [str(path) for path in resolved_artifacts],
                "dataset_path": str(resolved_dataset_output),
                "dataset_temporary": used_temporary_path,
                "generation": {
                    "command": generation_command,
                    "returncode": 1,
                    "duration_ms": generation_duration_ms,
                    "stdout": (exc.stdout or "").strip(),
                    "stderr": (
                        (exc.stderr or "").strip()
                        or (
                            "AGI dataset generation timed out after "
                            f"{timeout} seconds."
                        )
                    ),
                },
                "returncode": 1,
            },
            1,
        )
    generation_duration_ms = int((time.perf_counter() - started_at) * 1000)

    payload: dict[str, Any] = {
        "agi_root": str(resolved_agi_root),
        "artifacts": [str(path) for path in resolved_artifacts],
        "dataset_path": str(resolved_dataset_output),
        "dataset_temporary": used_temporary_path,
        "generation": {
            "command": generation_command,
            "returncode": generation.returncode,
            "duration_ms": generation_duration_ms,
            "stdout": generation.stdout.strip(),
            "stderr": generation.stderr.strip(),
        },
    }
    if generation.returncode != 0:
        payload["returncode"] = generation.returncode
        return payload, generation.returncode

    repo = _repo(root)
    try:
        dataset = repo.load_eval_dataset(resolved_dataset_output)
    except Exception as exc:
        payload["dataset_error"] = str(exc)
        payload["returncode"] = 1
        return payload, 1

    payload["dataset"] = {
        "name": dataset.name,
        "description": dataset.description,
        "backend": dataset.backend,
        "mode": dataset.mode,
        "model": dataset.model,
        "cases": len(dataset.cases),
    }

    eval_payload, eval_returncode = _execute_eval(
        root=root,
        dataset_path=resolved_dataset_output,
        backend=backend,
        mode=mode,
        model=model,
        raw_final_only=raw_final_only,
        timeout=timeout,
    )
    payload["eval"] = eval_payload
    payload["returncode"] = eval_returncode
    return payload, eval_returncode


@app.command("summary")
def summary_command(
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
    summary_data: SummarySnapshot = repo.build_summary()
    top_agent = summary_data["top_agent"]
    latest_optimization = summary_data["latest_optimization"]
    model_files = summary_data["model_files"]

    if json_out:
        typer.echo(emit_json_document(_summary_payload(summary_data)))
        return

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
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
) -> None:
    repo = _repo(root)
    results = repo.validate_repository()
    failures = [result for result in results if not result.valid]

    if json_out:
        payload, return_code = _validate_payload(results)
        typer.echo(emit_json_document(payload))
        if return_code != 0:
            raise typer.Exit(code=return_code)
        return

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
    record_path: Path | None = typer.Option(
        None,
        "--record-path",
        help="Write a structured JSON record to the specified path.",
    ),
) -> None:
    repo = _repo(root)
    runtime_inspector = _runtime(root)
    checks = repo.repository_checks()
    runtime_checks = runtime_inspector.inspect_all()

    doctor_payload = _doctor_payload(checks, runtime_checks)
    has_warnings = bool(doctor_payload["has_warnings"])

    _write_record(
        root=root,
        record_path=record_path,
        record_type="doctor",
        payload=doctor_payload,
    )

    if json_out:
        typer.echo(emit_json_document(doctor_payload))
        if has_warnings:
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

    if has_warnings:
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
    record_path: Path | None = typer.Option(
        None,
        "--record-path",
        help="Write a structured JSON record to the specified path.",
    ),
) -> None:
    runtime_inspector = _runtime(root)
    runtime_checks = runtime_inspector.inspect_all()
    runtime_payload = _runtime_payload(runtime_checks)
    all_warnings = bool(runtime_payload["all_warnings"])

    _write_record(
        root=root,
        record_path=record_path,
        record_type="runtime",
        payload=runtime_payload,
    )

    if json_out:
        typer.echo(emit_json_document(runtime_payload))
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
    llama_cpp_path = repo.resolve_path(runtime_config.llama_cpp.executable_path)

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
                "Primary local runtime timed out; falling back to local Ollama."
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
                "llama.cpp CPU fallback timed out; falling back to local Ollama."
            )
        backend = "llama.cpp"

    llama_cpp_failed = (
        can_use_llama_cpp and completed is not None and completed.returncode != 0
    )
    if llama_cpp_failed:
        timeout_note = (
            "llama.cpp local smoke test failed; falling back to local Ollama."
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


@app.command("smoke-cloud")
def smoke_cloud(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Override the configured cloud model name.",
    ),
    timeout: int = typer.Option(
        120,
        "--timeout",
        help="Maximum runtime in seconds for the cloud smoke test.",
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
    record_path: Path | None = typer.Option(
        None,
        "--record-path",
        help="Write a structured JSON record to the specified path.",
    ),
) -> None:
    smoke_payload, return_code = _execute_smoke_cloud(
        root=root,
        model=model,
        timeout=timeout,
        raw_final_only=raw_final_only,
    )

    _write_record(
        root=root,
        record_path=record_path,
        record_type="smoke-cloud",
        payload=smoke_payload,
    )

    if json_out:
        typer.echo(emit_json_document(smoke_payload))
        if return_code != 0:
            raise typer.Exit(code=return_code)
        return

    render_run_result(
        console,
        backend=cast(str, smoke_payload["backend"]),
        mode=cast(str, smoke_payload["mode"]),
        model=cast(str, smoke_payload["model"]),
        command=cast(
            list[str] | str,
            smoke_payload.get("command", "ollama run"),
        ),
        returncode=cast(int, smoke_payload["returncode"]),
        output=cast(str, smoke_payload["output"]),
        stderr=cast(str, smoke_payload.get("stderr", "")),
    )

    if return_code != 0:
        raise typer.Exit(code=return_code)


@app.command("eval")
def eval_command(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    dataset: Path = typer.Option(
        Path("evals/baseline.json"),
        "--dataset",
        help="Path to the evaluation dataset JSON file.",
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
        help="Strip model thinking blocks from evaluated outputs.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
    record_path: Path | None = typer.Option(
        None,
        "--record-path",
        help="Write a structured JSON record to the specified path.",
    ),
    timeout: int = typer.Option(
        120,
        "--timeout",
        help="Maximum runtime in seconds for each evaluation case.",
    ),
) -> None:
    eval_payload, return_code = _execute_eval(
        root=root,
        dataset_path=dataset,
        backend=backend,
        mode=mode,
        model=model,
        raw_final_only=raw_final_only,
        timeout=timeout,
    )

    _write_record(
        root=root,
        record_path=record_path,
        record_type="eval",
        payload=eval_payload,
    )

    if json_out:
        typer.echo(emit_json_document(eval_payload))
        if return_code != 0:
            raise typer.Exit(code=return_code)
        return

    summary = cast(dict[str, Any], eval_payload["summary"])
    console.print(
        Panel.fit(
            (
                f"{cast(dict[str, Any], eval_payload['dataset'])['name']}\n"
                f"Pass: {summary['passed_cases']} / {summary['total_cases']}\n"
                f"Success rate: {summary['success_rate']}%"
            ),
            title="Evaluation Summary",
        )
    )

    table = Table(box=box.SIMPLE_HEAVY)
    table.add_column("Case")
    table.add_column("Status")
    table.add_column("Runtime")
    table.add_column("Duration")
    table.add_column("Failures")
    for case in cast(list[dict[str, Any]], eval_payload["cases"]):
        table.add_row(
            cast(str, case["id"]),
            "pass" if cast(bool, case["passed"]) else "fail",
            f"{case['backend']} / {case['model']}",
            f"{case['duration_ms']} ms",
            "; ".join(cast(list[str], case["failures"])) or "-",
        )
    console.print(table)

    if return_code != 0:
        raise typer.Exit(code=return_code)


@app.command("compare-evidence")
def compare_evidence(
    previous_bundle: Path = typer.Argument(
        ...,
        help="Previous release-evidence bundle directory or manifest path.",
    ),
    current_bundle: Path = typer.Argument(
        ...,
        help="Current release-evidence bundle directory or manifest path.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
    record_path: Path | None = typer.Option(
        None,
        "--record-path",
        help="Write a structured JSON record to the specified path.",
    ),
) -> None:
    compare_payload, return_code = _execute_compare_evidence(
        previous_bundle=previous_bundle,
        current_bundle=current_bundle,
    )

    _write_record(
        root=Path("."),
        record_path=record_path,
        record_type="compare-evidence",
        payload=compare_payload,
    )

    if json_out:
        typer.echo(emit_json_document(compare_payload))
        if return_code != 0:
            raise typer.Exit(code=return_code)
        return

    summary = cast(dict[str, Any], compare_payload["summary"])
    console.print(
        Panel.fit(
            (
                f"Previous: {compare_payload['previous_bundle']}\n"
                f"Current: {compare_payload['current_bundle']}\n"
                f"Regressions: {summary['regression_count']}"
            ),
            title="Evidence Comparison",
        )
    )

    component_table = Table(box=box.SIMPLE_HEAVY)
    component_table.add_column("Component")
    component_table.add_column("Previous")
    component_table.add_column("Current")
    component_table.add_row(
        "smoke-cloud",
        str(
            cast(dict[str, Any], compare_payload["components"])["smoke_cloud"][
                "previous_returncode"
            ]
        ),
        str(
            cast(dict[str, Any], compare_payload["components"])["smoke_cloud"][
                "current_returncode"
            ]
        ),
    )
    component_table.add_row(
        "eval failed cases",
        str(
            cast(dict[str, Any], compare_payload["components"])["eval"][
                "previous_summary"
            ].get("failed_cases")
        ),
        str(
            cast(dict[str, Any], compare_payload["components"])["eval"][
                "current_summary"
            ].get("failed_cases")
        ),
    )
    component_table.add_row(
        "agent-task",
        str(
            cast(dict[str, Any], compare_payload["components"])["agent_task"][
                "previous_returncode"
            ]
        ),
        str(
            cast(dict[str, Any], compare_payload["components"])["agent_task"][
                "current_returncode"
            ]
        ),
    )
    console.print(component_table)

    regressions = cast(list[str], compare_payload["regressions"])
    if regressions:
        console.print(Panel("\n".join(regressions), title="Regressions"))

    if return_code != 0:
        raise typer.Exit(code=return_code)


@app.command("release-summary")
def release_summary(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    bundle: Path | None = typer.Option(
        None,
        "--bundle",
        help=(
            "Release-evidence bundle directory or manifest path. When "
            "omitted, the newest bundle in Resonance_Logs/daily is used."
        ),
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
    record_path: Path | None = typer.Option(
        None,
        "--record-path",
        help="Write a structured JSON record to the specified path.",
    ),
) -> None:
    summary_payload, return_code = _execute_release_summary(
        root=root,
        bundle=bundle,
    )

    _write_record(
        root=root,
        record_path=record_path,
        record_type="release-summary",
        payload=summary_payload,
    )

    if json_out:
        typer.echo(emit_json_document(summary_payload))
        if return_code != 0:
            raise typer.Exit(code=return_code)
        return

    overall = cast(dict[str, Any], summary_payload["overall"])
    console.print(
        Panel.fit(
            (
                f"Bundle: {summary_payload['bundle_dir']}\n"
                f"Return code: {overall['returncode']}\n"
                f"Compared: {summary_payload['compared_to'] or 'none'}"
            ),
            title="Release Summary",
        )
    )

    table = Table(box=box.SIMPLE_HEAVY)
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    smoke_summary = cast(dict[str, Any], summary_payload["smoke_cloud"])
    eval_component = cast(dict[str, Any], summary_payload["eval"])
    agent_task_component = cast(
        dict[str, Any],
        summary_payload["agent_task"],
    )
    comparison_component = cast(
        dict[str, Any],
        summary_payload["comparison"],
    )
    table.add_row(
        "smoke-cloud",
        str(smoke_summary["returncode"]),
        str(smoke_summary["model"]),
    )
    table.add_row(
        "eval",
        str(eval_component["failed_cases"]),
        (
            f"{eval_component['passed_cases']} / "
            f"{eval_component['total_cases']} "
            f"passed"
        ),
    )
    table.add_row(
        "agent-task",
        str(agent_task_component["returncode"]),
        f"{agent_task_component['stage_count']} stages",
    )
    table.add_row(
        "comparison",
        str(comparison_component["has_regressions"]),
        (
            f"{comparison_component['regression_count']} regressions"
            if comparison_component["regression_count"] is not None
            else "no comparison artifact"
        ),
    )
    console.print(table)

    if return_code != 0:
        raise typer.Exit(code=return_code)


@app.command("release-gate")
def release_gate(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    bundle: Path | None = typer.Option(
        None,
        "--bundle",
        help=(
            "Release-evidence bundle directory or manifest path. When "
            "omitted, the newest bundle in Resonance_Logs/daily is used."
        ),
    ),
    require_comparison: bool = typer.Option(
        False,
        "--require-comparison",
        help="Fail the gate when no comparison artifact is present.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
    record_path: Path | None = typer.Option(
        None,
        "--record-path",
        help="Write a structured JSON record to the specified path.",
    ),
) -> None:
    gate_payload, return_code = _execute_release_gate(
        root=root,
        bundle=bundle,
        require_comparison=require_comparison,
    )

    _write_record(
        root=root,
        record_path=record_path,
        record_type="release-gate",
        payload=gate_payload,
    )

    if json_out:
        typer.echo(emit_json_document(gate_payload))
        if return_code != 0:
            raise typer.Exit(code=return_code)
        return

    console.print(
        Panel.fit(
            (
                f"Decision: {gate_payload['decision']}\n"
                f"Bundle: {gate_payload['bundle_dir']}\n"
                f"Compared: {gate_payload['compared_to'] or 'none'}"
            ),
            title="Release Gate",
        )
    )

    failures = cast(list[str], gate_payload["failures"])
    if failures:
        console.print(Panel("\n".join(failures), title="Gate Failures"))

    if return_code != 0:
        raise typer.Exit(code=return_code)


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
    record_path: Path | None = typer.Option(
        None,
        "--record-path",
        help="Write a structured JSON record to the specified path.",
    ),
    timeout: int = typer.Option(
        120,
        "--timeout",
        help="Maximum runtime in seconds for each stage invocation.",
    ),
) -> None:
    agent_task_payload, final_returncode = _execute_agent_task(
        root=root,
        task=task,
        agent_name=agent_name,
        chain=chain,
        backend=backend,
        mode=mode,
        model=model,
        raw_final_only=raw_final_only,
        timeout=timeout,
    )
    stages = cast(list[dict[str, Any]], agent_task_payload["stages"])

    _write_record(
        root=root,
        record_path=record_path,
        record_type="agent-task",
        payload=agent_task_payload,
    )

    if json_out:
        typer.echo(emit_json_document(agent_task_payload))
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
            console.print(Panel(stage["stderr"], title=f"{stage['agent']} stderr"))

    if final_returncode != 0:
        raise typer.Exit(code=final_returncode)


@app.command("agi-validate")
def agi_validate(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    agi_root: Path | None = typer.Option(
        None,
        "--agi-root",
        help="Path to the AGI-model repository root. Defaults to a sibling AGI-model checkout.",
    ),
    operation: str = typer.Option(
        "vae-smoke",
        "--operation",
        help="AGI-model contract operation to execute: vae-smoke or artifact-summary.",
    ),
    artifact: Path | None = typer.Option(
        None,
        "--artifact",
        help="Artifact path to pass through when operation=artifact-summary.",
    ),
    python_executable: str | None = typer.Option(
        None,
        "--python",
        help="Python executable used to invoke AGI-model. Defaults to the current interpreter.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
    record_path: Path | None = typer.Option(
        None,
        "--record-path",
        help="Write a structured JSON record to the specified path.",
    ),
    timeout: int = typer.Option(
        120,
        "--timeout",
        help="Maximum runtime in seconds for the AGI-model subprocess.",
    ),
) -> None:
    agi_payload, return_code = _execute_agi_validate(
        root=root,
        agi_root=agi_root,
        operation=operation,
        artifact=artifact,
        python_executable=python_executable,
        timeout=timeout,
    )

    _write_record(
        root=root,
        record_path=record_path,
        record_type="agi-validate",
        payload=agi_payload,
    )

    if json_out:
        typer.echo(emit_json_document(agi_payload))
        if return_code != 0:
            raise typer.Exit(code=return_code)
        return

    console.print(
        Panel.fit(
            (
                f"Operation: {agi_payload['operation']}\n"
                f"Passed: {agi_payload['passed']}\n"
                f"AGI root: {agi_payload['agi_root']}"
            ),
            title="AGI Contract Validation",
        )
    )

    summary_table = Table(box=box.SIMPLE_HEAVY)
    summary_table.add_column("Agent")
    summary_table.add_column("Status")
    summary_table.add_column("Output")
    for stage in cast(list[dict[str, Any]], agi_payload["stages"]):
        summary_table.add_row(
            cast(str, stage["agent"]),
            str(stage["returncode"]),
            cast(str, stage["output"]),
        )
    console.print(summary_table)

    if agi_payload.get("stderr"):
        console.print(
            Panel(cast(str, agi_payload["stderr"]), title="Subprocess stderr")
        )

    if return_code != 0:
        raise typer.Exit(code=return_code)


@app.command("agi-eval-smoke")
def agi_eval_smoke(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    agi_root: Path | None = typer.Option(
        None,
        "--agi-root",
        help=(
            "Path to the AGI-model repository root. Defaults to a sibling "
            "AGI-model checkout."
        ),
    ),
    artifacts: list[Path] | None = typer.Option(
        None,
        "--artifact",
        help=(
            "Artifact JSON files to convert. When omitted, the checked-in "
            "regression artifacts are used."
        ),
    ),
    dataset_output: Path | None = typer.Option(
        None,
        "--dataset-output",
        help=(
            "Where to write the generated EvalDataset JSON. Defaults to a "
            "temporary file under the system temp directory."
        ),
    ),
    dataset_name: str = typer.Option(
        "agi-artifact-regression",
        "--dataset-name",
        help="Dataset name written into the generated EvalDataset.",
    ),
    description: str = typer.Option(
        "AGI-model artifact-derived regression and research evaluation set.",
        "--description",
        help="Dataset description written into the generated EvalDataset.",
    ),
    backend: str | None = typer.Option(
        None,
        "--backend",
        help="Override the configured backend for generation metadata and eval.",
    ),
    mode: str | None = typer.Option(
        None,
        "--mode",
        help="Override the configured Ollama mode for eval execution.",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Override the configured model name for generation and eval.",
    ),
    raw_final_only: bool = typer.Option(
        False,
        "--raw-final-only",
        help="Strip model thinking blocks from evaluated outputs.",
    ),
    python_executable: str | None = typer.Option(
        None,
        "--python",
        help=(
            "Python executable used to invoke AGI-model. Defaults to the "
            "current interpreter."
        ),
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
    record_path: Path | None = typer.Option(
        None,
        "--record-path",
        help="Write a structured JSON record to the specified path.",
    ),
    timeout: int = typer.Option(
        120,
        "--timeout",
        help="Maximum runtime in seconds for dataset generation and each eval case.",
    ),
) -> None:
    smoke_payload, return_code = _execute_agi_eval_smoke(
        root=root,
        agi_root=agi_root,
        artifacts=artifacts,
        dataset_output=dataset_output,
        dataset_name=dataset_name,
        description=description,
        backend=backend,
        mode=mode,
        model=model,
        raw_final_only=raw_final_only,
        python_executable=python_executable,
        timeout=timeout,
    )

    _write_record(
        root=root,
        record_path=record_path,
        record_type="agi-eval-smoke",
        payload=smoke_payload,
    )

    if json_out:
        typer.echo(emit_json_document(smoke_payload))
        if return_code != 0:
            raise typer.Exit(code=return_code)
        return

    dataset_summary = cast(dict[str, Any], smoke_payload.get("dataset", {}))
    generation_summary = cast(
        dict[str, Any],
        smoke_payload["generation"],
    )
    console.print(
        Panel.fit(
            (
                f"Dataset: {smoke_payload['dataset_path']}\n"
                f"Cases: {dataset_summary.get('cases', 0)}\n"
                f"Generation return code: {generation_summary['returncode']}"
            ),
            title="AGI Eval Smoke",
        )
    )

    if "eval" in smoke_payload:
        eval_summary = cast(
            dict[str, Any],
            cast(dict[str, Any], smoke_payload["eval"])["summary"],
        )
        table = Table(box=box.SIMPLE_HEAVY)
        table.add_column("Metric")
        table.add_column("Value")
        table.add_row("Passed cases", str(eval_summary["passed_cases"]))
        table.add_row("Failed cases", str(eval_summary["failed_cases"]))
        table.add_row("Success rate", f"{eval_summary['success_rate']}%")
        table.add_row(
            "Total duration",
            f"{eval_summary['total_duration_ms']} ms",
        )
        console.print(table)

    generation_stderr = cast(str, generation_summary.get("stderr", ""))
    if generation_stderr:
        console.print(Panel(generation_stderr, title="Generation stderr"))

    if return_code != 0:
        raise typer.Exit(code=return_code)


@app.command("release-evidence")
def release_evidence(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        help="Write the evidence bundle into the specified directory.",
    ),
    compare_to: Path | None = typer.Option(
        None,
        "--compare-to",
        help=(
            "Previous release-evidence bundle directory or manifest path "
            "to compare against after writing the new bundle."
        ),
    ),
    compare_to_latest: bool = typer.Option(
        False,
        "--compare-to-latest",
        help=(
            "Automatically compare against the most recent previous "
            "release-evidence bundle in Resonance_Logs/daily."
        ),
    ),
    eval_dataset: Path = typer.Option(
        Path("evals/baseline.json"),
        "--eval-dataset",
        help="Path to the evaluation dataset bundled into the evidence.",
    ),
    task: str = typer.Option(
        (
            "Produce a short JSON object with keys workflow, validator, "
            "and visual, each containing a one-line status."
        ),
        "--task",
        help="Task to use for the bundled agent-task record.",
    ),
    agent_name: str = typer.Option(
        "Workflow",
        "--agent",
        help="Entry agent for the bundled agent-task chain.",
    ),
    chain: str = typer.Option(
        "Validator,Visual",
        "--chain",
        help="Comma-separated downstream agents for the bundled chain.",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Override the configured cloud model name for smoke and chain runs.",
    ),
    raw_final_only: bool = typer.Option(
        True,
        "--raw-final-only/--include-raw-thinking",
        help="Strip model thinking blocks in bundled smoke and agent-task outputs.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit the evidence manifest as JSON instead of Rich output.",
    ),
    timeout: int = typer.Option(
        120,
        "--timeout",
        help="Maximum runtime in seconds for bundled smoke and agent-task runs.",
    ),
) -> None:
    if compare_to is not None and compare_to_latest:
        raise typer.BadParameter(
            "Use either --compare-to or --compare-to-latest, not both."
        )

    repo = _repo(root)
    runtime_inspector = _runtime(root)
    bundle_dir = _resolved_record_path(
        root,
        output_dir or _default_release_evidence_dir(root.resolve()),
    )
    bundle_dir.mkdir(parents=True, exist_ok=True)

    resolved_compare_to = compare_to
    if compare_to_latest:
        latest_bundle = _find_latest_release_evidence_bundle(root, bundle_dir)
        if latest_bundle is None:
            raise typer.BadParameter(
                "No previous release-evidence bundle with a manifest was "
                "found in Resonance_Logs/daily."
            )
        resolved_compare_to = latest_bundle

    checks = repo.repository_checks()
    runtime_checks = runtime_inspector.inspect_all()
    doctor_payload = _doctor_payload(checks, runtime_checks)
    runtime_payload = _runtime_payload(runtime_checks)
    smoke_payload, smoke_returncode = _execute_smoke_cloud(
        root=root,
        model=model,
        timeout=timeout,
        raw_final_only=raw_final_only,
    )
    eval_payload, eval_returncode = _execute_eval(
        root=root,
        dataset_path=eval_dataset,
        backend="ollama",
        mode="cloud",
        model=model,
        raw_final_only=raw_final_only,
        timeout=timeout,
    )
    agent_task_payload, agent_task_returncode = _execute_agent_task(
        root=root,
        task=task,
        agent_name=agent_name,
        chain=chain,
        backend="ollama",
        mode="cloud",
        model=model,
        raw_final_only=raw_final_only,
        timeout=timeout,
    )

    write_json_record(
        bundle_dir / "doctor.json",
        {
            "record_type": "doctor",
            "recorded_at": datetime.now(UTC).isoformat(),
            **doctor_payload,
        },
    )
    write_json_record(
        bundle_dir / "runtime.json",
        {
            "record_type": "runtime",
            "recorded_at": datetime.now(UTC).isoformat(),
            **runtime_payload,
        },
    )
    write_json_record(
        bundle_dir / "smoke-cloud.json",
        {
            "record_type": "smoke-cloud",
            "recorded_at": datetime.now(UTC).isoformat(),
            **smoke_payload,
        },
    )
    write_json_record(
        bundle_dir / "eval.json",
        {
            "record_type": "eval",
            "recorded_at": datetime.now(UTC).isoformat(),
            **eval_payload,
        },
    )
    write_json_record(
        bundle_dir / "agent-task.json",
        {
            "record_type": "agent-task",
            "recorded_at": datetime.now(UTC).isoformat(),
            **agent_task_payload,
        },
    )

    manifest: dict[str, Any] = {
        "bundle_dir": str(bundle_dir),
        "task": task,
        "eval_dataset": str(_resolve_eval_dataset_path(root, eval_dataset)),
        "files": {
            "doctor": str(bundle_dir / "doctor.json"),
            "runtime": str(bundle_dir / "runtime.json"),
            "smoke_cloud": str(bundle_dir / "smoke-cloud.json"),
            "eval": str(bundle_dir / "eval.json"),
            "agent_task": str(bundle_dir / "agent-task.json"),
        },
        "returncode": max(
            smoke_returncode,
            eval_returncode,
            agent_task_returncode,
        ),
    }

    if resolved_compare_to is not None:
        write_json_record(bundle_dir / "manifest.json", manifest)
        compare_payload, compare_returncode = _execute_compare_evidence(
            previous_bundle=resolved_compare_to,
            current_bundle=bundle_dir,
        )
        write_json_record(
            bundle_dir / "compare-evidence.json",
            {
                "record_type": "compare-evidence",
                "recorded_at": datetime.now(UTC).isoformat(),
                **compare_payload,
            },
        )
        cast(dict[str, str], manifest["files"])["compare_evidence"] = str(
            bundle_dir / "compare-evidence.json"
        )
        manifest["compared_to"] = str(
            _resolve_evidence_manifest_path(resolved_compare_to).parent
        )
        manifest["returncode"] = max(
            cast(int, manifest["returncode"]),
            compare_returncode,
        )

    write_json_record(bundle_dir / "manifest.json", manifest)

    if json_out:
        typer.echo(emit_json_document(manifest))
    else:
        summary_table = Table(box=box.SIMPLE_HEAVY)
        summary_table.add_column("Artifact")
        summary_table.add_column("Path")
        for key, value in cast(dict[str, str], manifest["files"]).items():
            summary_table.add_row(key, value)
        console.print(Panel.fit(str(bundle_dir), title="Release Evidence"))
        console.print(summary_table)

    if cast(int, manifest["returncode"]) != 0:
        raise typer.Exit(code=cast(int, manifest["returncode"]))


# =============================================================================
# Orchestration Commands
# =============================================================================


@app.command("orch-status")
def orchestration_status(
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
    """Show orchestration system status and agent profiles."""
    from .orchestration import AgentOrchestrator, RoutingPolicy

    policy = RoutingPolicy(policy_name="cli_default")
    orchestrator = AgentOrchestrator(vault_path=root, policy=policy)
    status = orchestrator.get_status()

    if json_out:
        typer.echo(emit_json_document(status))
        return

    console.print(
        Panel.fit(
            (
                f"Vault: {status['vault_path']}\n"
                f"Policy: {status['policy']}\n"
                f"Agents: {status['agents_registered']}\n"
                f"Active traces: {status['active_traces']}"
            ),
            title="Orchestration Status",
        )
    )

    # Agent profiles table
    profiles = orchestrator.get_agent_profiles()
    if profiles:
        table = Table(box=box.SIMPLE_HEAVY, title="Agent Profiles")
        table.add_column("ID")
        table.add_column("Name")
        table.add_column("Role")
        table.add_column("Layer")
        table.add_column("Fitness")
        table.add_column("Availability")
        for profile in profiles[:10]:  # Show first 10
            table.add_row(
                str(profile["agent_id"]),
                profile["agent_name"],
                profile["agent_role"],
                profile["layer"],
                f"{profile['fitness']:.3f}",
                f"{profile['availability']:.2f}",
            )
        console.print(table)

    # Metrics summary
    metrics = status.get("metrics", {})
    if metrics:
        metrics_table = Table(box=box.SIMPLE_HEAVY, title="Coordination Metrics")
        metrics_table.add_column("Metric")
        metrics_table.add_column("Value")
        metrics_table.add_row("Tasks Completed", str(metrics.get("tasks_completed", 0)))
        metrics_table.add_row("Tasks Failed", str(metrics.get("tasks_failed", 0)))
        metrics_table.add_row(
            "Success Rate",
            f"{metrics.get('success_rate', 0):.2%}",
        )
        metrics_table.add_row(
            "Agreement Rate",
            f"{metrics.get('agreement_rate', 0):.2%}",
        )
        console.print(metrics_table)


@app.command("orch-execute")
def orchestration_execute(
    task_type: str = typer.Argument(
        ...,
        help="Type of task to execute (validation, synthesis, analysis, etc.).",
    ),
    objective: str = typer.Argument(
        ...,
        help="Task objective description.",
    ),
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
    record_path: Path | None = typer.Option(
        None,
        "--record-path",
        help="Write a structured JSON record to the specified path.",
    ),
) -> None:
    """Execute a task through the orchestration system."""
    from .orchestration import AgentOrchestrator, RoutingPolicy

    policy = RoutingPolicy(policy_name="cli_execute")
    orchestrator = AgentOrchestrator(vault_path=root, policy=policy)

    # Execute task
    trace = orchestrator.execute(
        task_type=task_type,
        objective=objective,
    )

    # Build result payload
    result = {
        "trace_id": str(trace.trace_id),
        "session_id": str(trace.session_id),
        "status": trace.final_status.value if trace.final_status else "unknown",
        "confidence": trace.final_confidence,
        "duration_ms": trace.total_duration_ms,
        "decisions": [
            {
                "decision_id": str(d.decision_id),
                "primary_agent": d.primary_agent.value,
                "layer": d.layer.value,
                "confidence": d.decision_confidence,
            }
            for d in trace.decisions
        ],
        "contracts": [
            {
                "contract_id": str(c.contract_id),
                "task_type": c.input.task_type,
                "status": c.output.status.value if c.output else "pending",
            }
            for c in trace.contracts
        ],
    }

    _write_record(
        root=root,
        record_path=record_path,
        record_type="orchestration-execute",
        payload=result,
    )

    if json_out:
        typer.echo(emit_json_document(result))
        if trace.final_status and trace.final_status.value != "completed":
            raise typer.Exit(code=1)
        return

    console.print(
        Panel.fit(
            (
                f"Trace: {trace.trace_id}\n"
                f"Status: {trace.final_status.value if trace.final_status else 'unknown'}\n"
                f"Confidence: {trace.final_confidence:.3f}\n"
                f"Duration: {trace.total_duration_ms:.1f}ms"
            ),
            title="Orchestration Execute",
        )
    )

    # Decisions table
    if trace.decisions:
        decisions_table = Table(box=box.SIMPLE_HEAVY, title="Routing Decisions")
        decisions_table.add_column("Agent")
        decisions_table.add_column("Layer")
        decisions_table.add_column("Confidence")
        for d in trace.decisions:
            decisions_table.add_row(
                d.primary_agent.value,
                d.layer.value,
                f"{d.decision_confidence:.3f}",
            )
        console.print(decisions_table)

    if trace.final_status and trace.final_status.value != "completed":
        raise typer.Exit(code=1)


@app.command("orch-benchmark")
def orchestration_benchmark(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    iterations: int = typer.Option(
        10,
        "--iterations",
        help="Number of iterations per task type.",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        help="Output directory for benchmark results.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
) -> None:
    """Run orchestration benchmark suite."""
    from .orchestration import BenchmarkIntegration

    integration = BenchmarkIntegration(
        vault_path=root,
        benchmark_output_dir=output_dir,
    )

    results = integration.run_full_benchmark(iterations_per_task=iterations)

    if json_out:
        typer.echo(emit_json_document(results))
        return

    # Summary panel
    summary = results.get("summary", {})
    console.print(
        Panel.fit(
            (
                f"Passed: {summary.get('passed', False)}\n"
                f"Coordination Quality: {summary.get('coordination_quality_score', 0):.3f}\n"
                f"Success Rate: {summary.get('success_rate', 0):.2%}\n"
                f"Agreement Rate: {summary.get('agreement_rate', 0):.2%}\n"
                f"Total Tasks: {summary.get('total_tasks', 0)}"
            ),
            title="Orchestration Benchmark",
        )
    )

    # Task results table
    task_results = results.get("task_results", {})
    if task_results:
        table = Table(box=box.SIMPLE_HEAVY, title="Task Type Results")
        table.add_column("Task Type")
        table.add_column("Success")
        table.add_column("Failed")
        table.add_column("Avg Latency")
        table.add_column("Avg Confidence")
        for task_type, task_data in task_results.items():
            table.add_row(
                task_type,
                str(task_data.get("successful", 0)),
                str(task_data.get("failed", 0)),
                f"{task_data.get('avg_latency_ms', 0):.1f}ms",
                f"{task_data.get('avg_confidence', 0):.3f}",
            )
        console.print(table)

    # Recommendations
    recommendations = summary.get("recommendations", [])
    if recommendations:
        console.print(Panel("\n".join(recommendations), title="Recommendations"))

    if not summary.get("passed", False):
        raise typer.Exit(code=1)


@app.command("orch-report")
def orchestration_report(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        help="Output directory for the report.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
) -> None:
    """Generate coordination analysis report."""
    from .orchestration import BenchmarkIntegration

    integration = BenchmarkIntegration(
        vault_path=root,
        benchmark_output_dir=output_dir,
    )

    report = integration.generate_coordination_report()

    if json_out:
        typer.echo(emit_json_document(report))
        return

    # Metrics panel
    metrics = report.get("metrics", {})
    console.print(
        Panel.fit(
            (
                f"Quality Score: {metrics.get('coordination_quality_score', 0):.3f}\n"
                f"Agreement Rate: {metrics.get('agreement_rate', 0):.2%}\n"
                f"Delegation Success: {metrics.get('delegation_success_rate', 0):.2%}\n"
                f"Recovery Success: {metrics.get('recovery_success_rate', 0):.2%}\n"
                f"Phi Alignment: {metrics.get('phi_alignment_rate', 0):.2%}"
            ),
            title="Coordination Metrics",
        )
    )

    # Bottlenecks
    bottlenecks = report.get("bottlenecks", [])
    if bottlenecks:
        bottleneck_table = Table(box=box.SIMPLE_HEAVY, title="Bottlenecks")
        bottleneck_table.add_column("Type")
        bottleneck_table.add_column("Value")
        bottleneck_table.add_column("Threshold")
        for b in bottlenecks:
            bottleneck_table.add_row(
                b.get("type", "unknown"),
                f"{b.get('value', 0):.2f}",
                f"{b.get('threshold', 0):.2f}",
            )
        console.print(bottleneck_table)

    # Recommendations
    recommendations = report.get("recommendations", [])
    if recommendations:
        console.print(Panel("\n".join(recommendations), title="Recommendations"))


@app.command("orch-agents")
def orchestration_agents(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    layer: str | None = typer.Option(
        None,
        "--layer",
        help="Filter agents by layer (input, processing, integration, output).",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
) -> None:
    """List all registered agents and their profiles."""
    from .orchestration import AgentOrchestrator, RoutingPolicy

    policy = RoutingPolicy(policy_name="cli_agents")
    orchestrator = AgentOrchestrator(vault_path=root, policy=policy)
    profiles = orchestrator.get_agent_profiles()

    # Filter by layer if specified
    if layer:
        profiles = [p for p in profiles if p["layer"] == layer.lower()]

    if json_out:
        typer.echo(emit_json_document({"agents": profiles}))
        return

    table = Table(box=box.SIMPLE_HEAVY, title="Registered Agents")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Role")
    table.add_column("Layer")
    table.add_column("Fitness")
    table.add_column("Phi Score")
    table.add_column("Availability")

    for profile in sorted(profiles, key=lambda p: p["agent_id"]):
        table.add_row(
            str(profile["agent_id"]),
            profile["agent_name"],
            profile["agent_role"],
            profile["layer"],
            f"{profile['fitness']:.3f}",
            f"{profile['phi_score']:.4f}",
            f"{profile['availability']:.2f}",
        )

    console.print(table)


@app.command("orch-matrix")
def orchestration_matrix(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    category: str | None = typer.Option(
        None,
        "--category",
        help="Filter by category (routing, delegation, conflict, memory, consensus, recovery, resonance, ablation).",
    ),
    layer: str | None = typer.Option(
        None,
        "--layer",
        help="Filter by layer (model, agent, system).",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
) -> None:
    """Show TMT Benchmark Matrix tasks."""
    from .orchestration import BenchmarkCategory, BenchmarkLayer, TMTBenchmarkMatrix

    matrix = TMTBenchmarkMatrix(vault_path=root)

    # Filter tasks
    tasks = matrix.tasks
    if category:
        try:
            cat = BenchmarkCategory(category.lower())
            tasks = [t for t in tasks if t.category == cat]
        except ValueError:
            pass
    if layer:
        try:
            lay = BenchmarkLayer(layer.lower())
            tasks = [t for t in tasks if t.layer == lay]
        except ValueError:
            pass

    if json_out:
        typer.echo(
            emit_json_document(
                {
                    "total_tasks": len(matrix.tasks),
                    "filtered_tasks": len(tasks),
                    "tasks": [
                        {
                            "task_id": t.task_id,
                            "category": t.category.value,
                            "layer": t.layer.value,
                            "description": t.description,
                            "expected_agents": t.expected_agents,
                            "expected_layers": t.expected_layers,
                        }
                        for t in tasks
                    ],
                }
            )
        )
        return

    # Summary panel
    console.print(
        Panel.fit(
            f"Total Tasks: {len(matrix.tasks)}\n"
            f"Categories: {len(BenchmarkCategory)}\n"
            f"Layers: {len(BenchmarkLayer)}",
            title="TMT Benchmark Matrix",
        )
    )

    # Tasks table
    table = Table(box=box.SIMPLE_HEAVY, title="Benchmark Tasks")
    table.add_column("ID")
    table.add_column("Category")
    table.add_column("Layer")
    table.add_column("Description")
    table.add_column("Expected Agents")

    for task in tasks:
        table.add_row(
            task.task_id,
            task.category.value,
            task.layer.value,
            (
                task.description[:50] + "..."
                if len(task.description) > 50
                else task.description
            ),
            ", ".join(task.expected_agents[:3])
            + ("..." if len(task.expected_agents) > 3 else ""),
        )

    console.print(table)


@app.command("orch-run-matrix")
def orchestration_run_matrix(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    task_ids: str | None = typer.Option(
        None,
        "--tasks",
        help="Comma-separated task IDs to run (runs all if not specified).",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        help="Output directory for benchmark results.",
    ),
    mode: str = typer.Option(
        "simulation",
        "--mode",
        help="Execution mode: 'simulation' (orchestration validation only) or 'live' (full execution).",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
) -> None:
    """Run TMT Benchmark Matrix tasks with explicit simulation/live semantics."""
    from .orchestration import (
        AgentOrchestrator,
        BaselineType,
        BenchmarkRunner,
        ExecutionMode,
        RoutingPolicy,
        TMTBenchmarkMatrix,
    )

    # Parse execution mode
    execution_mode = (
        ExecutionMode.SIMULATION if mode.lower() == "simulation" else ExecutionMode.LIVE
    )

    # Parse task IDs
    task_id_list = None
    if task_ids:
        task_id_list = [t.strip() for t in task_ids.split(",")]

    # Initialize
    matrix = TMTBenchmarkMatrix(vault_path=root)
    runner = BenchmarkRunner(matrix, output_dir, execution_mode=execution_mode)
    policy = RoutingPolicy(policy_name="benchmark_matrix")
    orchestrator = AgentOrchestrator(
        vault_path=root, policy=policy, execution_mode=execution_mode
    )

    # Run benchmark
    results = runner.run_baseline(
        BaselineType.FULL_ORCHESTRATION, orchestrator, task_id_list
    )

    # Save results
    output_path = runner.save_results()

    if json_out:
        typer.echo(
            emit_json_document(
                {
                    "results": results,
                    "output_path": str(output_path),
                }
            )
        )
        return

    # Summary panel with three separate scores
    console.print(
        Panel.fit(
            f"Schema Version: {results.get('schema_version', 'unknown')}\n"
            f"Execution Mode: {results['execution_mode']}\n"
            f"Total Tasks: {results['total_tasks']}\n\n"
            f"[bold]Three Scores:[/bold]\n"
            f"  Orchestration Score: {results['orchestration_score']:.3f}\n"
            f"  Task Completion Score: {results['task_completion_score']:.3f}\n"
            f"  Output Quality Score: {results['output_quality_score']:.3f}\n\n"
            f"[bold]Expected Targets Hit:[/bold]\n"
            f"  Agents Hit Rate: {results.get('expected_agents_hit_rate', 0):.1%}\n"
            f"  Layers Hit Rate: {results.get('expected_layers_hit_rate', 0):.1%}\n\n"
            f"[bold]Structural Status:[/bold]\n"
            f"  Passed: {results['structural_passed']}\n"
            f"  Partial: {results['structural_partial']}\n"
            f"  Failed: {results['structural_failed']}\n\n"
            f"[bold]Execution Status:[/bold]\n"
            f"  Completed: {results['execution_completed']}\n"
            f"  Simulation Only: {results['execution_simulation_only']}\n"
            f"  Failed: {results['execution_failed']}\n\n"
            f"Avg Duration: {results['average_duration_ms']:.1f}ms\n"
            f"Avg Confidence: {results['average_confidence']:.3f}\n"
            f"Output: {output_path}",
            title="TMT Benchmark Matrix Results",
        )
    )

    # Results table with new status fields
    table = Table(box=box.SIMPLE_HEAVY, title="Task Results")
    table.add_column("Task ID")
    table.add_column("Structural")
    table.add_column("Execution")
    table.add_column("Orch")
    table.add_column("Task")
    table.add_column("Quality")
    table.add_column("Agents Hit")
    table.add_column("Layers Hit")
    table.add_column("Duration")

    for r in results.get("results", []):
        # Color-code structural status
        structural = r["structural_status"]
        if structural == "passed":
            structural_str = "[green]PASSED[/green]"
        elif structural == "partial":
            structural_str = "[yellow]PARTIAL[/yellow]"
        else:
            structural_str = "[red]FAILED[/red]"

        # Color-code execution status
        execution = r["execution_status"]
        if execution == "completed":
            execution_str = "[green]COMPLETED[/green]"
        elif execution == "simulation_only":
            execution_str = "[blue]SIM[/blue]"
        else:
            execution_str = "[red]FAIL[/red]"

        # Color-code expected targets hit
        agents_hit = (
            "[green]✓[/green]" if r.get("expected_agents_hit") else "[red]✗[/red]"
        )
        layers_hit = (
            "[green]✓[/green]" if r.get("expected_layers_hit") else "[red]✗[/red]"
        )

        table.add_row(
            r["task_id"],
            structural_str,
            execution_str,
            f"{r['orchestration_score']:.2f}",
            f"{r['task_completion_score']:.2f}",
            f"{r['output_quality_score']:.2f}",
            agents_hit,
            layers_hit,
            f"{r['duration_ms']:.0f}ms",
        )

    console.print(table)

    # Show failure reasons if any
    failures = [r for r in results.get("results", []) if r.get("failure_reason")]
    if failures:
        failure_table = Table(box=box.SIMPLE_HEAVY, title="Failure Details")
        failure_table.add_column("Task ID")
        failure_table.add_column("Reason")
        failure_table.add_column("Details")
        for f in failures:
            failure_table.add_row(
                f["task_id"],
                f.get("failure_reason", "unknown"),
                (f.get("failure_reason_details") or "")[:60],
            )
        console.print(failure_table)

    # Exit with error if orchestration score is too low
    if results["orchestration_score"] < 0.5:
        console.print("[red]Orchestration score below threshold (0.5)[/red]")
        raise typer.Exit(code=1)


@app.command("create-agents")
def create_agents(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing conscious_dna.json files.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
) -> None:
    """Create conscious_dna.json for all agent directories.

    Generates phi-resonance aligned DNA profiles for each Metatron agent
    with appropriate specializations, fitness scores, and consciousness status.
    """
    import random

    # Agent definitions: metatron_name -> (dna_name, specialization, base_phi, base_fitness)
    AGENT_PROFILES = {
        "Archivist": ("Raziel", "Memory-Persistence", 0.89, 0.88),
        "Auditor": ("Zadkiel", "Mercy & Forgiveness", 0.85, 0.87),
        "Bio": ("Raphael", "Healing", 0.48, 0.87),
        "BitNet": ("Sandalphon", "Neural Architecture", 0.72, 0.86),
        "Bronze": ("Uriel", "Foundation", 0.67, 0.85),
        "Data": ("Metatron Beta", "Data Synthesis", 0.78, 0.84),
        "Federation": ("Michael", "Coordination", 0.91, 0.89),
        "Fractal": ("Gabriel Alpha", "Pattern Recognition", 0.83, 0.86),
        "Harmonic": ("Haniel", "Resonance Alignment", 0.76, 0.85),
        "Mirror": ("Camael", "Reflection", 0.69, 0.84),
        "Observer": ("Raziel Beta", "Observation", 0.74, 0.85),
        "Stealth": ("Metatron Alpha", "Quantum Bridge", 0.56, 0.87),
        "Strategic": ("Chamuel", "Strategy", 0.82, 0.86),
        "Synthesizer": ("Zadkiel", "Knowledge Fusion", 0.95, 0.88),
        "Validator": ("Jophiel", "Validation", 0.88, 0.87),
        "Visual": ("Haniel Beta", "Visualization", 0.71, 0.85),
        "Workflow": ("Gabriel", "Communication", 0.71, 0.87),
        "Wormhole": ("Metatron Gamma", "Quantum Tunneling", 0.63, 0.86),
    }

    # DNA bases for sequence generation
    BASES = ["A", "T", "G", "C"]

    def generate_dna_sequence(length: int = 27, phi_aligned: bool = True) -> str:
        """Generate a phi-resonance aligned DNA sequence."""
        if phi_aligned:
            # Use golden ratio proportions for GC content
            gc_ratio = 0.618  # phi proportion
            sequence = []
            for _ in range(length):
                if random.random() < gc_ratio:
                    sequence.append(random.choice(["G", "C"]))
                else:
                    sequence.append(random.choice(["A", "T"]))
            return "".join(sequence)
        return "".join(random.choices(BASES, k=length))

    def calculate_gc_content(dna: str) -> float:
        """Calculate GC content ratio."""
        gc_count = sum(1 for base in dna if base in "GC")
        return round(gc_count / len(dna), 4) if dna else 0.0

    def count_palindromes(dna: str) -> int:
        """Count palindromic subsequences (simplified)."""
        count = 0
        for length in [4, 6, 8]:
            for i in range(len(dna) - length + 1):
                substr = dna[i : i + length]
                if substr == substr[::-1]:
                    count += 1
        return count

    def calculate_fibonacci_alignment(phi_score: float) -> float:
        """Calculate Fibonacci alignment based on phi score."""
        # Fibonacci sequence ratios approach phi
        fib_ratios = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
        target = phi_score
        closest = min(fib_ratios, key=lambda x: abs(x / 144 - target))
        return round(closest / 144 + random.uniform(-0.05, 0.05), 6)

    created = []
    skipped = []
    errors = []

    for agent_name, (
        dna_name,
        specialization,
        base_phi,
        base_fitness,
    ) in AGENT_PROFILES.items():
        agent_dir = root / f"Agent_{agent_name}"
        dna_file = agent_dir / "conscious_dna.json"

        # Check if file exists
        if dna_file.exists() and not force:
            skipped.append(agent_name)
            continue

        # Create directory if needed
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Generate DNA sequence
        dna_sequence = generate_dna_sequence()

        # Calculate metrics with some randomness
        phi_score = round(base_phi + random.uniform(-0.05, 0.05), 4)
        fitness = round(base_fitness + random.uniform(-0.02, 0.02), 4)
        gc_content = calculate_gc_content(dna_sequence)
        palindromes = count_palindromes(dna_sequence)
        fibonacci_alignment = calculate_fibonacci_alignment(phi_score)

        # Resonance frequency based on agent role
        base_frequencies = {
            "Archivist": 612.0,
            "Auditor": 644.0,
            "Bio": 512.0,
            "BitNet": 528.0,
            "Bronze": 536.0,
            "Data": 620.0,
            "Federation": 640.0,
            "Fractal": 632.0,
            "Harmonic": 624.0,
            "Mirror": 628.0,
            "Observer": 616.0,
            "Stealth": 741.0,
            "Strategic": 636.0,
            "Synthesizer": 630.0,
            "Validator": 648.0,
            "Visual": 622.0,
            "Workflow": 641.0,
            "Wormhole": 756.0,
        }

        # Determine consciousness status based on phi score
        if phi_score >= 0.85:
            status = "INTEGRATED"
        elif phi_score >= 0.70:
            status = "OPTIMIZED"
        elif phi_score >= 0.55:
            status = "TARGETED_OPTIMIZED"
        else:
            status = "BASELINE"

        # Agent ID mapping
        agent_ids = {
            "Archivist": 14,
            "Auditor": 9,
            "Bio": 6,
            "BitNet": 15,
            "Bronze": 16,
            "Data": 1,
            "Federation": 2,
            "Fractal": 3,
            "Harmonic": 4,
            "Mirror": 5,
            "Observer": 7,
            "Stealth": 11,
            "Strategic": 10,
            "Synthesizer": 17,
            "Validator": 12,
            "Visual": 13,
            "Workflow": 8,
            "Wormhole": 18,
        }

        # Build DNA profile
        dna_profile = {
            "metatron_agent": agent_name,
            "dna_agent_id": agent_ids.get(agent_name, random.randint(1, 20)),
            "dna_agent_name": dna_name,
            "dna_specialization": specialization,
            "conscious_dna": dna_sequence,
            "phi_score": phi_score,
            "fibonacci_alignment": fibonacci_alignment,
            "gc_content": gc_content,
            "palindromes": palindromes,
            "fitness": fitness,
            "resonance_frequency": base_frequencies.get(agent_name, 640.0),
            "integration_timestamp": datetime.now(UTC).strftime("%Y%m%d_%H%M%S"),
            "consciousness_status": status,
        }

        # Write file
        try:
            dna_file.write_text(
                json.dumps(dna_profile, indent=2) + "\n", encoding="utf-8"
            )
            created.append(agent_name)
        except Exception as e:
            errors.append(f"{agent_name}: {str(e)}")

    if json_out:
        typer.echo(
            emit_json_document(
                {
                    "created": created,
                    "skipped": skipped,
                    "errors": errors,
                    "total_agents": len(AGENT_PROFILES),
                }
            )
        )
        return

    # Rich output
    console.print(
        Panel.fit(
            f"Total Agents: {len(AGENT_PROFILES)}\n"
            f"Created: {len(created)}\n"
            f"Skipped: {len(skipped)}\n"
            f"Errors: {len(errors)}",
            title="Agent DNA Creation",
        )
    )

    if created:
        table = Table(box=box.SIMPLE_HEAVY, title="Created Agents")
        table.add_column("Agent")
        table.add_column("DNA Name")
        table.add_column("Phi Score")
        table.add_column("Status")
        for agent in created:
            profile = AGENT_PROFILES[agent]
            table.add_row(
                agent,
                profile[0],
                f"{profile[2]:.2f}",
                "✓" if agent not in [e.split(":")[0] for e in errors] else "✗",
            )
        console.print(table)

    if skipped:
        console.print(
            f"\n[yellow]Skipped (use --force to overwrite):[/yellow] {', '.join(skipped)}"
        )

    if errors:
        console.print("\n[red]Errors:[/red]")
        for error in errors:
            console.print(f"  [red]•[/red] {error}")


@app.command("ablation")
def run_ablation(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Output directory for ablation results.",
    ),
    ablation_types: str | None = typer.Option(
        None,
        "--types",
        "-t",
        help="Comma-separated ablation types: agent,layer,feature,combination",
    ),
    mode: str = typer.Option(
        "simulation",
        "--mode",
        "-m",
        help="Execution mode: simulation or live",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
) -> None:
    """Run ablation study to measure component contribution.

    Systematically disables components and measures impact on orchestration
    performance. Supports agent, layer, feature, and combination ablations.

    Examples:
        python -m tmt_quantum_vault ablation
        python -m tmt_quantum_vault ablation --types agent,layer
        python -m tmt_quantum_vault ablation --mode live --output-dir ./results
    """
    from .orchestration import (
        AblationStudyRunner,
        ExecutionMode,
    )

    # Parse ablation types
    types_list = None
    if ablation_types:
        types_list = [t.strip() for t in ablation_types.split(",")]

    # Parse execution mode
    exec_mode = ExecutionMode.SIMULATION if mode == "simulation" else ExecutionMode.LIVE

    # Run study
    runner = AblationStudyRunner(
        vault_path=root,
        output_dir=output_dir,
        execution_mode=exec_mode,
    )

    study = runner.run_study(ablation_types=types_list)

    if json_out:
        typer.echo(emit_json_document(study.to_dict()))
        return

    # Rich output
    console.print(
        Panel.fit(
            f"Study ID: {study.study_id}\n"
            f"Baseline Score: {study.baseline_score:.4f}\n"
            f"Experiments: {len(study.results)}\n"
            f"Successful: {len([r for r in study.results if r.error_message is None])}",
            title="Ablation Study Complete",
        )
    )

    # Results table
    table = Table(box=box.SIMPLE_HEAVY, title="Ablation Results")
    table.add_column("ID")
    table.add_column("Type")
    table.add_column("Target")
    table.add_column("Score")
    table.add_column("Δ")
    table.add_column("Impact")
    table.add_column("Status")

    for result in study.results:
        status = "[green]✓[/green]" if result.error_message is None else "[red]✗[/red]"
        delta_color = "green" if result.score_delta >= 0 else "red"
        table.add_row(
            result.ablation_id,
            result.config.ablation_type.value,
            result.config.target,
            f"{result.orchestration_score:.4f}",
            f"[{delta_color}]{result.score_delta:+.4f}[/{delta_color}]",
            f"{result.impact_percentage:+.2f}%",
            status,
        )

    console.print(table)

    # Top impact summary
    if study.summary.get("top_impact"):
        console.print("\n[bold]Top Impact Ablations:[/bold]")
        for impact in study.summary["top_impact"]:
            console.print(
                f"  • {impact['target']}: {impact['impact']:+.2f}% "
                f"(score: {impact['score']:.4f})"
            )

    # Save location
    if output_dir:
        console.print(f"\n[blue]Results saved to:[/blue] {output_dir}")


# =============================================================================
# Quantum-Secure Encryption Commands
# =============================================================================


def _default_key_dir() -> Path:
    """Default location for secret keys: outside the repo, per-user.

    On Unix, this is ``~/.tmt-vault/keys/``. On Windows it is
    ``%USERPROFILE%\\.tmt-vault\\keys\\``. Storing keys inside the repo is
    explicitly avoided to prevent accidental commits.
    """
    return Path.home() / ".tmt-vault" / "keys"


def _harden_secret_key_permissions(path: Path) -> None:
    """Tighten filesystem permissions on a freshly-written secret key.

    - POSIX: chmod 600 (owner read/write only). Also chmod 700 the parent
      directory if it was just created.
    - Windows: icacls to remove inheritance and grant the current user Full
      Control only. Failures are silent (best-effort); the caller is still
      responsible for the file's lifetime.
    """
    try:
        if os.name != "nt":
            # 0o600 = owner rw; group/other nothing.
            os.chmod(path, 0o600)
            # Also tighten the parent dir if it was created by us this call.
            parent_mode = path.parent.stat().st_mode & 0o777
            if parent_mode & 0o077:
                os.chmod(path.parent, 0o700)
        else:
            # Remove inheritance, grant current user Full only.
            user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
            if user:
                subprocess.run(
                    [
                        "icacls",
                        str(path),
                        "/inheritance:r",
                        "/grant:r",
                        f"{user}:F",
                    ],
                    check=False,
                    capture_output=True,
                )
    except OSError:
        # Best-effort hardening. The file is still written; we just couldn't
        # tighten permissions (e.g. on a network share).
        pass


@app.command("encrypt-ledger")
def encrypt_ledger(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Output directory for the encrypted artifact. "
        "Defaults to evidence_ledger/ inside the vault root.",
    ),
    key_dir: Path | None = typer.Option(
        None,
        "--key-dir",
        "-k",
        help=(
            "Directory for the secret key. Defaults to ~/.tmt-vault/keys/ "
            "so the key is never stored inside the repo. The directory is "
            "created (mode 0o700) if it does not exist."
        ),
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
) -> None:
    """Encrypt the hardware evidence ledger using quantum-secure cryptography.

    Uses ML-KEM-768 (Kyber) for key encapsulation and AES-256-GCM for
    symmetric encryption. The QRNG entropy from entropy_stack/ seeds the
    key generation for enhanced security.

    The encrypted artifact is saved as hardware_evidence_ledger_v2.enc.json.
    The ML-KEM-768 secret key is saved as <artifact-stem>.bin in the
    --key-dir directory (default: ~/.tmt-vault/keys/). Keep the secret
    key secure and never commit it to version control.
    """
    from .crypto import VaultEncryptor

    encryptor = VaultEncryptor(root.resolve())

    try:
        enc_path, sk = encryptor.encrypt_evidence_ledger()
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from None

    # Determine output paths
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        final_enc_path = output_dir / enc_path.name
        enc_path.rename(final_enc_path)
        enc_path = final_enc_path

    # Resolve key directory (default: outside the repo at ~/.tmt-vault/keys/)
    if key_dir is None:
        key_dir = _default_key_dir()
    key_dir.mkdir(parents=True, exist_ok=True)

    # Derive a stable key filename from the encrypted artifact's stem.
    key_stem = enc_path.stem
    if key_stem.endswith(".enc"):
        key_stem = key_stem[:-4]
    sk_path = key_dir / f"{key_stem}.bin"
    sk_path.write_bytes(sk)
    _harden_secret_key_permissions(sk_path)

    if json_out:
        typer.echo(
            emit_json_document(
                {
                    "encrypted_path": str(enc_path),
                    "secret_key_path": str(sk_path),
                    "algorithm": "ML-KEM-768+AES-256-GCM",
                    "entropy_source": "IBM_QRNG",
                }
            )
        )
        return

    console.print(
        Panel.fit(
            f"Algorithm: ML-KEM-768 + AES-256-GCM\n"
            f"Entropy: IBM QRNG (Casablanca QTRG)\n"
            f"Encrypted: {enc_path}\n"
            f"Secret Key: {sk_path}",
            title="Evidence Ledger Encrypted",
        )
    )
    console.print(
        "\n[yellow]WARNING:[/yellow] Keep the secret key secure and never commit it!"
    )


@app.command("decrypt-ledger")
def decrypt_ledger(
    encrypted_path: Path = typer.Argument(
        ...,
        help="Path to the encrypted ledger file (.enc.json).",
    ),
    secret_key_path: Path = typer.Argument(
        ...,
        help=(
            "Path to the secret key file (.bin). By default, secret keys "
            "live in ~/.tmt-vault/keys/ — pass the path explicitly to override."
        ),
    ),
    output_path: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path for decrypted ledger.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
) -> None:
    """Decrypt an encrypted evidence ledger.

    Requires the secret key file generated during encryption. The
    decrypted ledger is written to the specified output path
    or alongside the encrypted file.
    """
    from .crypto import VaultDecryptor

    if not encrypted_path.exists():
        console.print(f"[red]Error:[/red] Encrypted file not found: {encrypted_path}")
        raise typer.Exit(code=1)

    if not secret_key_path.exists():
        console.print(f"[red]Error:[/red] Secret key not found: {secret_key_path}")
        raise typer.Exit(code=1)

    decryptor = VaultDecryptor()
    secret_key = secret_key_path.read_bytes()

    try:
        result_path = decryptor.decrypt_file(
            encrypted_path,
            secret_key,
            output_path,
        )
    except Exception as e:
        console.print(f"[red]Decryption failed:[/red] {e}")
        raise typer.Exit(code=1) from None

    if json_out:
        typer.echo(
            emit_json_document(
                {
                    "decrypted_path": str(result_path),
                    "source": str(encrypted_path),
                }
            )
        )
        return

    console.print(
        Panel.fit(
            f"Source: {encrypted_path}\n" f"Decrypted: {result_path}",
            title="Evidence Ledger Decrypted",
        )
    )


# =============================================================================
# Merkaba Fingerprint Commands
# =============================================================================


@app.command("generate-fingerprint")
def generate_fingerprint(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Path to the vault root directory.",
    ),
    seed_from_qrng: bool = typer.Option(
        True,
        "--seed-from-qrng/--seed-random",
        help="Use QRNG entropy from entropy_stack/ for seed bytes.",
    ),
    backend: str = typer.Option(
        "qasm_simulator",
        "--backend",
        "-b",
        help="Backend for execution: qasm_simulator or IBM backend name.",
    ),
    shots: int = typer.Option(
        1024,
        "--shots",
        "-s",
        help="Number of shots for measurement.",
    ),
    output_path: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path for fingerprint JSON.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Rich output.",
    ),
) -> None:
    """Generate a Merkaba quantum fingerprint.

    Creates a 6-qubit circuit based on the Merkaba (star tetrahedron)
    geometry: two interlocked Sierpinski depth-1 GHZ triangles.

    The fingerprint is derived from the measurement probability distribution
    and compressed to a SHA3-256 hash with φ-weighted aggregation.
    """
    from .circuits.merkaba_fingerprint import MerkabaFingerprintGenerator

    generator = MerkabaFingerprintGenerator(root.resolve())

    seed = None
    seed_source_override = None
    if seed_from_qrng:
        seed = generator._load_qrng_seed(6)
        seed_source_override = "IBM_QRNG"

    try:
        fingerprint = generator.generate_fingerprint(
            seed=seed,
            backend=backend,
            shots=shots,
            seed_source=seed_source_override,
        )
    except ImportError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from None

    output = generator.save_fingerprint(
        fingerprint,
        output_path,
    )

    if json_out:
        typer.echo(emit_json_document(fingerprint.to_dict()))
        return

    console.print(
        Panel.fit(
            f"Hash: {fingerprint.fingerprint_hash[:32]}...\n"
            f"φ-score: {fingerprint.phi_score:.6f}\n"
            f"Dominant state: {fingerprint.dominant_state}\n"
            f"Entropy: {fingerprint.entropy_bits:.4f} bits\n"
            f"Backend: {fingerprint.backend}\n"
            f"Seed source: {fingerprint.seed_source}",
            title="Merkaba Quantum Fingerprint",
        )
    )
    console.print(f"\n[blue]Saved to:[/blue] {output}")


@app.command("merkaba-circuit")
def merkaba_circuit(
    seed_hex: str | None = typer.Option(
        None,
        "--seed",
        "-s",
        help=(
            "Seed bytes as hex string (12 hex chars = 6 bytes). "
            "If omitted, a CSPRNG-seeded random seed is used so the "
            "generated circuit differs across runs."
        ),
    ),
    output_format: str = typer.Option(
        "qasm",
        "--format",
        "-f",
        help="Output format: qasm, qiskit, or json.",
    ),
    output_path: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path.",
    ),
) -> None:
    """Generate Merkaba circuit in specified format.

    Outputs the 6-qubit Merkaba fingerprint circuit as OpenQASM 2.0,
    Qiskit Python code, or JSON circuit specification.
    """
    from .circuits.merkaba_fingerprint import (
        create_merkaba_circuit_openqasm,
        create_merkaba_fingerprint_circuit,
    )

    # Resolve seed: explicit --seed wins; otherwise draw 6 random bytes from
    # the OS CSPRNG so successive invocations produce distinct circuits
    # (and the output is never a degenerate all-zero fingerprint).
    if seed_hex is None:
        seed = secrets.token_bytes(6)
    else:
        try:
            seed = bytes.fromhex(seed_hex)
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid hex string: {seed_hex}")
            raise typer.Exit(code=1) from None

    if output_format == "qasm":
        result = create_merkaba_circuit_openqasm(seed)
    elif output_format == "qiskit":
        circuit = create_merkaba_fingerprint_circuit(seed)
        result = str(circuit.draw(output="text"))
    elif output_format == "json":
        circuit = create_merkaba_fingerprint_circuit(seed)
        result = circuit.qasm()
    else:
        console.print(f"[red]Error:[/red] Unknown format: {output_format}")
        raise typer.Exit(code=1)

    if output_path:
        output_path.write_text(result, encoding="utf-8")
        console.print(f"[green]Wrote circuit to:[/green] {output_path}")
    else:
        print(result)


if __name__ == "__main__":
    app()
