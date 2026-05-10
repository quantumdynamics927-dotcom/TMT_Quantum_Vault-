"""
TMT Quantum Vault — Hugging Face Spaces Demo

Gradio interface for the 17-agent orchestration system with:
- Three-lane routing (simulation, quantum, LLM)
- Phi-resonance alignment scoring
- Real-time orchestration visualization
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Any

import gradio as gr

# Set simulation mode by default for HF Spaces
os.environ.setdefault("TMT_EXECUTION_MODE", "simulation")

from tmt_quantum_vault.orchestration import (
    AgentOrchestrator,
    RoutingPolicy,
    ExecutionMode,
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


def run_orchestration(
    task_type: str,
    objective: str,
    mode: str,
    preferred_agents: str,
) -> dict[str, Any]:
    """Execute orchestration task and return structured results."""
    if not objective.strip():
        return {"error": "Please provide an objective"}

    # Parse preferred agents
    agents_list = None
    if preferred_agents.strip():
        agents_list = [a.strip() for a in preferred_agents.split(",") if a.strip()]

    # Set execution mode
    exec_mode = ExecutionMode.SIMULATION if mode == "simulation" else ExecutionMode.LIVE

    try:
        trace = orchestrator.execute(
            task_type=task_type,
            objective=objective,
            execution_mode=exec_mode,
            preferred_agents=agents_list,
        )

        # Extract decision chain
        decisions = []
        for d in trace.decisions:
            decisions.append({
                "layer": d.layer.value,
                "primary_agent": d.primary_agent.value,
                "confidence": round(d.confidence, 4),
                "reasoning": d.reasoning[:100] + "..." if len(d.reasoning) > 100 else d.reasoning,
            })

        return {
            "orchestration_score": round(trace.orchestration_score, 4),
            "task_completion_score": round(trace.task_completion_score, 4),
            "output_quality_score": round(trace.output_quality_score, 4),
            "average_confidence": round(trace.average_confidence, 4),
            "average_resonance": round(trace.average_resonance, 4),
            "agents_involved": [d.primary_agent.value for d in trace.decisions],
            "layers_traversed": list(dict.fromkeys(d.layer.value for d in trace.decisions)),
            "handoff_count": len(trace.decisions),
            "decisions": decisions,
            "status": "success",
        }
    except Exception as e:
        return {"error": str(e), "status": "failed"}


def run_benchmark(task_ids: str) -> dict[str, Any]:
    """Run benchmark tasks and return results."""
    from tmt_quantum_vault.orchestration import (
        BenchmarkRunner,
        TMTBenchmarkMatrix,
    )

    # Parse task IDs
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
        # ⚛️ TMT Quantum Vault — Orchestration Demo
        
        **17-Agent Resonant Intelligence Lattice** with phi-aligned coordination,
        three-lane routing (simulation/quantum/LLM), and real-time orchestration tracing.
        
        > 🔒 **Private Space** — Orchestration runs in simulation mode by default.
        """
    )

    with gr.Tabs():
        # Tab 1: Orchestration
        with gr.TabItem("🎯 Orchestration"):
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
                        placeholder="Synthesizer, Validator, Observer...",
                        info="Comma-separated list of preferred agents",
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

        # Tab 2: Benchmark
        with gr.TabItem("📊 Benchmark"):
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

        # Tab 3: Agents
        with gr.TabItem("🤖 Agents"):
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

        # Tab 4: Architecture
        with gr.TabItem("📐 Architecture"):
            gr.Markdown(
                """
                ### TMT Quantum Vault Architecture
                
                **Core-13 Coordination Lattice** with **Extended-17 Operational Topology**
                
                ```
                              ┌─────────────────────────────────────┐
                              │         Agent_Synthesizer           │
                              │         (Knowledge Fusion)          │
                              │              φ = 0.95               │
                              └─────────────────────────────────────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    │                       │                       │
              ┌─────┴─────┐           ┌─────┴─────┐           ┌─────┴─────┐
              │  Observer │           │  Workflow │           │ Validator │
              │  (Watch)   │           │  (Route)   │           │  (Check)  │
              └───────────┘           └───────────┘           └───────────┘
                    │                       │                       │
              ┌─────┴─────┐           ┌─────┴─────┐           ┌─────┴─────┐
              │  Auditor   │           │ Strategic │           │  Archivist│
              │  (Audit)    │           │ (Plan)     │           │  (Store)  │
              └───────────┘           └───────────┘           └───────────┘
                    │                       │                       │
              ┌─────┴─────┐           ┌─────┴─────┐           ┌─────┴─────┐
              │   Bio      │           │  Fractal  │           │  Harmonic │
              │  (Heal)     │           │ (Pattern) │           │ (Resonate)│
              └───────────┘           └───────────┘           └───────────┘
                    │                       │                       │
              ┌─────┴─────┐           ┌─────┴─────┐           ┌─────┴─────┐
              │  Stealth   │           │  Mirror   │           │ Wormhole  │
              │  (Bridge)   │           │ (Reflect) │           │  (Tunnel) │
              └───────────┘           └───────────┘           └───────────┘
                    │                       │                       │
              ┌─────┴─────┐           ┌─────┴─────┐           ┌─────┴─────┐
              │  BitNet    │           │  Bronze   │           │ Federation│
              │  (Neural)   │           │(Foundation)│           │ (Coord)   │
              └───────────┘           └───────────┘           └───────────┘
                                            │
                                      ┌─────┴─────┐
                                      │   Data    │
                                      │ (Synthesize)
                                      └───────────┘
                ```
                
                **Three-Lane Routing:**
                - **Simulation**: Fast, free, local validation
                - **Quantum**: IBM Kingston (φ ≥ 0.618 threshold)
                - **LLM**: Ollama qwen2.5:1.5b for synthesis
                
                **Phi-Resonance Alignment:**
                - Golden ratio (φ = 1.618...) guides coordination
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