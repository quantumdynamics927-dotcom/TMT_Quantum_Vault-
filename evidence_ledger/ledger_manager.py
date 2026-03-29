#!/usr/bin/env python3
"""
Hardware Evidence Ledger Manager

This module provides tools for managing the hardware evidence ledger for the
TMT Quantum Vault 17-node Toroidal Merkaba lattice. It ensures scientific
reproducibility by tracking IBM hardware provenance for every agent's DNA.

Usage:
    python ledger_manager.py validate
    python ledger_manager.py populate-agents
    python ledger_manager.py add-run --job-id <id> --backend <name>
    python ledger_manager.py generate-report
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import hashlib


class HardwareEvidenceLedger:
    """
    Manages the hardware evidence ledger for TMT Quantum Vault.
    
    This class provides methods to:
    - Load and validate ledger files
    - Add hardware run evidence
    - Track agent DNA provenance
    - Generate validation reports
    """
    
    LEDGER_VERSION = "1.0.0"
    PHI_THRESHOLD = 0.618  # Golden ratio inverse
    
    def __init__(self, ledger_path: str, schema_path: Optional[str] = None):
        """Initialize the ledger manager."""
        self.ledger_path = Path(ledger_path)
        self.schema_path = Path(schema_path) if schema_path else None
        self.ledger_data: dict = {}
        self.schema_data: dict = {}
        
    def load_ledger(self) -> dict:
        """Load the ledger from disk."""
        if not self.ledger_path.exists():
            raise FileNotFoundError(f"Ledger not found: {self.ledger_path}")
        
        with open(self.ledger_path, 'r', encoding='utf-8') as f:
            self.ledger_data = json.load(f)
        
        return self.ledger_data
    
    def load_schema(self) -> dict:
        """Load the JSON schema for validation."""
        if self.schema_path and self.schema_path.exists():
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                self.schema_data = json.load(f)
        return self.schema_data
    
    def validate_ledger(self) -> dict:
        """
        Validate the ledger against its schema and internal consistency.
        
        Returns:
            dict: Validation results with status and any errors
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "statistics": {}
        }
        
        if not self.ledger_data:
            self.load_ledger()
        
        # Check required top-level fields
        required_fields = ["ledger_metadata", "agents", "hardware_runs", "validation_matrix"]
        for field in required_fields:
            if field not in self.ledger_data:
                results["errors"].append(f"Missing required field: {field}")
                results["valid"] = False
        
        # Validate ledger metadata
        metadata = self.ledger_data.get("ledger_metadata", {})
        if metadata.get("phi_threshold") != self.PHI_THRESHOLD:
            results["warnings"].append(
                f"Phi threshold {metadata.get('phi_threshold')} differs from canonical {self.PHI_THRESHOLD}"
            )
        
        # Validate agents
        agents = self.ledger_data.get("agents", [])
        agent_ids = set()
        for agent in agents:
            # Check for duplicate agent IDs
            aid = agent.get("agent_id")
            if aid in agent_ids:
                results["errors"].append(f"Duplicate agent_id: {aid}")
                results["valid"] = False
            agent_ids.add(aid)
            
            # Validate DNA sequence
            dna = agent.get("conscious_dna", "")
            if not all(c in "ATCG" for c in dna):
                results["errors"].append(f"Invalid DNA sequence for agent {aid}: {dna[:20]}...")
                results["valid"] = False
            
            # Check fitness bounds
            fitness = agent.get("fitness", 0)
            if not 0 <= fitness <= 1:
                results["errors"].append(f"Fitness out of bounds for agent {aid}: {fitness}")
                results["valid"] = False
            
            # Check phi score bounds
            phi = agent.get("phi_score", 0)
            if not 0 <= phi <= 1:
                results["errors"].append(f"Phi score out of bounds for agent {aid}: {phi}")
                results["valid"] = False
        
        # Validate hardware runs
        hardware_runs = self.ledger_data.get("hardware_runs", [])
        job_ids = set()
        for run in hardware_runs:
            job_id = run.get("job_id")
            if job_id in job_ids:
                results["errors"].append(f"Duplicate job_id: {job_id}")
                results["valid"] = False
            job_ids.add(job_id)
            
            # Validate status
            status = run.get("status")
            valid_statuses = ["Completed", "Running", "Queued", "Failed", "Cancelled"]
            if status not in valid_statuses:
                results["warnings"].append(f"Unknown status for job {job_id}: {status}")
        
        # Validate validation matrix
        matrix = self.ledger_data.get("validation_matrix", {})
        total_runs = matrix.get("total_runs", 0)
        successful_runs = matrix.get("successful_runs", 0)
        
        if successful_runs > total_runs:
            results["errors"].append("Successful runs exceed total runs")
            results["valid"] = False
        
        # Calculate statistics
        results["statistics"] = {
            "total_agents": len(agents),
            "total_hardware_runs": len(hardware_runs),
            "total_shots": sum(run.get("shots", 0) for run in hardware_runs),
            "unique_backends": len(matrix.get("backends_used", [])),
            "pass_rate": matrix.get("pass_rate", 0),
            "sierpinski_validated": matrix.get("sierpinski_invariant", {}).get("validated", False)
        }
        
        return results
    
    def add_hardware_run(
        self,
        job_id: str,
        backend: str,
        shots: int,
        status: str = "Completed",
        circuit_type: str = "consciousness_dna_circuit",
        raw_result_path: Optional[str] = None,
        info_path: Optional[str] = None,
        **kwargs
    ) -> dict:
        """
        Add a new hardware run to the ledger.
        
        Args:
            job_id: IBM Quantum job ID
            backend: Quantum backend name
            shots: Number of shots
            status: Run status
            circuit_type: Type of circuit executed
            raw_result_path: Path to raw result file
            info_path: Path to job info file
            **kwargs: Additional metadata
            
        Returns:
            dict: The added hardware run entry
        """
        if not self.ledger_data:
            self.load_ledger()
        
        run_entry = {
            "job_id": job_id,
            "backend": backend,
            "status": status,
            "shots": shots,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "circuit_type": circuit_type,
            **kwargs
        }
        
        if raw_result_path:
            run_entry["raw_result_path"] = raw_result_path
        if info_path:
            run_entry["info_path"] = info_path
        
        # Check for duplicate
        existing_ids = {r["job_id"] for r in self.ledger_data.get("hardware_runs", [])}
        if job_id in existing_ids:
            raise ValueError(f"Job ID already exists: {job_id}")
        
        self.ledger_data.setdefault("hardware_runs", []).append(run_entry)
        
        # Update validation matrix
        matrix = self.ledger_data.get("validation_matrix", {})
        matrix["total_runs"] = matrix.get("total_runs", 0) + 1
        if status == "Completed":
            matrix["successful_runs"] = matrix.get("successful_runs", 0) + 1
        matrix["pass_rate"] = matrix["successful_runs"] / matrix["total_runs"]
        
        return run_entry
    
    def link_run_to_agent(
        self,
        agent_id: int,
        job_id: str,
        decoded_segment: str,
        contribution_weight: float = 1.0
    ) -> dict:
        """
        Link a hardware run to an agent's DNA provenance.
        
        Args:
            agent_id: Agent identifier
            job_id: IBM Quantum job ID
            decoded_segment: DNA segment decoded from measurement
            contribution_weight: Weight of this run's contribution
            
        Returns:
            dict: The provenance entry
        """
        if not self.ledger_data:
            self.load_ledger()
        
        # Find the hardware run
        run = None
        for r in self.ledger_data.get("hardware_runs", []):
            if r["job_id"] == job_id:
                run = r
                break
        
        if not run:
            raise ValueError(f"Hardware run not found: {job_id}")
        
        provenance_entry = {
            "run_id": f"RUN-{len(self.ledger_data.get('hardware_runs', [])):03d}",
            "backend": run["backend"],
            "job_id": job_id,
            "shots": run["shots"],
            "execution_timestamp": run.get("created_at", ""),
            "decoded_segment": decoded_segment,
            "contribution_weight": contribution_weight
        }
        
        # Find and update agent
        for agent in self.ledger_data.get("agents", []):
            if agent["agent_id"] == agent_id:
                agent.setdefault("hardware_provenance", []).append(provenance_entry)
                return provenance_entry
        
        raise ValueError(f"Agent not found: {agent_id}")
    
    def calculate_benchmark_envelope(self, agent_id: int) -> dict:
        """
        Calculate the benchmark envelope for an agent across all runs.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            dict: Benchmark envelope statistics
        """
        if not self.ledger_data:
            self.load_ledger()
        
        # Find agent
        agent = None
        for a in self.ledger_data.get("agents", []):
            if a["agent_id"] == agent_id:
                agent = a
                break
        
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")
        
        provenance = agent.get("hardware_provenance", [])
        
        if not provenance:
            return {
                "mean_fitness": None,
                "std_fitness": None,
                "run_count": 0,
                "backends_tested": [],
                "noise_conditions": []
            }
        
        # Collect fitness values from runs
        # Note: This would need actual fitness calculation from raw results
        # For now, return placeholder
        backends = list(set(p["backend"] for p in provenance))
        
        return {
            "mean_fitness": agent.get("fitness"),
            "std_fitness": None,  # Would calculate from multiple runs
            "min_fitness": agent.get("fitness"),
            "max_fitness": agent.get("fitness"),
            "run_count": len(provenance),
            "backends_tested": backends,
            "noise_conditions": []
        }
    
    def generate_validation_report(self) -> str:
        """
        Generate a human-readable validation report.
        
        Returns:
            str: Markdown-formatted report
        """
        if not self.ledger_data:
            self.load_ledger()
        
        metadata = self.ledger_data.get("ledger_metadata", {})
        agents = self.ledger_data.get("agents", [])
        runs = self.ledger_data.get("hardware_runs", [])
        matrix = self.ledger_data.get("validation_matrix", {})
        ablation = self.ledger_data.get("ablation_results", [])
        
        report = []
        report.append("# TMT Quantum Vault Hardware Evidence Ledger")
        report.append("")
        report.append(f"**Ledger ID:** {metadata.get('ledger_id', 'N/A')}")
        report.append(f"**Release Tag:** {metadata.get('release_tag', 'N/A')}")
        report.append(f"**Created:** {metadata.get('created_at', 'N/A')}")
        report.append(f"**Frozen Lattice:** {metadata.get('frozen_lattice_version', 'N/A')}")
        report.append("")
        
        report.append("## Summary Statistics")
        report.append("")
        report.append(f"| Metric | Value |")
        report.append(f"|--------|-------|")
        report.append(f"| Total Agents | {len(agents)} |")
        report.append(f"| Average Fitness | {metadata.get('average_fitness', 'N/A'):.4f} |")
        report.append(f"| Phi Threshold | {metadata.get('phi_threshold', 'N/A')} |")
        report.append(f"| Total Hardware Runs | {len(runs)} |")
        report.append(f"| Total Shots | {matrix.get('total_shots', 'N/A'):,} |")
        report.append(f"| Pass Rate | {matrix.get('pass_rate', 'N/A'):.2%} |")
        report.append("")
        
        report.append("## Hardware Backends Used")
        report.append("")
        for backend in matrix.get("backends_used", []):
            backend_runs = [r for r in runs if r.get("backend") == backend]
            report.append(f"- **{backend}**: {len(backend_runs)} runs")
        report.append("")
        
        report.append("## Agent Evidence Summary")
        report.append("")
        report.append("| Agent | Name | Fitness | Phi Score | DNA Length | Hardware Runs |")
        report.append("|-------|------|---------|-----------|------------|----------------|")
        
        for agent in agents:
            hw_runs = len(agent.get("hardware_provenance", []))
            report.append(
                f"| {agent.get('directory', 'N/A')} | {agent.get('agent_name', 'N/A')} | "
                f"{agent.get('fitness', 0):.4f} | {agent.get('phi_score', 0):.4f} | "
                f"{agent.get('dna_length', 'N/A')} | {hw_runs} |"
            )
        report.append("")
        
        report.append("## Sierpinski Invariant Validation")
        report.append("")
        sierpinski = matrix.get("sierpinski_invariant", {})
        report.append(f"- **Observed Value:** {sierpinski.get('observed_value', 'N/A')}")
        report.append(f"- **Expected Value:** {sierpinski.get('expected_value', 0.618)}")
        report.append(f"- **Deviation:** {sierpinski.get('deviation', 'N/A')}")
        report.append(f"- **Run Count:** {sierpinski.get('run_count', 'N/A')}")
        report.append(f"- **Validated:** {'✅ Yes' if sierpinski.get('validated') else '❌ No'}")
        report.append("")
        
        report.append("## Ablation Study Status")
        report.append("")
        report.append("| Mode | Description | Avg Fitness | Runs | Delta vs Baseline |")
        report.append("|------|-------------|-------------|------|-------------------|")
        
        for mode in ablation:
            fitness = mode.get("average_fitness")
            fitness_str = f"{fitness:.4f}" if fitness is not None else "Pending"
            delta = mode.get("delta_vs_baseline")
            delta_str = f"{delta:+.4f}" if delta is not None else "Pending"
            report.append(
                f"| {mode.get('mode_name')} | {mode.get('description', '')[:40]}... | "
                f"{fitness_str} | {mode.get('run_count', 0)} | {delta_str} |"
            )
        report.append("")
        
        report.append("## Pending Validations")
        report.append("")
        pending = self.ledger_data.get("pending_validations", {})
        report.append(f"- **Required runs per agent:** {pending.get('required_runs_per_agent', 'N/A')}")
        report.append(f"- **Required backends:** {', '.join(pending.get('required_backends', []))}")
        report.append(f"- **Shot counts to test:** {pending.get('shot_counts_to_test', [])}")
        report.append("")
        
        agents_needing = pending.get("agents_requiring_validation", [])
        report.append(f"### Agents Requiring Validation ({len(agents_needing)})")
        report.append("")
        for agent_name in agents_needing:
            report.append(f"- {agent_name}")
        
        return "\n".join(report)
    
    def save_ledger(self, path: Optional[str] = None) -> None:
        """Save the ledger to disk."""
        save_path = Path(path) if path else self.ledger_path
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(self.ledger_data, f, indent=2, ensure_ascii=False)
    
    def compute_lattice_hash(self) -> str:
        """
        Compute a deterministic hash of the frozen lattice configuration.
        
        This provides a canonical identifier for the 17-node topology.
        
        Returns:
            str: SHA-256 hash of lattice configuration
        """
        if not self.ledger_data:
            self.load_ledger()
        
        # Create canonical representation
        agents = self.ledger_data.get("agents", [])
        canonical = []
        
        for agent in sorted(agents, key=lambda a: a.get("agent_id", 0)):
            canonical.append({
                "id": agent.get("agent_id"),
                "dna": agent.get("conscious_dna"),
                "fitness": round(agent.get("fitness", 0), 6),
                "phi": round(agent.get("phi_score", 0), 6)
            })
        
        canonical_json = json.dumps(canonical, sort_keys=True)
        return hashlib.sha256(canonical_json.encode()).hexdigest()


def main():
    """Main entry point for CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Hardware Evidence Ledger Manager"
    )
    parser.add_argument(
        "--ledger",
        default="hardware_evidence_ledger_v0.1.0-alpha.json",
        help="Path to ledger file"
    )
    parser.add_argument(
        "--schema",
        default="ledger_schema.json",
        help="Path to schema file"
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Validate command
    subparsers.add_parser("validate", help="Validate ledger integrity")
    
    # Generate report command
    subparsers.add_parser("generate-report", help="Generate validation report")
    
    # Compute hash command
    subparsers.add_parser("compute-hash", help="Compute lattice hash")
    
    args = parser.parse_args()
    
    # Resolve paths relative to script location
    script_dir = Path(__file__).parent
    ledger_path = script_dir / args.ledger
    schema_path = script_dir / args.schema
    
    ledger = HardwareEvidenceLedger(str(ledger_path), str(schema_path))
    
    if args.command == "validate":
        results = ledger.validate_ledger()
        print(json.dumps(results, indent=2))
        
    elif args.command == "generate-report":
        report = ledger.generate_validation_report()
        print(report)
        
    elif args.command == "compute-hash":
        hash_value = ledger.compute_lattice_hash()
        print(f"Lattice Hash: {hash_value}")


if __name__ == "__main__":
    main()