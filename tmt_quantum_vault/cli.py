# pyright: reportMissingImports=false

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any, cast

import requests
import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .ollama_api import run as ollama_run
from .models import (
    AgentDNA,
    OptimizationEntry,
    SummarySnapshot,
    ValidationResult,
)
from .output import (
    emit_json_document,
    emit_json_result,
    render_run_result,
    strip_thinking,
    write_json_record,
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
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            **payload,
        },
    )


def _doctor_payload(
    checks: list[tuple[str, str]],
    runtime_checks: list[Any],
) -> dict[str, Any]:
    has_repository_warnings = any(status == "warning" for status, _ in checks)
    has_runtime_warnings = any(
        runtime_check.status == "warning"
        for runtime_check in runtime_checks
    )
    return {
        "repository": [
            {"status": status, "detail": detail}
            for status, detail in checks
        ],
        "runtime": [
            _json_runtime_check(runtime_check)
            for runtime_check in runtime_checks
        ],
        "has_warnings": has_repository_warnings or has_runtime_warnings,
    }


def _runtime_payload(runtime_checks: list[Any]) -> dict[str, Any]:
    all_warnings = all(
        runtime_check.status == "warning"
        for runtime_check in runtime_checks
    )
    return {
        "runtime": [
            _json_runtime_check(runtime_check)
            for runtime_check in runtime_checks
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
    top_agent = cast(AgentDNA | None, summary_data["top_agent"])
    latest_optimization = cast(
        OptimizationEntry | None,
        summary_data["latest_optimization"],
    )
    model_files = cast(list[Path], summary_data["model_files"])
    return {
        "vault_name": summary_data["vault_name"],
        "consciousness_level": summary_data["consciousness_level"],
        "fibonacci_sync": summary_data["fibonacci_sync"],
        "agent_count": summary_data["agent_count"],
        "integrated_agents": summary_data["integrated_agents"],
        "memory_store_count": summary_data["memory_store_count"],
        "daily_log_count": summary_data["daily_log_count"],
        "average_fitness": summary_data["average_fitness"],
        "average_resonance_frequency": summary_data[
            "average_resonance_frequency"
        ],
        "model_count": len(model_files),
        "model_files": [path.as_posix() for path in model_files],
        "top_agent": (
            top_agent.model_dump(mode="json")
            if top_agent is not None
            else None
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
            "results": [
                _json_validation_result(result) for result in results
            ],
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
        failures.append(
            "missing required tokens: " + ", ".join(missing_required)
        )

    if case.expectation.contains_any and not any(
        token.casefold() in lowered_output
        for token in case.expectation.contains_any
    ):
        failures.append(
            "missing any-of tokens: "
            + ", ".join(case.expectation.contains_any)
        )

    present_excluded = [
        token
        for token in case.expectation.excludes
        if token.casefold() in lowered_output
    ]
    if present_excluded:
        failures.append(
            "found excluded tokens: " + ", ".join(present_excluded)
        )

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
    return json.loads(path.read_text(encoding="utf-8"))


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
                cast(dict[str, Any], previous_payload.get("dataset", {})).get(
                    "name"
                )
                if previous_payload is not None
                else None
            ),
            "current_dataset": (
                cast(dict[str, Any], current_payload.get("dataset", {})).get(
                    "name"
                )
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
        regressions.append(
            "overall bundle returncode regressed from pass to fail"
        )

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
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
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
        if (
            resolved_current is not None
            and candidate.resolve() == resolved_current
        ):
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
                (
                    stage["returncode"]
                    for stage in stages
                    if stage["returncode"] != 0
                ),
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
            artifact.resolve()
            if artifact.is_absolute()
            else (agi_root / artifact).resolve()
            for artifact in artifacts
        ]
    else:
        resolved_artifacts = [
            (agi_root / "phi_agent_report_20260310_231439.json").resolve(),
            (agi_root / "dna_quantum_analysis_results.json").resolve(),
            (
                agi_root
                / "ibm_hardware_aggregate_20260202_040836.json"
            ).resolve(),
        ]

    missing = [
        str(path)
        for path in resolved_artifacts
        if not path.exists()
    ]
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
                f"Error: {contract_result.get('error')}"
                if contract_result.get("error")
                else "No contract error reported.",
            ],
        ),
        _agi_stage_output(
            "Visual",
            _render_metric_lines(metrics)
            or ["No metrics were returned by the AGI contract."],
        ),
    ]
    for stage in stages:
        stage["returncode"] = completed.returncode if stage["agent"] == "Validator" else 0

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
    resolved_dataset_output, used_temporary_path = (
        _resolve_agi_dataset_output(resolved_agi_root, dataset_output)
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
        generation_duration_ms = int(
            (time.perf_counter() - started_at) * 1000
        )
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
    generation_duration_ms = int(
        (time.perf_counter() - started_at) * 1000
    )

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
    top_agent = cast(AgentDNA | None, summary_data["top_agent"])
    latest_optimization = cast(
        OptimizationEntry | None,
        summary_data["latest_optimization"],
    )
    model_files = cast(list[Path], summary_data["model_files"])

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


if __name__ == "__main__":
    app()


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
            cast(dict[str, Any], compare_payload["components"])[
                "smoke_cloud"
            ]["previous_returncode"]
        ),
        str(
            cast(dict[str, Any], compare_payload["components"])[
                "smoke_cloud"
            ]["current_returncode"]
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
            cast(dict[str, Any], compare_payload["components"])[
                "agent_task"
            ]["previous_returncode"]
        ),
        str(
            cast(dict[str, Any], compare_payload["components"])[
                "agent_task"
            ]["current_returncode"]
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
        (
            f"{agent_task_component['stage_count']} "
            "stages"
        ),
    )
    table.add_row(
        "comparison",
        str(comparison_component["has_regressions"]),
        (
            f"{comparison_component['regression_count']} "
            "regressions"
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
            console.print(
                Panel(stage["stderr"], title=f"{stage['agent']} stderr")
            )

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
        help=(
            "Maximum runtime in seconds for dataset generation and each eval "
            "case."
        ),
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
        help=(
            "Override the configured cloud model name for smoke and chain "
            "runs."
        ),
    ),
    raw_final_only: bool = typer.Option(
        True,
        "--raw-final-only/--include-raw-thinking",
        help=(
            "Strip model thinking blocks in bundled smoke and agent-task "
            "outputs."
        ),
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit the evidence manifest as JSON instead of Rich output.",
    ),
    timeout: int = typer.Option(
        120,
        "--timeout",
        help=(
            "Maximum runtime in seconds for bundled smoke and agent-task "
            "runs."
        ),
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
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            **doctor_payload,
        },
    )
    write_json_record(
        bundle_dir / "runtime.json",
        {
            "record_type": "runtime",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            **runtime_payload,
        },
    )
    write_json_record(
        bundle_dir / "smoke-cloud.json",
        {
            "record_type": "smoke-cloud",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            **smoke_payload,
        },
    )
    write_json_record(
        bundle_dir / "eval.json",
        {
            "record_type": "eval",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            **eval_payload,
        },
    )
    write_json_record(
        bundle_dir / "agent-task.json",
        {
            "record_type": "agent-task",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
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
                "recorded_at": datetime.now(timezone.utc).isoformat(),
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


if __name__ == "__main__":
    app()
