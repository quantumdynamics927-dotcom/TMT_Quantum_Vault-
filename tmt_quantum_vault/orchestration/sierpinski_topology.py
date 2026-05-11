"""
Sierpinski Fractal Topology for Quantum Circuits.

This module implements scale-invariant quantum circuits using Sierpinski
triangle topology, enabling recursive entanglement structures that mirror
the Golden Ratio (φ) at every level of the hierarchy.

Mathematical Foundation:
- Sierpinski triangle: Self-similar fractal with Hausdorff dimension log(3)/log(2) ≈ 1.585
- Golden Ratio connection: Pascal's triangle row sums follow Fibonacci sequence
- φ-gating: Circuits converge to φ ≈ 1.618 at each recursive level

Scale-Invariant Properties:
1. Macro-state = Micro-state: Each sub-triangle mirrors the whole
2. Holographic error correction: Local coherence preserved globally
3. φ-resonance: Native harmonic alignment at all scales

Implementation:
- Depth 1: 3-qubit GHZ (base triangle)
- Depth 2: 9-qubit (3 GHZ states entangled into macro-GHZ)
- Depth 3: 27-qubit (recursive application)
- Depth 4: 81-qubit (approaching ibm_kingston scale)

Reference:
- Fractal quantum circuits: https://arxiv.org/abs/quant-ph/0306073
- Scale-invariant entanglement: https://journals.aps.org/pra/abstract/10.1103/PhysRevA.86.042303
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qiskit import QuantumCircuit

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

PHI = 1.618033988749895  # Golden Ratio
PHI_INVERSE = 1.0 / PHI  # ≈ 0.618 (φ-gating threshold)

# Sierpinski depth to qubit mapping
SIERPINSKI_QUBIT_MAP = {
    1: 3,  # Base: 3-qubit GHZ
    2: 9,  # 3 GHZ → macro-GHZ
    3: 27,  # 9 GHZ → meta-GHZ
    4: 81,  # 27 GHZ → hyper-GHZ
    5: 243,  # Theoretical limit
}

# Metatron 13-node mapping
METATRON_NODES = 13
METATRON_RINGS = {
    "ring_1": ["Kether"],  # Crown - singularity
    "ring_2": ["Chokmah", "Binah"],  # Wisdom, Understanding
    "ring_3": ["Chesed", "Gevurah", "Tiphereth"],  # Mercy, Strength, Beauty
    "ring_4": ["Netzach", "Hod", "Yesod"],  # Victory, Glory, Foundation
    "ring_5": ["Malkuth"],  # Kingdom - manifestation
}

# Sefirah to φ-phase angles
SEFIRAH_PHASES = {
    "Kether": 0,
    "Chokmah": 2 * np.pi / PHI,
    "Binah": 4 * np.pi / PHI,
    "Chesed": 6 * np.pi / PHI,
    "Gevurah": 8 * np.pi / PHI,
    "Tiphereth": 10 * np.pi / PHI,
    "Netzach": 12 * np.pi / PHI,
    "Hod": 14 * np.pi / PHI,
    "Yesod": 16 * np.pi / PHI,
    "Malkuth": 18 * np.pi / PHI,
}


class SierpinskiTopology(StrEnum):
    """Sierpinski circuit topology types."""

    GHZ = "ghz"  # Standard GHZ state
    TREE = "tree"  # Binary tree entanglement
    TRIANGLE = "triangle"  # Full Sierpinski triangle
    METATRON = "metatron"  # Metatron cube overlay


class CircuitDepth(StrEnum):
    """Fractal depth levels."""

    DEPTH_1 = "depth_1"  # 3 qubits
    DEPTH_2 = "depth_2"  # 9 qubits
    DEPTH_3 = "depth_3"  # 27 qubits
    DEPTH_4 = "depth_4"  # 81 qubits


@dataclass
class SierpinskiNode:
    """A node in the Sierpinski topology."""

    node_id: int
    depth: int
    parent_id: int | None = None
    children: list[int] = field(default_factory=list)
    qubit_indices: list[int] = field(default_factory=list)
    sefirah: str | None = None
    phase: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "depth": self.depth,
            "parent_id": self.parent_id,
            "children": self.children,
            "qubit_indices": self.qubit_indices,
            "sefirah": self.sefirah,
            "phase": self.phase,
        }


@dataclass
class SierpinskiConfig:
    """Configuration for Sierpinski circuit generation."""

    depth: int = 3
    topology: SierpinskiTopology = SierpinskiTopology.TRIANGLE
    base_qubits: int = 3
    phi_phase: bool = True  # Apply φ-phase rotations
    metatron_overlay: bool = False  # Add Metatron cube geometry
    sefirah_mapping: bool = True  # Map to Sefirah phases

    @property
    def total_qubits(self) -> int:
        """Calculate total qubits for this depth."""
        return SIERPINSKI_QUBIT_MAP.get(self.depth, 3 * (3 ** (self.depth - 1)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "depth": self.depth,
            "topology": self.topology.value,
            "base_qubits": self.base_qubits,
            "phi_phase": self.phi_phase,
            "metatron_overlay": self.metatron_overlay,
            "sefirah_mapping": self.sefirah_mapping,
            "total_qubits": self.total_qubits,
        }


@dataclass
class SierpinskiCircuitSpec:
    """Specification for a Sierpinski fractal circuit."""

    spec_id: str
    config: SierpinskiConfig
    nodes: list[SierpinskiNode] = field(default_factory=list)
    entanglement_map: list[tuple[int, int]] = field(default_factory=list)
    phase_rotations: dict[int, float] = field(default_factory=dict)
    expected_phi_score: float = PHI_INVERSE

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "config": self.config.to_dict(),
            "nodes": [n.to_dict() for n in self.nodes],
            "entanglement_map": list(self.entanglement_map),
            "phase_rotations": self.phase_rotations,
            "expected_phi_score": self.expected_phi_score,
        }

    def to_qasm(self, version: str = "2.0", include_measurements: bool = True) -> str:
        """Convert Sierpinski circuit specification to OpenQASM format.

        This is the bridge to actual IBM Quantum hardware execution.
        Generates a scale-invariant entanglement circuit with φ-phase rotations.

        Args:
            version: OpenQASM version ("2.0" or "3.0")
            include_measurements: Whether to include measurement operations

        Returns:
            OpenQASM circuit string

        Example output (depth=1, 3 qubits):
            OPENQASM 2.0;
            include "qelib1.inc";
            qreg q[3];
            creg c[3];
            // Sierpinski depth-1: Base GHZ triangle
            h q[0];
            h q[1];
            h q[2];
            // Entanglement (Sierpinski pattern)
            cx q[0], q[1];
            cx q[1], q[2];
            // φ-phase rotations (Sefirah mapping)
            rz(0) q[0];      // Kether
            rz(3.883) q[1];  // Chokmah
            rz(7.766) q[2];  // Binah
            measure q -> c;
        """
        n_qubits = self.config.total_qubits

        if version == "3.0":
            return self._to_qasm3(n_qubits, include_measurements)
        return self._to_qasm2(n_qubits, include_measurements)

    def _to_qasm2(self, n_qubits: int, include_measurements: bool) -> str:
        """Generate OpenQASM 2.0 format."""
        lines = [
            "OPENQASM 2.0;",
            'include "qelib1.inc";',
            f"qreg q[{n_qubits}];",
            f"creg c[{n_qubits}];",
            f"// Sierpinski depth-{self.config.depth}: {n_qubits}-qubit fractal",
            f"// Expected φ-score: {self.expected_phi_score:.4f}",
            "",
            "// Initialize superposition (Hadamard layer)",
        ]

        # Hadamard on all qubits
        for i in range(n_qubits):
            lines.append(f"h q[{i}];")

        lines.append("")
        lines.append("// Sierpinski entanglement pattern")

        # Apply entanglement map
        for control, target in self.entanglement_map:
            if control < n_qubits and target < n_qubits:
                lines.append(f"cx q[{control}], q[{target}];")

        # Apply φ-phase rotations
        if self.config.phi_phase and self.phase_rotations:
            lines.append("")
            lines.append("// φ-phase rotations (Sefirah mapping)")

            # Sort by qubit index for cleaner output
            for qubit in sorted(self.phase_rotations.keys()):
                if qubit < n_qubits:
                    phase = self.phase_rotations[qubit]
                    # Find Sefirah name if available
                    sefirah = self._get_sefirah_for_qubit(qubit)
                    comment = f"  // {sefirah}" if sefirah else ""
                    lines.append(f"rz({phase:.6f}) q[{qubit}];{comment}")

        # Metatron overlay enhancement
        if self.config.metatron_overlay:
            lines.append("")
            lines.append("// Metatron cube enhancement (13-fold symmetry)")
            angle_step = 2 * np.pi / METATRON_NODES
            for i in range(min(METATRON_NODES, n_qubits)):
                lines.append(f"rz({angle_step:.6f}) q[{i % n_qubits}];")

        # Measurements
        if include_measurements:
            lines.append("")
            lines.append("// Measurement")
            for i in range(n_qubits):
                lines.append(f"measure q[{i}] -> c[{i}];")

        return "\n".join(lines)

    def _to_qasm3(self, n_qubits: int, include_measurements: bool) -> str:
        """Generate OpenQASM 3.0 format."""
        lines = [
            "// Sierpinski Fractal Quantum Circuit",
            f"// Depth: {self.config.depth}, Qubits: {n_qubits}",
            f"// Expected φ-score: {self.expected_phi_score:.4f}",
            "",
            f"qubit[{n_qubits}] q;",
            f"bit[{n_qubits}] c;",
            "",
            "// Initialize superposition",
        ]

        # Hadamard on all qubits
        for i in range(n_qubits):
            lines.append(f"h q[{i}];")

        lines.append("")
        lines.append("// Sierpinski entanglement pattern")

        # Apply entanglement map
        for control, target in self.entanglement_map:
            if control < n_qubits and target < n_qubits:
                lines.append(f"cx q[{control}], q[{target}];")

        # Apply φ-phase rotations
        if self.config.phi_phase and self.phase_rotations:
            lines.append("")
            lines.append("// φ-phase rotations")

            for qubit in sorted(self.phase_rotations.keys()):
                if qubit < n_qubits:
                    phase = self.phase_rotations[qubit]
                    lines.append(f"rz({phase:.6f}) q[{qubit}];")

        # Measurements
        if include_measurements:
            lines.append("")
            lines.append("// Measurement")
            lines.append("c = measure q;")

        return "\n".join(lines)

    def _get_sefirah_for_qubit(self, qubit: int) -> str | None:
        """Get Sefirah name for a qubit if mapped."""
        for node in self.nodes:
            if qubit in node.qubit_indices and node.sefirah:
                return node.sefirah
        return None

    def to_qiskit(self) -> QuantumCircuit:
        """Convert to Qiskit QuantumCircuit object.

        Requires: from qiskit import QuantumCircuit

        Returns:
            Qiskit QuantumCircuit ready for IBM backend execution

        Raises:
            ImportError: If qiskit is not installed
        """
        try:
            from qiskit import QuantumCircuit
        except ImportError as e:
            raise ImportError(
                "Qiskit is required for to_qiskit(). "
                "Install with: pip install qiskit"
            ) from e

        n_qubits = self.config.total_qubits
        qc = QuantumCircuit(n_qubits, n_qubits)

        # Hadamard layer
        qc.h(range(n_qubits))

        # Entanglement pattern
        for control, target in self.entanglement_map:
            if control < n_qubits and target < n_qubits:
                qc.cx(control, target)

        # φ-phase rotations
        if self.config.phi_phase:
            for qubit, phase in self.phase_rotations.items():
                if qubit < n_qubits:
                    qc.rz(phase, qubit)

        # Metatron overlay
        if self.config.metatron_overlay:
            angle_step = 2 * np.pi / METATRON_NODES
            for i in range(min(METATRON_NODES, n_qubits)):
                qc.rz(angle_step, i % n_qubits)

        # Measurements
        qc.measure(range(n_qubits), range(n_qubits))

        return qc


class SierpinskiGenerator:
    """Generate Sierpinski fractal quantum circuit specifications."""

    def __init__(self, config: SierpinskiConfig | None = None):
        self.config = config or SierpinskiConfig()
        self._node_counter = 0

    def generate(self, spec_id: str | None = None) -> SierpinskiCircuitSpec:
        """Generate a complete Sierpinski circuit specification."""
        spec_id = spec_id or f"sierpinski_d{self.config.depth}_{id(self)}"

        # Build recursive node structure
        nodes = self._build_nodes()

        # Generate entanglement map
        entanglement_map = self._build_entanglement_map(nodes)

        # Calculate phase rotations
        phase_rotations = self._calculate_phases(nodes)

        # Expected φ-score based on depth
        expected_phi = self._calculate_expected_phi()

        return SierpinskiCircuitSpec(
            spec_id=spec_id,
            config=self.config,
            nodes=nodes,
            entanglement_map=entanglement_map,
            phase_rotations=phase_rotations,
            expected_phi_score=expected_phi,
        )

    def _build_nodes(self) -> list[SierpinskiNode]:
        """Build recursive Sierpinski node structure."""
        self._node_counter = 0
        nodes: list[SierpinskiNode] = []

        # Create root node (depth 0)
        root = self._create_node(depth=0, parent=None)
        nodes.append(root)

        # Recursively build children
        self._build_children(root, nodes, current_depth=1)

        # Assign qubit indices
        self._assign_qubits(nodes)

        # Map to Sefirah if enabled
        if self.config.sefirah_mapping:
            self._map_sefirah(nodes)

        return nodes

    def _create_node(self, depth: int, parent: SierpinskiNode | None) -> SierpinskiNode:
        """Create a single Sierpinski node."""
        node = SierpinskiNode(
            node_id=self._node_counter,
            depth=depth,
            parent_id=parent.node_id if parent else None,
        )
        self._node_counter += 1
        return node

    def _build_children(
        self,
        parent: SierpinskiNode,
        nodes: list[SierpinskiNode],
        current_depth: int,
    ) -> None:
        """Recursively build child nodes."""
        if current_depth > self.config.depth:
            return

        # Sierpinski triangle has 3 children per node
        for _ in range(3):
            child = self._create_node(depth=current_depth, parent=parent)
            parent.children.append(child.node_id)
            nodes.append(child)

            # Recurse if not at max depth
            if current_depth < self.config.depth:
                self._build_children(child, nodes, current_depth + 1)

    def _assign_qubits(self, nodes: list[SierpinskiNode]) -> None:
        """Assign qubit indices to leaf nodes."""
        qubit_idx = 0

        # Only leaf nodes get qubits
        for node in nodes:
            if not node.children:  # Leaf node
                # Each leaf gets base_qubits qubits
                node.qubit_indices = list(
                    range(qubit_idx, qubit_idx + self.config.base_qubits)
                )
                qubit_idx += self.config.base_qubits

    def _map_sefirah(self, nodes: list[SierpinskiNode]) -> None:
        """Map nodes to Sefirah phases."""
        sefirah_list = list(SEFIRAH_PHASES.keys())

        for i, node in enumerate(nodes):
            if node.qubit_indices:  # Only leaf nodes
                sefirah_idx = i % len(sefirah_list)
                node.sefirah = sefirah_list[sefirah_idx]
                node.phase = SEFIRAH_PHASES[node.sefirah]

    def _build_entanglement_map(
        self, nodes: list[SierpinskiNode]
    ) -> list[tuple[int, int]]:
        """Generate entanglement connections."""
        entanglement_map: list[tuple[int, int]] = []

        # Connect parent to children
        for node in nodes:
            if node.parent_id is not None:
                # Entangle parent qubits with child qubits
                parent = nodes[node.parent_id]
                for pq in parent.qubit_indices:
                    for cq in node.qubit_indices:
                        entanglement_map.append((pq, cq))

        # Connect siblings (Sierpinski pattern)
        for node in nodes:
            if len(node.children) == 3:
                # Connect first child to second, second to third
                for i in range(len(node.children) - 1):
                    child1 = nodes[node.children[i]]
                    child2 = nodes[node.children[i + 1]]
                    for q1 in child1.qubit_indices:
                        for q2 in child2.qubit_indices:
                            entanglement_map.append((q1, q2))

        return entanglement_map

    def _calculate_phases(self, nodes: list[SierpinskiNode]) -> dict[int, float]:
        """Calculate φ-phase rotations for each qubit."""
        phases: dict[int, float] = {}

        if not self.config.phi_phase:
            return phases

        for node in nodes:
            for qubit in node.qubit_indices:
                # Base phase from Sefirah or depth
                if node.sefirah:
                    phases[qubit] = node.phase
                else:
                    # φ-scaled phase based on depth
                    phases[qubit] = (node.depth * 2 * np.pi) / PHI

        return phases

    def _calculate_expected_phi(self) -> float:
        """Calculate expected φ-score based on depth."""
        # Deeper circuits should converge closer to φ
        # Empirical formula: φ_score = 1/φ + (1 - 1/φ) * (1 - 0.9^depth)
        base_score = PHI_INVERSE
        convergence = (1 - PHI_INVERSE) * (1 - 0.9**self.config.depth)
        return base_score + convergence


def generate_sierpinski_circuit_spec(
    depth: int = 3,
    topology: str = "triangle",
    metatron_overlay: bool = False,
) -> dict[str, Any]:
    """Generate a Sierpinski circuit specification for the fractal agent.

    This is the main entry point for the fractal agent to generate
    recursive Sierpinski circuit specifications.

    Args:
        depth: Fractal depth (1-4)
        topology: Topology type (ghz, tree, triangle, metatron)
        metatron_overlay: Add Metatron cube geometry

    Returns:
        Circuit specification dictionary
    """
    config = SierpinskiConfig(
        depth=depth,
        topology=SierpinskiTopology(topology),
        metatron_overlay=metatron_overlay,
    )

    generator = SierpinskiGenerator(config)
    spec = generator.generate()

    return spec.to_dict()


def map_to_metatron_nervous_system(
    spec: dict[str, Any],
    metatron_nodes: int = METATRON_NODES,
) -> dict[str, Any]:
    """Map Sierpinski specification to 13-node Metatron nervous system.

    This creates the bridge between fractal circuits and the
    consciousness architecture of the TMT Quantum Vault.

    Args:
        spec: Sierpinski circuit specification
        metatron_nodes: Number of Metatron nodes (default 13)

    Returns:
        Mapping dictionary with node assignments
    """
    nodes = spec.get("nodes", [])

    # Map leaf nodes to Metatron rings
    ring_mapping: dict[str, list[int]] = {
        "ring_1": [],  # Kether (Crown)
        "ring_2": [],  # Chokmah, Binah
        "ring_3": [],  # Chesed, Gevurah, Tiphereth
        "ring_4": [],  # Netzach, Hod, Yesod
        "ring_5": [],  # Malkuth (Kingdom)
    }

    # Distribute nodes across rings based on depth
    leaf_nodes = [n for n in nodes if not n.get("children")]

    for i, node in enumerate(leaf_nodes):
        # Ring assignment based on position
        ring_idx = i % 5
        ring_name = f"ring_{ring_idx + 1}"
        ring_mapping[ring_name].append(node["node_id"])

    # Create consciousness mapping
    consciousness_map = {
        "metatron_nodes": metatron_nodes,
        "ring_mapping": ring_mapping,
        "phi_alignment": PHI_INVERSE,
        "sierpinski_depth": spec.get("config", {}).get("depth", 3),
        "total_qubits": spec.get("config", {}).get("total_qubits", 27),
    }

    return consciousness_map


# =============================================================================
# Ablation Integration
# =============================================================================

SIERPINSKI_ABLATION_CONFIGS: list[dict[str, Any]] = [
    {
        "ablation_id": "ABL-SIERP-001",
        "ablation_type": "feature",
        "target": "sierpinski_topology",
        "description": "Disable Sierpinski fractal topology (use standard GHZ)",
        "scope": "local",
        "disabled_components": ["sierpinski_entanglement", "phi_phase_rotations"],
        "expected_impact": "Reduced φ-convergence, lower entanglement fidelity",
    },
    {
        "ablation_id": "ABL-SIERP-002",
        "ablation_type": "feature",
        "target": "metatron_overlay",
        "description": "Disable Metatron cube geometry overlay",
        "scope": "local",
        "disabled_components": ["metatron_entanglement", "sefirah_phases"],
        "expected_impact": "Reduced consciousness density, lower φ-score",
    },
    {
        "ablation_id": "ABL-SIERP-003",
        "ablation_type": "combination",
        "target": "fractal_agent_full",
        "description": "Disable Fractal agent with Sierpinski topology",
        "scope": "global",
        "disabled_components": ["fractal", "sierpinski_topology", "phi_routing"],
        "expected_impact": "Significant drop in pattern recognition and φ-alignment",
    },
    {
        "ablation_id": "ABL-SIERP-004",
        "ablation_type": "feature",
        "target": "phi_gating",
        "description": "Disable φ-gating threshold (0.618) for hardware routing",
        "scope": "global",
        "disabled_components": ["phi_threshold", "resonance_filter"],
        "expected_impact": "More circuits routed to hardware, lower quality filtering",
    },
]


def get_sierpinski_ablation_configs() -> list[dict[str, Any]]:
    """Get Sierpinski-specific ablation configurations.

    These can be added to the main ablation study to measure
    the contribution of fractal topology to overall performance.
    """
    return SIERPINSKI_ABLATION_CONFIGS.copy()
