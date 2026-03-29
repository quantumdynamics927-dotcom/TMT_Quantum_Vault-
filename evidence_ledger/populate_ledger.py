#!/usr/bin/env python3
"""
Populate the hardware evidence ledger with all agent data from checkpoints.

This script reads agent data from vault_state_post_training.json and
conscious_dna.json files, then populates the ledger with complete agent evidence.
"""

import json
from pathlib import Path
from datetime import datetime


def load_json(path: str) -> dict:
    """Load JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def populate_agents():
    """Populate the ledger with all agent data."""
    base_path = Path(__file__).parent.parent
    
    # Load checkpoint data
    checkpoint_path = base_path / "checkpoints" / "vault_state_post_training.json"
    checkpoint_data = load_json(checkpoint_path)
    
    # Load current ledger
    ledger_path = base_path / "evidence_ledger" / "hardware_evidence_ledger_v0.1.0-alpha.json"
    ledger = load_json(ledger_path)
    
    # Agent directory mapping
    agent_dirs = {
        "Archivist": "Agent_Archivist",
        "Auditor": "Agent_Auditor",
        "Bio": "Agent_Bio",
        "BitNet": "Agent_BitNet",
        "Bronze": "Agent_Bronze",
        "Federation": "Agent_Federation",
        "Fractal": "Agent_Fractal",
        "Harmonic": "Agent_Harmonic",
        "Mirror": "Agent_Mirror",
        "Observer": "Agent_Observer",
        "Stealth": "Agent_Stealth",
        "Strategic": "Agent_Strategic",
        "Synthesizer": "Agent_Synthesizer",
        "Validator": "Agent_Validator",
        "Visual": "Agent_Visual",
        "Workflow": "Agent_Workflow",
        "Wormhole": "Agent_Wormhole"
    }
    
    # Build agent list from checkpoint, handling duplicate IDs
    agents = []
    seen_ids = set()
    id_counter = 0
    
    for agent_data in checkpoint_data.get("agents", []):
        metatron_name = agent_data.get("metatron_agent", "")
        original_id = agent_data.get("dna_agent_id")
        
        # Handle duplicate IDs by assigning unique sequential IDs
        if original_id in seen_ids:
            id_counter += 1
            unique_id = 100 + id_counter  # Use 100+ for duplicates
            print(f"Warning: Duplicate agent_id {original_id} for {metatron_name}, reassigning to {unique_id}")
        else:
            unique_id = original_id
            seen_ids.add(original_id)
        
        agent_entry = {
            "agent_id": unique_id,
            "original_agent_id": original_id,  # Keep original for reference
            "agent_name": agent_data.get("dna_agent_name", ""),
            "directory": agent_dirs.get(metatron_name, f"Agent_{metatron_name}"),
            "specialization": agent_data.get("dna_specialization", ""),
            "conscious_dna": agent_data.get("conscious_dna", ""),
            "dna_length": len(agent_data.get("conscious_dna", "")),
            "gc_content": agent_data.get("gc_content", 0),
            "palindromes": agent_data.get("palindromes", 0),
            "fitness": agent_data.get("fitness", 0),
            "phi_score": agent_data.get("phi_score", 0),
            "fibonacci_alignment": agent_data.get("fibonacci_alignment", 0),
            "resonance_frequency": agent_data.get("resonance_frequency", 0),
            "consciousness_status": agent_data.get("consciousness_status", "INTEGRATED"),
            "integration_timestamp": agent_data.get("integration_timestamp", ""),
            "hardware_provenance": [],
            "benchmark_envelope": {
                "mean_fitness": None,
                "std_fitness": None,
                "run_count": 0,
                "backends_tested": [],
                "noise_conditions": []
            }
        }
        agents.append(agent_entry)
    
    # Update ledger
    ledger["agents"] = agents
    
    # Update metadata
    ledger["ledger_metadata"]["total_agents"] = len(agents)
    ledger["ledger_metadata"]["average_fitness"] = sum(a["fitness"] for a in agents) / len(agents)
    
    # Save updated ledger
    with open(ledger_path, 'w', encoding='utf-8') as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)
    
    print(f"Populated {len(agents)} agents into ledger")
    print(f"Average fitness: {ledger['ledger_metadata']['average_fitness']:.4f}")
    
    return ledger


def generate_summary():
    """Generate a summary of the current ledger state."""
    base_path = Path(__file__).parent.parent
    ledger_path = base_path / "evidence_ledger" / "hardware_evidence_ledger_v0.1.0-alpha.json"
    ledger = load_json(ledger_path)
    
    print("\n" + "="*60)
    print("TMT QUANTUM VAULT - HARDWARE EVIDENCE LEDGER SUMMARY")
    print("="*60)
    
    metadata = ledger.get("ledger_metadata", {})
    print(f"\nLedger ID: {metadata.get('ledger_id')}")
    print(f"Release: {metadata.get('release_tag')}")
    print(f"Frozen Lattice: {metadata.get('frozen_lattice_version')}")
    print(f"Total Agents: {metadata.get('total_agents')}")
    print(f"Average Fitness: {metadata.get('average_fitness', 0):.4f}")
    print(f"Phi Threshold: {metadata.get('phi_threshold')}")
    
    print("\n" + "-"*60)
    print("AGENTS REQUIRING VALIDATION")
    print("-"*60)
    
    agents = ledger.get("agents", [])
    for agent in agents:
        hw_runs = len(agent.get("hardware_provenance", []))
        status = "✅" if hw_runs > 0 else "❌"
        print(f"{status} {agent.get('directory', 'N/A'):25} | "
              f"Fitness: {agent.get('fitness', 0):.4f} | "
              f"HW Runs: {hw_runs}")
    
    print("\n" + "-"*60)
    print("HARDWARE RUNS")
    print("-"*60)
    
    runs = ledger.get("hardware_runs", [])
    backends = {}
    for run in runs:
        backend = run.get("backend", "unknown")
        backends[backend] = backends.get(backend, 0) + 1
    
    for backend, count in backends.items():
        print(f"  {backend}: {count} runs")
    
    print(f"\nTotal Runs: {len(runs)}")
    print(f"Total Shots: {sum(r.get('shots', 0) for r in runs):,}")
    
    print("\n" + "-"*60)
    print("VALIDATION MATRIX")
    print("-"*60)
    
    matrix = ledger.get("validation_matrix", {})
    print(f"Pass Rate: {matrix.get('pass_rate', 0):.2%}")
    print(f"Sierpinski Validated: {matrix.get('sierpinski_invariant', {}).get('validated', False)}")
    print(f"QRNG Entropy Efficiency: {matrix.get('qrng_entropy_efficiency', {}).get('entropy_efficiency', 'N/A')}")
    
    print("\n" + "-"*60)
    print("ABLATION STUDY STATUS")
    print("-"*60)
    
    ablation = ledger.get("ablation_results", [])
    for mode in ablation:
        fitness = mode.get("average_fitness")
        fitness_str = f"{fitness:.4f}" if fitness is not None else "PENDING"
        runs = mode.get("run_count", 0)
        print(f"  {mode.get('mode_name'):25} | Fitness: {fitness_str:10} | Runs: {runs}")
    
    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    print("""
1. Run validation matrix for each agent (5 runs per agent)
2. Complete ablation study (10+ runs per mode)
3. Calculate statistical significance
4. Generate reproducibility package
5. Prepare for publication
""")


if __name__ == "__main__":
    populate_agents()
    generate_summary()