"""
TMT Quantum Vault - Hugging Face Spaces Demo

Gradio interface for the 17-agent orchestration system with:
- Three-lane routing (simulation, quantum, LLM)
- Phi-resonance alignment scoring
- Real-time orchestration visualization
"""

import inspect
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import gradio as gr

# Set simulation mode by default for HF Spaces
os.environ.setdefault("TMT_EXECUTION_MODE", "simulation")

from tmt_quantum_vault.orchestration import (
    AgentOrchestrator,
    ExecutionMode,
    RoutingPolicy,
)
from tmt_quantum_vault.repository import VaultRepository


# Initialize orchestrator
VAULT_PATH = Path("/app")
policy = RoutingPolicy(policy_name="hf_demo")
repo = VaultRepository(VAULT_PATH)
orchestrator = AgentOrchestrator(
    vault_path=VAULT_PATH,
    policy=policy,
    execution_mode=ExecutionMode.SIMULATION,
)


def get_agent_profiles() -> list[dict[str, Any]]:
    """Load agent profiles from conscious_dna.json files."""
    agents = repo.load_agents()
    return [
        {
            "name": agent.metatron_agent,
            "dna_name": agent.dna_agent_name,
            "specialization": agent.dna_specialization,
            "phi_score": round(agent.phi_score, 4),
            "fitness": round(agent.fitness, 4),
            "status": agent.consciousness_status,
        }
        for _, agent in agents
    ]


def _serialize_trace(trace: Any) -> dict[str, Any]:
    """Serialize a CoordinationTrace defensively across model versions."""
    decisions = []
    for decision in getattr(trace, "decisions", []) or []:
        layer = getattr(decision, "layer", None)
        agent = getattr(decision, "primary_agent", None)

        confidence = getattr(decision, "confidence", None)
        if confidence is None:
            confidence = getattr(decision, "decision_confidence", 0.0)

        reason = getattr(decision, "reasoning", None) or getattr(
            decision, "primary_reason", ""
        )
        reason_text = str(reason)
        if len(reason_text) > 100:
            reason_text = reason_text[:100] + "..."

        decisions.append(
            {
                "layer": getattr(layer, "value", layer),
                "primary_agent": getattr(agent, "value", agent),
                "confidence": round(float(confidence or 0.0), 4),
                "reasoning": reason_text,
            }
        )

    agents_involved = [d["primary_agent"] for d in decisions]
    layers_traversed = list(dict.fromkeys(d["layer"] for d in decisions))

    average_confidence = round(
        float(
            getattr(trace, "average_confidence", None)
            or getattr(trace, "final_confidence", 0.0)
            or 0.0
        ),
        4,
    )

    return {
        "orchestration_score": round(
            float(getattr(trace, "orchestration_score", 0.0) or 0.0), 4
        ),
        "task_completion_score": round(
            float(getattr(trace, "task_completion_score", 0.0) or 0.0), 4
        ),
        "output_quality_score": round(
            float(getattr(trace, "output_quality_score", 0.0) or 0.0), 4
        ),
        "average_confidence": average_confidence,
        "average_resonance": round(
            float(getattr(trace, "average_resonance", 0.0) or 0.0), 4
        ),
        "agents_involved": agents_involved,
        "layers_traversed": layers_traversed,
        "handoff_count": len(decisions),
        "decisions": decisions,
        "status": "success",
    }


def run_orchestration(
    task_type: str,
    objective: str,
    mode: str,
    preferred_agents: str,
) -> dict[str, Any]:
    """Execute orchestration task and return structured results."""
    if not objective.strip():
        return {"error": "Please provide an objective"}

    agents_list = None
    if preferred_agents.strip():
        agents_list = [a.strip() for a in preferred_agents.split(",") if a.strip()]

    exec_mode = (
        ExecutionMode.SIMULATION if mode == "simulation" else ExecutionMode.LIVE
    )
    orchestrator.execution_mode = exec_mode

    kwargs: dict[str, Any] = {
        "task_type": task_type,
        "objective": objective,
        "preferred_agents": agents_list,
    }

    # Backward compatibility: only pass kwargs the running execute() accepts.
    params = inspect.signature(orchestrator.execute).parameters
    if "execution_mode" in params:
        kwargs["execution_mode"] = exec_mode
    if "context" in params:
        kwargs["context"] = {"source": "hf_space", "ui_mode": mode}

    try:
        trace = orchestrator.execute(**kwargs)
        return _serialize_trace(trace)
    except Exception as e:
        return {"error": str(e), "status": "failed"}


def run_benchmark(task_ids: str) -> dict[str, Any]:
    """Run benchmark tasks and return results."""
    from tmt_quantum_vault.orchestration import (
        BenchmarkRunner,
        TMTBenchmarkMatrix,
    )

    task_id_list = None
    if task_ids.strip():
        task_id_list = [t.strip() for t in task_ids.split(",") if t.strip()]

    try:
        matrix = TMTBenchmarkMatrix(vault_path=VAULT_PATH)
        runner = BenchmarkRunner(matrix, output_dir=None)

        results = runner.run_baseline(
            baseline_type="full_orchestration",
            orchestrator=orchestrator,
            task_ids=task_id_list,
        )

        return {
            "orchestration_score": round(results.get("orchestration_score", 0), 4),
            "task_completion_score": round(results.get("task_completion_score", 0), 4),
            "output_quality_score": round(results.get("output_quality_score", 0), 4),
            "total_tasks": results.get("total_tasks", 0),
            "passed": results.get("structural_passed", 0),
            "failed": results.get("structural_failed", 0),
            "status": "success",
        }
    except Exception as e:
        return {"error": str(e), "status": "failed"}


# Build Gradio interface
with gr.Blocks(
    title="TMT Quantum Vault",
    theme=gr.themes.Soft(),
    css="""
    .agent-card { padding: 10px; border-radius: 8px; margin: 5px; }
    .phi-high { background: #d4edda; }
    .phi-mid { background: #fff3cd; }
    .phi-low { background: #f8d7da; }
    """,
) as demo:
    gr.Markdown(
        """
        # TMT Quantum Vault - Orchestration Demo

        **17-Agent Resonant Intelligence Lattice** with phi-aligned coordination,
        three-lane routing (simulation/quantum/LLM), and real-time orchestration tracing.

        > **Private Space** - Orchestration runs in simulation mode by default.
        """
    )

    with gr.Tabs():
        with gr.TabItem("Target"):
            with gr.Row():
                with gr.Column(scale=2):
                    task_type = gr.Dropdown(
                        choices=[
                            "synthesis",
                            "coordination",
                            "routing",
                            "memory",
                            "validation",
                            "observation",
                            "delegation",
                            "consensus",
                            "recovery",
                        ],
                        label="Task Type",
                        value="synthesis",
                        info="Select the orchestration task category",
                    )
                    mode = gr.Radio(
                        choices=["simulation", "live"],
                        label="Execution Mode",
                        value="simulation",
                        info="Simulation mode is safe for HF Spaces",
                    )
                    objective = gr.Textbox(
                        label="Objective",
                        placeholder="Describe the task objective...",
                        lines=3,
                        info="Enter the task objective for orchestration",
                    )
                    preferred_agents = gr.Textbox(
                        label="Preferred Agents (optional)",
                        placeholder="synthesizer, validator, observer...",
                        info="Comma-separated list of preferred agents (lowercase role names)",
                    )
                    submit_btn = gr.Button(
                        "Run Orchestration",
                        variant="primary",
                        size="lg",
                    )

                with gr.Column(scale=3):
                    output = gr.JSON(
                        label="Orchestration Result",
                        height=400,
                    )

            submit_btn.click(
                run_orchestration,
                inputs=[task_type, objective, mode, preferred_agents],
                outputs=output,
            )

        with gr.TabItem("Benchmark"):
            gr.Markdown(
                """
                ### TMT Benchmark Matrix

                Run the 19-task benchmark suite to validate orchestration behavior.
                """
            )
            with gr.Row():
                benchmark_tasks = gr.Textbox(
                    label="Task IDs (optional)",
                    placeholder="Leave empty for all tasks, or: ROUTING-001, DELEG-001...",
                    info="Comma-separated task IDs to run specific tests",
                )
                benchmark_btn = gr.Button("Run Benchmark", variant="primary")

            benchmark_output = gr.JSON(label="Benchmark Results", height=300)
            benchmark_btn.click(
                run_benchmark,
                inputs=[benchmark_tasks],
                outputs=benchmark_output,
            )

        with gr.TabItem("Agents"):
            gr.Markdown("### Registered Agent Profiles")
            agents_table = gr.Dataframe(
                value=lambda: [
                    [
                        a["name"],
                        a["dna_name"],
                        a["specialization"],
                        a["phi_score"],
                        a["fitness"],
                        a["status"],
                    ]
                    for a in get_agent_profiles()
                ],
                headers=[
                    "Agent",
                    "DNA Name",
                    "Specialization",
                    "Phi Score",
                    "Fitness",
                    "Status",
                ],
                label="17-Agent Ensemble",
                interactive=False,
            )

        with gr.TabItem("Architecture"):
            gr.Markdown(
                """
                ### TMT Quantum Vault Architecture

                **Core-13 Coordination Lattice** with **Extended-17 Operational Topology**

                ```
                              -------------------------------------
                              |         Agent_Synthesizer           |
                              |         (Knowledge Fusion)          |
                              |              phi = 0.95               |
                              --------------------------------------
                                            |
                    --------------------------|--------------------------
                    |                       |                       |
              -------------           -------------           -------------
              |  Observer |           |  Workflow |           | Validator |
              |  (Watch)   |           |  (Route)   |           |  (Check)  |
              -------------           -------------           -------------
                    |                       |                       |
              -------------           -------------           -------------
              |  Auditor   |           | Strategic |           |  Archivist|
              |  (Audit)    |           | (Plan)     |           |  (Store)  |
              -------------           -------------           -------------
                    |                       |                       |
              -------------           -------------           -------------
              |   Bio      |           |  Fractal  |           |  Harmonic |
              |  (Heal)     |           | (Pattern) |           | (Resonate)|
              -------------           -------------           -------------
                    |                       |                       |
              -------------           -------------           -------------
              |  Stealth   |           |  Mirror   |           | Wormhole  |
              |  (Bridge)   |           | (Reflect) |           |  (Tunnel) |
              -------------           -------------           -------------
                    |                       |                       |
              -------------           -------------           -------------
              |  BitNet    |           |  Bronze   |           | Federation|
              |  (Neural)   |           |(Foundation)|           | (Coord)   |
              -------------           -------------           -------------
                                            |
                                      -------------
                                      |   Data    |
                                      | (Synthesize)
                                      -------------
                ```

                **Three-Lane Routing:**
                - **Simulation**: Fast, free, local validation
                - **Quantum**: IBM Kingston (phi >= 0.618 threshold)
                - **LLM**: Ollama qwen2.5:1.5b for synthesis

                **Phi-Resonance Alignment:**
                - Golden ratio (phi = 1.618...) guides coordination
                - GC content targets ~0.618 in DNA sequences
                - Fibonacci alignment scoring for agent fitness
                """
            )

    gr.Markdown(
        """
        ---
        **TMT Quantum Vault** v0.4.0 | [GitHub](https://github.com/quantumdynamics927-dotcom/TMT_Quantum_Vault-) | MIT License
        """
    )


# Health check endpoint for Docker
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# Add health check route
demo.app.add_api_route("/health", health_check, methods=["GET"])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
