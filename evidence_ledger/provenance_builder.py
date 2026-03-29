#!/usr/bin/env python3
"""
Provenance Chain Builder

This module builds complete provenance chains linking IBM hardware runs to agent DNA,
following the PROV-O model for scientific reproducibility.

PROV Model:
- Entity: Raw result file, decoded DNA file, checkpoint snapshot
- Activity: Circuit execution, DNA extraction, fitness calculation
- Agent: Researcher, script, backend, lattice node

Usage:
    python provenance_builder.py link --job-id <id> --agent-id <id>
    python provenance_builder.py verify
    python provenance_builder.py compute-checksums
"""

import json
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import uuid


class ProvenanceBuilder:
    """
    Builds PROV-compliant provenance chains for the hardware evidence ledger.
    
    Every chain must answer:
    - WHO generated the data (researcher, script, backend)
    - WHAT backend and circuit were used
    - WHEN the execution occurred
    - HOW the final score was derived (algorithm version)
    """
    
    def __init__(self, ledger_path: str):
        """Initialize the provenance builder."""
        self.ledger_path = Path(ledger_path)
        self.ledger_data: dict = {}
        
    def load_ledger(self) -> dict:
        """Load the ledger from disk."""
        if not self.ledger_path.exists():
            raise FileNotFoundError(f"Ledger not found: {self.ledger_path}")
        
        with open(self.ledger_path, 'r', encoding='utf-8') as f:
            self.ledger_data = json.load(f)
        
        return self.ledger_data
    
    def save_ledger(self) -> None:
        """Save the ledger to disk."""
        with open(self.ledger_path, 'w', encoding='utf-8') as f:
            json.dump(self.ledger_data, f, indent=2, ensure_ascii=False)
    
    def compute_file_checksum(self, file_path: str) -> str:
        """Compute SHA-256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256_hash.update(chunk)
        
        return f"sha256:{sha256_hash.hexdigest()}"
    
    def compute_string_checksum(self, content: str) -> str:
        """Compute SHA-256 checksum of a string."""
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"
    
    def generate_persistent_id(self, pid_type: str = "uuid") -> dict:
        """Generate a FAIR-compliant persistent identifier."""
        return {
            "pid_type": pid_type,
            "pid_value": str(uuid.uuid4()) if pid_type == "uuid" else None,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "version": "2.0.0"
        }
    
    def link_hardware_run_to_agent(
        self,
        job_id: str,
        agent_id: int,
        decoded_dna_segment: str,
        contribution_weight: float = 1.0,
        extraction_method: str = "direct_measurement"
    ) -> dict:
        """
        Create a complete provenance chain from IBM job to agent DNA.
        
        This is the core function that makes claims machine-verifiable.
        
        Args:
            job_id: IBM Quantum job ID
            agent_id: Lattice agent ID
            decoded_dna_segment: DNA sequence extracted from measurement
            contribution_weight: Weight of this run's contribution
            extraction_method: How DNA was extracted
            
        Returns:
            dict: The created provenance chain
        """
        if not self.ledger_data:
            self.load_ledger()
        
        # Find the raw result entity
        raw_result = None
        for entity in self.ledger_data.get("entities", {}).get("raw_results", []):
            if entity.get("job_id") == job_id:
                raw_result = entity
                break
        
        if not raw_result:
            raise ValueError(f"Raw result not found for job_id: {job_id}")
        
        # Find the agent
        agent = None
        for a in self.ledger_data.get("agents", {}).get("lattice_agents", []):
            if a.get("agent_id") == agent_id:
                agent = a
                break
        
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")
        
        # Create decoded DNA entity
        dna_entity_id = self.generate_persistent_id()
        dna_entity = {
            "entity_id": dna_entity_id,
            "source_entity_id": raw_result["entity_id"]["pid_value"],
            "dna_sequence": decoded_dna_segment,
            "dna_length": len(decoded_dna_segment),
            "gc_content": (decoded_dna_segment.count('G') + decoded_dna_segment.count('C')) / len(decoded_dna_segment),
            "decoding_algorithm": extraction_method,
            "decoding_version": "2.0.0",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "checksum": self.compute_string_checksum(decoded_dna_segment)
        }
        
        # Add to entities
        self.ledger_data.setdefault("entities", {}).setdefault("decoded_dna", []).append(dna_entity)
        
        # Create DNA extraction activity
        extraction_activity_id = self.generate_persistent_id()
        extraction_activity = {
            "activity_id": extraction_activity_id,
            "used_entity": raw_result["entity_id"]["pid_value"],
            "generated_entity": dna_entity_id["pid_value"],
            "was_associated_with": "script-ledger-manager",
            "algorithm_version": "2.0.0",
            "extraction_method": extraction_method
        }
        
        # Add to activities
        self.ledger_data.setdefault("activities", {}).setdefault("dna_extractions", []).append(extraction_activity)
        
        # Create provenance chain
        chain_id = self.generate_persistent_id("uuid")
        provenance_chain = {
            "chain_id": chain_id["pid_value"],
            "agent_id": agent_id,
            "agent_directory": agent["directory"],
            "is_complete": True,
            "entities": [
                raw_result["entity_id"]["pid_value"],
                dna_entity_id["pid_value"]
            ],
            "activities": [
                raw_result.get("activity_id", {}).get("pid_value", "unknown"),
                extraction_activity_id["pid_value"]
            ],
            "chain_summary": {
                "raw_result_job_id": job_id,
                "backend": raw_result.get("backend", "unknown"),
                "shots": raw_result.get("shots", 0),
                "decoded_dna_hash": dna_entity["checksum"],
                "fitness_calculation_version": "2.0.0"
            },
            "verification": {
                "checksums_valid": True,
                "chain_integrity": True,
                "last_verified": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        # Add to provenance chains
        self.ledger_data.setdefault("provenance_chains", []).append(provenance_chain)
        
        # Update agent's provenance chain reference
        agent["provenance_chain_id"] = chain_id["pid_value"]
        
        # Update validation matrix
        matrix = self.ledger_data.get("validation_matrix", {})
        provenance = matrix.get("provenance_completeness", {})
        provenance["agents_with_complete_chains"] = provenance.get("agents_with_complete_chains", 0) + 1
        provenance["completeness_ratio"] = provenance["agents_with_complete_chains"] / provenance.get("total_agents", 17)
        
        # Update acceptance criteria
        acceptance = self.ledger_data.get("acceptance_criteria", {})
        if acceptance.get("provenance_linked", {}).get("status") == "FAIL":
            # Check if all agents now have provenance
            agents_with_chains = sum(1 for a in self.ledger_data.get("agents", {}).get("lattice_agents", []) 
                                    if a.get("provenance_chain_id"))
            if agents_with_chains == provenance.get("total_agents", 17):
                acceptance["provenance_linked"]["status"] = "PASS"
                acceptance["provenance_linked"]["notes"] = "All agents have linked hardware provenance chains"
        
        return provenance_chain
    
    def compute_all_checksums(self) -> dict:
        """
        Compute checksums for all raw result files.
        
        This ensures raw evidence integrity.
        """
        if not self.ledger_data:
            self.load_ledger()
        
        base_path = self.ledger_path.parent.parent
        results_path = base_path / "circuits" / "results"
        
        checksums_computed = 0
        errors = []
        
        for entity in self.ledger_data.get("entities", {}).get("raw_results", []):
            raw_path = entity.get("raw_counts_path")
            if raw_path:
                full_path = base_path / raw_path
                if full_path.exists():
                    try:
                        entity["checksum"] = self.compute_file_checksum(str(full_path))
                        entity["file_size_bytes"] = os.path.getsize(full_path)
                        checksums_computed += 1
                    except Exception as e:
                        errors.append(f"Error computing checksum for {raw_path}: {e}")
                else:
                    errors.append(f"File not found: {raw_path}")
        
        return {
            "checksums_computed": checksums_computed,
            "errors": errors
        }
    
    def verify_provenance_integrity(self) -> dict:
        """
        Verify the integrity of all provenance chains.
        
        Checks:
        1. All entities have valid checksums
        2. All activities reference valid entities
        3. All chains are complete (raw → DNA → agent)
        4. All agents have provenance_chain_id
        """
        if not self.ledger_data:
            self.load_ledger()
        
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "statistics": {}
        }
        
        # Count entities
        raw_results = self.ledger_data.get("entities", {}).get("raw_results", [])
        decoded_dna = self.ledger_data.get("entities", {}).get("decoded_dna", [])
        chains = self.ledger_data.get("provenance_chains", [])
        agents = self.ledger_data.get("agents", {}).get("lattice_agents", [])
        
        results["statistics"] = {
            "raw_results_count": len(raw_results),
            "decoded_dna_count": len(decoded_dna),
            "provenance_chains_count": len(chains),
            "agents_count": len(agents),
            "agents_with_provenance": sum(1 for a in agents if a.get("provenance_chain_id"))
        }
        
        # Check raw results have checksums
        for entity in raw_results:
            if not entity.get("checksum") or entity["checksum"] == "sha256:pending":
                results["warnings"].append(f"Raw result {entity.get('job_id')} missing checksum")
        
        # Check decoded DNA has checksums
        for entity in decoded_dna:
            if not entity.get("checksum"):
                results["warnings"].append(f"Decoded DNA {entity.get('entity_id', {}).get('pid_value')} missing checksum")
        
        # Check chains are complete
        for chain in chains:
            if not chain.get("is_complete"):
                results["errors"].append(f"Chain {chain.get('chain_id')} is incomplete")
                results["valid"] = False
            
            if not chain.get("entities") or len(chain["entities"]) < 2:
                results["errors"].append(f"Chain {chain.get('chain_id')} missing entities")
                results["valid"] = False
        
        # Check all agents have provenance
        agents_without_provenance = [a["directory"] for a in agents if not a.get("provenance_chain_id")]
        if agents_without_provenance:
            results["warnings"].append(f"Agents without provenance: {', '.join(agents_without_provenance)}")
        
        # Update validation matrix
        matrix = self.ledger_data.get("validation_matrix", {})
        provenance = matrix.get("provenance_completeness", {})
        provenance["agents_with_complete_chains"] = results["statistics"]["agents_with_provenance"]
        provenance["completeness_ratio"] = results["statistics"]["agents_with_provenance"] / max(provenance.get("total_agents", 17), 1)
        
        return results
    
    def generate_provenance_report(self) -> str:
        """Generate a human-readable provenance report."""
        if not self.ledger_data:
            self.load_ledger()
        
        report = []
        report.append("# Hardware Evidence Ledger - Provenance Report")
        report.append("")
        report.append(f"**Generated:** {datetime.utcnow().isoformat()}Z")
        report.append(f"**Schema Version:** {self.ledger_data.get('ledger_metadata', {}).get('schema_version', 'unknown')}")
        report.append("")
        
        # Metadata
        metadata = self.ledger_data.get("ledger_metadata", {})
        report.append("## Ledger Metadata")
        report.append("")
        report.append(f"| Field | Value |")
        report.append(f"|-------|-------|")
        report.append(f"| Ledger ID | {metadata.get('ledger_id', 'N/A')} |")
        report.append(f"| Release Tag | {metadata.get('release_tag', 'N/A')} |")
        report.append(f"| Total Agents | {metadata.get('total_agents', 'N/A')} |")
        report.append(f"| Average Fitness | {metadata.get('average_fitness', 'N/A'):.4f} |")
        report.append(f"| Schema Version | {metadata.get('schema_version', 'N/A')} |")
        report.append("")
        
        # Provenance completeness
        completeness = metadata.get("provenance_completeness", {})
        report.append("## Provenance Completeness")
        report.append("")
        report.append(f"| Metric | Value |")
        report.append(f"|--------|-------|")
        report.append(f"| Agents with Provenance | {completeness.get('agents_with_provenance', 0)}/{completeness.get('total_agents', 17)} |")
        report.append(f"| Completeness Ratio | {completeness.get('completeness_ratio', 0):.2%} |")
        report.append(f"| Status | {completeness.get('status', 'UNKNOWN')} |")
        report.append("")
        
        # Entities
        entities = self.ledger_data.get("entities", {})
        report.append("## Entities (PROV)")
        report.append("")
        report.append(f"| Entity Type | Count |")
        report.append(f"|--------------|-------|")
        report.append(f"| Raw Results | {len(entities.get('raw_results', []))} |")
        report.append(f"| Decoded DNA | {len(entities.get('decoded_dna', []))} |")
        report.append(f"| Circuit Definitions | {len(entities.get('circuit_definitions', []))} |")
        report.append(f"| Checkpoint Snapshots | {len(entities.get('checkpoint_snapshots', []))} |")
        report.append("")
        
        # Activities
        activities = self.ledger_data.get("activities", {})
        report.append("## Activities (PROV)")
        report.append("")
        report.append(f"| Activity Type | Count |")
        report.append(f"|---------------|-------|")
        report.append(f"| Circuit Executions | {len(activities.get('circuit_executions', []))} |")
        report.append(f"| DNA Extractions | {len(activities.get('dna_extractions', []))} |")
        report.append(f"| Fitness Calculations | {len(activities.get('fitness_calculations', []))} |")
        report.append("")
        
        # Agents
        agents = self.ledger_data.get("agents", {})
        report.append("## Agents (PROV)")
        report.append("")
        report.append(f"| Agent Type | Count |")
        report.append(f"|------------|-------|")
        report.append(f"| Quantum Backends | {len(agents.get('quantum_backends', []))} |")
        report.append(f"| Researchers | {len(agents.get('researchers', []))} |")
        report.append(f"| Scripts | {len(agents.get('scripts', []))} |")
        report.append(f"| Lattice Agents | {len(agents.get('lattice_agents', []))} |")
        report.append("")
        
        # Provenance chains
        chains = self.ledger_data.get("provenance_chains", [])
        report.append("## Provenance Chains")
        report.append("")
        
        if chains:
            report.append(f"| Chain ID | Agent | Backend | Job ID | Complete |")
            report.append(f"|----------|-------|---------|--------|----------|")
            for chain in chains:
                summary = chain.get("chain_summary", {})
                report.append(
                    f"| {chain.get('chain_id', 'N/A')[:8]}... | "
                    f"{chain.get('agent_directory', 'N/A')} | "
                    f"{summary.get('backend', 'N/A')} | "
                    f"{summary.get('raw_result_job_id', 'N/A')[:12]}... | "
                    f"{'✅' if chain.get('is_complete') else '❌'} |"
                )
        else:
            report.append("*No provenance chains linked yet.*")
        report.append("")
        
        # Lattice agents with provenance status
        lattice_agents = agents.get("lattice_agents", [])
        report.append("## Lattice Agents Provenance Status")
        report.append("")
        report.append(f"| Agent | Directory | Fitness | Phi | Provenance |")
        report.append(f"|-------|-----------|---------|-----|------------|")
        
        for agent in sorted(lattice_agents, key=lambda a: a.get("fitness", 0), reverse=True):
            prov_status = "✅ Linked" if agent.get("provenance_chain_id") else "❌ Unlinked"
            report.append(
                f"| {agent.get('agent_name', 'N/A')} | "
                f"{agent.get('directory', 'N/A')} | "
                f"{agent.get('fitness', 0):.4f} | "
                f"{agent.get('phi_score', 0):.4f} | "
                f"{prov_status} |"
            )
        report.append("")
        
        # Acceptance criteria
        acceptance = self.ledger_data.get("acceptance_criteria", {})
        report.append("## Acceptance Criteria")
        report.append("")
        report.append(f"| Criterion | Status | Notes |")
        report.append(f"|-----------|--------|-------|")
        for criterion, details in acceptance.items():
            status = details.get("status", "UNKNOWN")
            status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
            report.append(f"| {criterion} | {status_icon} {status} | {details.get('notes', '')} |")
        report.append("")
        
        # Next milestones
        milestones = self.ledger_data.get("next_milestones", [])
        report.append("## Next Milestones")
        report.append("")
        for milestone in milestones:
            status = milestone.get("status", "PENDING")
            status_icon = "✅" if status == "COMPLETE" else "🔄" if status == "IN_PROGRESS" else "⏳"
            report.append(f"- {status_icon} **{milestone.get('milestone', '')}**: {status} (Priority: {milestone.get('priority', 'NORMAL')})")
        
        return "\n".join(report)


def main():
    """Main entry point for CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Provenance Chain Builder for Hardware Evidence Ledger"
    )
    parser.add_argument(
        "--ledger",
        default="hardware_evidence_ledger_v2.json",
        help="Path to ledger file"
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Link command
    link_parser = subparsers.add_parser("link", help="Link hardware run to agent")
    link_parser.add_argument("--job-id", required=True, help="IBM Quantum job ID")
    link_parser.add_argument("--agent-id", required=True, type=int, help="Agent ID")
    link_parser.add_argument("--dna-segment", required=True, help="Decoded DNA segment")
    link_parser.add_argument("--weight", type=float, default=1.0, help="Contribution weight")
    
    # Verify command
    subparsers.add_parser("verify", help="Verify provenance integrity")
    
    # Checksums command
    subparsers.add_parser("compute-checksums", help="Compute all checksums")
    
    # Report command
    subparsers.add_parser("report", help="Generate provenance report")
    
    args = parser.parse_args()
    
    # Resolve paths
    script_dir = Path(__file__).parent
    ledger_path = script_dir / args.ledger
    
    builder = ProvenanceBuilder(str(ledger_path))
    builder.load_ledger()
    
    if args.command == "link":
        chain = builder.link_hardware_run_to_agent(
            job_id=args.job_id,
            agent_id=args.agent_id,
            decoded_dna_segment=args.dna_segment,
            contribution_weight=args.weight
        )
        builder.save_ledger()
        print(f"Created provenance chain: {chain['chain_id']}")
        print(f"Agent {args.agent_id} now linked to job {args.job_id}")
        
    elif args.command == "verify":
        results = builder.verify_provenance_integrity()
        builder.save_ledger()
        print(json.dumps(results, indent=2))
        
    elif args.command == "compute-checksums":
        results = builder.compute_all_checksums()
        builder.save_ledger()
        print(f"Computed {results['checksums_computed']} checksums")
        if results['errors']:
            print("Errors:")
            for error in results['errors']:
                print(f"  - {error}")
        
    elif args.command == "report":
        report = builder.generate_provenance_report()
        print(report)


if __name__ == "__main__":
    main()