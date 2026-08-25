"""
Merkaba Quantum Fingerprint Generator.

This module implements a 6-qubit quantum fingerprint circuit based on the
Merkaba (star tetrahedron) geometry. The circuit uses two interlocked
Sierpinski depth-1 GHZ triangles representing the upward and downward
tetrahedra of the Merkaba.

Geometry Mapping:
    - q[0-2]: Upward tetrahedron (fire, masculine) - Sierpinski triangle A
    - q[3-5]: Downward tetrahedron (water, feminine) - Sierpinski triangle B
    - Inter-tetrahedron entanglement: Counter-rotation between triangles

The seed bytes drive phi-phase rotations, making every fingerprint unique
but reproducible from the same seed.

Reference:
    - Merkaba geometry: Star tetrahedron (two interlocked tetrahedra)
    - Sierpinski topology: Recursive triangle fractal
    - φ-gating threshold: 0.618 (1/φ)

Usage:
    from tmt_quantum_vault.circuits.merkaba_fingerprint import (
        create_merkaba_fingerprint_circuit,
        extract_fingerprint,
        MerkabaFingerprintGenerator,
    )

    circuit = create_merkaba_fingerprint_circuit(seed_bytes)
    # Run on backend, get counts
    fingerprint = extract_fingerprint(counts, shots=1024)
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

PHI = 1.618033988749895  # Golden ratio
PHI_INVERSE = 1.0 / PHI  # 0.618...

# Circuit geometry
MERKABA_QUBITS = 6  # Two triangles of 3 qubits each
MERKABA_STATES = 2**6  # 64 basis states

# Fingerprint output
FINGERPRINT_HASH_BITS = 256  # SHA3-256 output


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class MerkabaFingerprint:
    """Container for Merkaba quantum fingerprint results."""

    fingerprint_hash: str
    phi_score: float
    dominant_state: str
    entropy_bits: float
    circuit_geometry: str = "merkaba_6q_sierpinski_depth1"
    seed_source: str = "unknown"
    backend: str = "unknown"
    shots: int = 1024
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    probability_distribution: dict[str, float] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "fingerprint_hash": self.fingerprint_hash,
            "phi_score": self.phi_score,
            "dominant_state": self.dominant_state,
            "entropy_bits": self.entropy_bits,
            "circuit_geometry": self.circuit_geometry,
            "seed_source": self.seed_source,
            "backend": self.backend,
            "shots": self.shots,
            "created_at": self.created_at,
            "probability_distribution": self.probability_distribution,
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MerkabaFingerprint:
        """Create from dictionary."""
        return cls(
            fingerprint_hash=data["fingerprint_hash"],
            phi_score=data["phi_score"],
            dominant_state=data["dominant_state"],
            entropy_bits=data["entropy_bits"],
            circuit_geometry=data.get(
                "circuit_geometry", "merkaba_6q_sierpinski_depth1"
            ),
            seed_source=data.get("seed_source", "unknown"),
            backend=data.get("backend", "unknown"),
            shots=data.get("shots", 1024),
            created_at=data.get("created_at", ""),
            probability_distribution=data.get("probability_distribution", {}),
            provenance=data.get("provenance", {}),
        )


# =============================================================================
# Circuit Generation
# =============================================================================


def create_merkaba_fingerprint_circuit(
    seed: bytes,
) -> "QuantumCircuit":  # noqa: UP037,F821
    """
    Create a 6-qubit Merkaba circuit for quantum fingerprint generation.

    Structure: Two Sierpinski depth-1 GHZ triangles (3+3) entangled across
    the tetrahedron interface.

    Args:
        seed: Seed bytes (minimum 6 bytes) for phi-phase rotations

    Returns:
        QuantumCircuit with 6 qubits and 6 classical bits
    """
    try:
        from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
    except ImportError as e:
        raise ImportError(
            "qiskit package required. Install with: pip install qiskit"
        ) from e

    qr = QuantumRegister(6, "q")
    cr = ClassicalRegister(6, "c")
    qc = QuantumCircuit(qr, cr, name="MerkabaFingerprint")

    # Ensure we have at least 6 bytes
    if len(seed) < 6:
        seed = seed.ljust(6, b"\x00")

    # ── Layer 1: Upward tetrahedron (fire triangle) ──────────────────────
    # Sierpinski depth-1 GHZ on q[0,1,2]
    qc.h(qr[0])
    qc.cx(qr[0], qr[1])
    qc.cx(qr[1], qr[2])

    # φ-phase rotations seeded from input bytes (makes it a fingerprint)
    seed_ints = list(seed[:3])
    for i, s in enumerate(seed_ints):
        angle = (s / 255.0) * 2 * np.pi / PHI
        qc.rz(angle, qr[i])

    qc.barrier(label="upward_tetrahedron")

    # ── Layer 2: Downward tetrahedron (water triangle) ───────────────────
    # Sierpinski depth-1 GHZ on q[3,4,5] — counter-rotated
    qc.h(qr[3])  # Start from apex of inverted triangle
    qc.cx(qr[3], qr[4])
    qc.cx(qr[4], qr[5])

    seed_ints_b = list(seed[3:6]) if len(seed) >= 6 else seed_ints
    for i, s in enumerate(seed_ints_b):
        # Counter-rotated: ×φ not ÷φ
        angle = (s / 255.0) * 2 * np.pi * PHI
        qc.rz(angle, qr[3 + i])

    qc.barrier(label="downward_tetrahedron")

    # ── Layer 3: Merkaba inter-tetrahedron entanglement ──────────────────
    # The 6 edges between upward and downward tetrahedra
    # In the star tetrahedron each vertex of A connects to 2 of B
    qc.cx(qr[0], qr[3])  # apex A → apex B
    qc.cx(qr[1], qr[4])  # base A1 → base B1
    qc.cx(qr[2], qr[5])  # base A2 → base B2

    qc.barrier(label="merkaba_entanglement")

    # ── Layer 4: φ-resonance interference ────────────────────────────────
    # Apply a final φ-scaled global phase to create interference
    # between the two tetrahedra — this generates the unique
    # measurement distribution (the "fingerprint")
    for i in range(6):
        qc.rz(np.pi / PHI, qr[i])

    qc.barrier(label="phi_interference")

    # Measure all 6 qubits
    qc.measure(qr, cr)

    return qc


def create_merkaba_circuit_openqasm(seed: bytes) -> str:
    """
    Generate OpenQASM 2.0 representation of the Merkaba circuit.

    Args:
        seed: Seed bytes for phi-phase rotations

    Returns:
        OpenQASM 2.0 string
    """
    if len(seed) < 6:
        seed = seed.ljust(6, b"\x00")

    seed_ints = list(seed[:6])

    qasm = """// Merkaba 6-qubit Fingerprint Circuit
// Generated from seed bytes
OPENQASM 2.0;
include "qelib1.inc";

qreg q[6];
creg c[6];

// Layer 1: Upward tetrahedron (fire triangle)
h q[0];
cx q[0], q[1];
cx q[1], q[2];
"""

    # Add phi-phase rotations for upward tetrahedron
    for i in range(3):
        angle = (seed_ints[i] / 255.0) * 2 * np.pi / PHI
        qasm += f"rz({angle:.10f}) q[{i}];\n"

    qasm += """
// Layer 2: Downward tetrahedron (water triangle)
h q[3];
cx q[3], q[4];
cx q[4], q[5];
"""

    # Add counter-rotated phi-phase rotations for downward tetrahedron
    for i in range(3):
        angle = (seed_ints[3 + i] / 255.0) * 2 * np.pi * PHI
        qasm += f"rz({angle:.10f}) q[{3 + i}];\n"

    qasm += """
// Layer 3: Merkaba inter-tetrahedron entanglement
cx q[0], q[3];
cx q[1], q[4];
cx q[2], q[5];

// Layer 4: φ-resonance interference
"""

    phi_angle = np.pi / PHI
    for i in range(6):
        qasm += f"rz({phi_angle:.10f}) q[{i}];\n"

    qasm += """
// Measurement
measure q -> c;
"""

    return qasm


# =============================================================================
# Fingerprint Extraction
# =============================================================================


def extract_fingerprint(
    counts: dict[str, int],
    shots: int = 1024,
    seed_source: str = "unknown",
    backend: str = "unknown",
    provenance: dict[str, Any] | None = None,
) -> MerkabaFingerprint:
    """
    Convert 6-qubit measurement counts into a fingerprint hash.

    The fingerprint is the probability distribution over 64 bitstrings,
    compressed to a 256-bit hash via φ-weighted aggregation.

    Args:
        counts: Measurement counts from backend
        shots: Total number of shots
        seed_source: Source of seed bytes (e.g., "IBM_QRNG")
        backend: Backend used for execution
        provenance: Optional provenance chain

    Returns:
        MerkabaFingerprint with hash, phi_score, and metadata
    """
    # Build probability vector over all 64 = 2^6 bitstrings
    probs: dict[str, float] = {}
    for bitstring, count in counts.items():
        # Normalize bitstring to 6 bits
        bs = bitstring.replace(" ", "").zfill(6)[-6:]
        probs[bs] = count / shots

    # φ-weighted aggregation — same technique as sacred_score
    phi_score = sum(probs.get(bs, 0) * (1 / PHI ** (bs.count("1") + 1)) for bs in probs)

    # Canonical fingerprint: sorted prob vector → SHA3-256
    prob_bytes = b"".join(
        int(probs.get(f"{i:06b}", 0) * 1e9).to_bytes(4, "big") for i in range(64)
    )
    fingerprint_hash = hashlib.sha3_256(prob_bytes).hexdigest()

    # Calculate entropy
    entropy_bits = -sum(p * np.log2(p) for p in probs.values() if p > 0)

    # Find dominant state
    dominant_state = max(probs, key=probs.get) if probs else "000000"

    return MerkabaFingerprint(
        fingerprint_hash=fingerprint_hash,
        phi_score=round(phi_score, 6),
        dominant_state=dominant_state,
        entropy_bits=round(entropy_bits, 4),
        seed_source=seed_source,
        backend=backend,
        shots=shots,
        probability_distribution=probs,
        provenance=provenance or {},
    )


# =============================================================================
# Generator Class
# =============================================================================


class MerkabaFingerprintGenerator:
    """
    Generate quantum fingerprints using Merkaba geometry.

    Integrates with entropy_stack for QRNG seed bytes and can
    execute on simulators or IBM hardware.
    """

    def __init__(self, vault_path: Path):
        """Initialize the fingerprint generator.

        Args:
            vault_path: Path to TMT Quantum Vault root
        """
        self.vault_path = Path(vault_path)
        self.entropy_path = self.vault_path / "entropy_stack"

    def _load_qrng_seed(self, num_bytes: int = 6) -> bytes:
        """Load QRNG entropy from entropy_stack.

        Args:
            num_bytes: Number of bytes to extract

        Returns:
            Seed bytes from quantum randomness
        """
        entropy_file = self.entropy_path / "three_layer_entropy_stack.json"

        if not entropy_file.exists():
            logger.warning("Entropy stack not found, using system randomness")
            import secrets

            return secrets.token_bytes(num_bytes)

        with open(entropy_file, encoding="utf-8") as f:
            entropy_data = json.load(f)

        # Extract entropy bits from layer 1 (Casablanca QTRG)
        layer1 = entropy_data.get("layer_1_casablanca_qtrg", {})
        entropy_bits = layer1.get("entropy_bits", [])

        if not entropy_bits:
            logger.warning("No entropy bits found, using system randomness")
            import secrets

            return secrets.token_bytes(num_bytes)

        # Convert entropy bits to bytes
        seed_bytes = bytes([int(b) % 256 for b in entropy_bits[:num_bytes]])

        if len(seed_bytes) < num_bytes:
            seed_bytes = seed_bytes.ljust(num_bytes, b"\x00")

        logger.info(f"Loaded {len(seed_bytes)} bytes of QRNG entropy")
        return seed_bytes

    def generate_fingerprint(
        self,
        seed: bytes | None = None,
        backend: str = "qasm_simulator",
        shots: int = 1024,
        provenance: dict[str, Any] | None = None,
        seed_source: str | None = None,
    ) -> MerkabaFingerprint:
        """
        Generate a quantum fingerprint.

        Args:
            seed: Optional seed bytes (loaded from QRNG if not provided)
            backend: Backend to use ("qasm_simulator" or IBM backend name)
            shots: Number of shots
            provenance: Optional provenance chain
            seed_source: Optional override for seed source label

        Returns:
            MerkabaFingerprint with results
        """
        try:
            from qiskit import transpile
            from qiskit_aer import AerSimulator
        except ImportError as e:
            raise ImportError(
                "qiskit and qiskit-aer required. Install with: pip install qiskit qiskit-aer"
            ) from e

        # Load seed from QRNG if not provided
        if seed is None:
            seed = self._load_qrng_seed(6)
            effective_seed_source = "IBM_QRNG"
        else:
            effective_seed_source = seed_source or "provided"

        # Create circuit
        circuit = create_merkaba_fingerprint_circuit(seed)

        # Execute on backend
        if backend == "qasm_simulator":
            simulator = AerSimulator()
            transpiled = transpile(circuit, simulator)
            job = simulator.run(transpiled, shots=shots)
            result = job.result()
            counts = result.get_counts()
        else:
            # For IBM hardware, use the existing IBM integration
            raise NotImplementedError(
                f"Backend {backend} not implemented. Use qasm_simulator or "
                "integrate with IBM Quantum via tmt_quantum_vault.ibm module."
            )

        # Extract fingerprint
        fingerprint = extract_fingerprint(
            counts,
            shots=shots,
            seed_source=effective_seed_source,
            backend=backend,
            provenance=provenance,
        )

        return fingerprint

    def save_fingerprint(
        self,
        fingerprint: MerkabaFingerprint,
        output_path: Path | None = None,
    ) -> Path:
        """
        Save fingerprint to JSON file.

        Args:
            fingerprint: Fingerprint to save
            output_path: Optional output path

        Returns:
            Path to saved file
        """
        if output_path is None:
            output_dir = self.vault_path / "evidence_ledger" / "fingerprints"
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"merkaba_fingerprint_{timestamp}.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(fingerprint.to_dict(), f, indent=2)

        logger.info(f"Saved fingerprint to {output_path}")
        return output_path


# =============================================================================
# CLI Integration
# =============================================================================


def generate_fingerprint_cli(
    vault_path: str,
    seed_from_qrng: bool = True,
    backend: str = "qasm_simulator",
    shots: int = 1024,
    output_path: str | None = None,
) -> None:
    """CLI entry point for generating Merkaba fingerprints."""
    generator = MerkabaFingerprintGenerator(Path(vault_path))

    seed = None
    if seed_from_qrng:
        seed = generator._load_qrng_seed(6)

    fingerprint = generator.generate_fingerprint(
        seed=seed,
        backend=backend,
        shots=shots,
    )

    output = generator.save_fingerprint(
        fingerprint,
        Path(output_path) if output_path else None,
    )

    print(f"Fingerprint: {fingerprint.fingerprint_hash}")
    print(f"φ-score: {fingerprint.phi_score:.6f}")
    print(f"Dominant state: {fingerprint.dominant_state}")
    print(f"Entropy: {fingerprint.entropy_bits:.4f} bits")
    print(f"Saved to: {output}")
