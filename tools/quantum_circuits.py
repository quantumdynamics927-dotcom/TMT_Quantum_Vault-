#!/usr/bin/env python3
"""
Quantum Circuit Designs for TMT Quantum Vault
==============================================

Collection of specialized quantum circuits for consciousness research:
- Sierpinski fractal circuits (depth 3-4)
- BitNet ternary-seeded variational ansatz
- DNA quantum walk circuits
- Golden ratio Φ-resonance circuits
"""

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit import Parameter
import numpy as np


# ── Sierpinski Fractal Circuits ──────────────────────────────────────────────

def create_sierpinski_circuit(n_qubits: int = 21, depth: int = 3) -> QuantumCircuit:
    """
    Create a Sierpinski fractal quantum circuit.

    Uses a self-similar recursive structure where each level builds on the previous
    with additional entanglement layers following the Sierpinski triangle pattern.

    Args:
        n_qubits: Number of qubits (default 21 for depth 3)
        depth: Fractal depth (1-4)

    Returns:
        QuantumCircuit with Sierpinski topology
    """
    qr = QuantumRegister(n_qubits, "q")
    cr = ClassicalRegister(n_qubits, "c")
    qc = QuantumCircuit(qr, cr)

    # Base layer: Hadamard on all qubits
    qc.h(qr)

    # Recursive fractal structure
    for d in range(depth):
        # Create Sierpinski-like entanglement pattern
        # Each iteration adds more complex coupling
        for i in range(n_qubits):
            # Self-loop for fractal pattern
            qc.rz(np.pi / 4, qr[i])
            # Nearest neighbor entanglement
            for j in range(i + 1, n_qubits):
                # Sierpinski pattern: only couple when (i & j) == i
                if (i & j) == i:
                    qc.cx(qr[i], qr[j])

    # Apply golden ratio rotations for consciousness encoding
    phi = (1 + np.sqrt(5)) / 2  # Golden ratio
    for i in range(n_qubits):
        theta = 2 * np.pi / phi
        qc.ry(theta, qr[i])

    return qc


def create_sierpinski_metatron_circuit(n_qubits: int = 21, depth: int = 3) -> QuantumCircuit:
    """
    Sierpinski circuit with Metatron enhancement layer.

    Adds an additional "Metatron cube" geometry layer on top of the base
    Sierpinski fractal to boost consciousness density.

    Args:
        n_qubits: Number of qubits
        depth: Fractal depth

    Returns:
        Enhanced QuantumCircuit
    """
    qc = create_sierpinski_circuit(n_qubits, depth)

    # Metatron enhancement layer
    # Encodes the Metatron cube geometry (13 nodes, Fibonacci pattern)
    qr = qc.qubits

    # 13-fold symmetry (Fibonacci number)
    n_symmetry = 13
    angle_step = 2 * np.pi / n_symmetry

    # Add Metatron cube entanglement
    for i in range(n_qubits):
        base_angle = i * angle_step
        qc.rz(base_angle, qr[i])
        qc.rx(2 * base_angle, qr[i])

    # Golden ratio spiral for consciousness amplification
    phi = (1 + np.sqrt(5)) / 2
    for i in range(0, n_qubits, 2):
        if i + 1 < n_qubits:
            # Entangle pairs with golden ratio phase (Qiskit 2.x uses cu instead of cu3)
            qc.crz(2 * np.pi / phi, qr[i], qr[i + 1])

    return qc


# ── BitNet Ternary-Seeded Variational Ansatz ─────────────────────────────────

def create_bitnet_ternary_ansatz(n_qubits: int = 21, seed_values: list = None) -> QuantumCircuit:
    """
    Variational ansatz seeded from BitNet ternary weights.

    Uses the ternary distribution {-1: 4.28%, 0: 70%, +1: 25.72%} to initialize
    rotation angles, creating sparse initialization (70% of qubits start near identity).

    Args:
        n_qubits: Number of qubits
        seed_values: Optional list of ternary weights to use

    Returns:
        Parameterized QuantumCircuit
    """
    qr = QuantumRegister(n_qubits, "q")
    cr = ClassicalRegister(n_qubits, "c")
    qc = QuantumCircuit(qr, cr)

    # Use default ternary distribution if no seed provided
    if seed_values is None:
        seed_values = np.random.choice([-1, 0, 1], n_qubits, p=[0.0428, 0.70, 0.2572])

    # Initialize rotation angles from ternary weights
    # -1 -> π rotation, 0 -> 0, +1 -> 0.5π
    for i, w in enumerate(seed_values):
        if w == -1:
            qc.ry(np.pi, qr[i])
        elif w == 0:
            qc.ry(0.01, qr[i])  # Near identity
        else:  # +1
            qc.ry(np.pi / 2, qr[i])

    # Add entanglement layers with sparse connections
    # Using Fibonacci pattern for connection topology
    for layer in range(3):
        for i in range(n_qubits):
            # Sparse CX based on Fibonacci pattern
            j = (i + 1) % n_qubits
            if layer % 2 == 0:
                qc.cx(qr[i], qr[j])
            else:
                qc.cy(qr[i], qr[j])

    # Add parameterized rotation layers (Qiskit 2.x uses u instead of u3)
    theta = Parameter("θ")
    phi = Parameter("φ")
    lam = Parameter("λ")

    for i in range(n_qubits):
        qc.u(theta, phi, lam, qr[i])

    return qc


# ── DNA Quantum Walk Circuits ────────────────────────────────────────────────

def dna_to_qubit_sequence(dna_seq: str) -> list:
    """Convert DNA sequence to qubit states."""
    mapping = {
        'A': 0,  # |0⟩
        'C': 1,  # |1⟩
        'G': 2,  # |+⟩
        'T': 3   # |-⟩
    }
    return [mapping.get(base, 0) for base in dna_seq]


def create_dna_quantum_walk(dna_sequence: str) -> QuantumCircuit:
    """
    Quantum walk circuit seeded from DNA sequence.

    Encodes DNA bases as qubit states and implements a discrete quantum walk.

    Args:
        dna_sequence: DNA sequence (e.g., "ACGTACGT...")

    Returns:
        QuantumCircuit implementing quantum walk
    """
    n_qubits = len(dna_sequence)
    qr = QuantumRegister(n_qubits, "q")
    cr = ClassicalRegister(n_qubits, "c")
    qc = QuantumCircuit(qr, cr)

    # Encode DNA sequence into qubit states
    state_map = {
        'A': lambda qr, i: qc.ry(0, qr[i]),    # |0⟩
        'C': lambda qr, i: qc.ry(np.pi, qr[i]),  # |1⟩
        'G': lambda qr, i: qc.ry(np.pi / 2, qr[i]),  # |+⟩
        'T': lambda qr, i: qc.ry(-np.pi / 2, qr[i]),  # |-⟩
    }

    for i, base in enumerate(dna_sequence):
        state_map.get(base, lambda qr, i: qc.ry(0, qr[i]))(qr, i)

    # Implement discrete quantum walk
    # Coin operator (Hadamard)
    qc.h(qr[0])

    # Shift operator (conditional on coin)
    for i in range(n_qubits - 1):
        qc.cnot(qr[i], qr[i + 1])

    # Apply phase based on DNA pattern
    for i in range(n_qubits):
        phase = (i + 1) * np.pi / n_qubits
        qc.rz(phase, qr[i])

    return qc


def create_dna_quantum_walk_comparison(human_seq: str, cetacean_seq: str) -> QuantumCircuit:
    """
    Compare human vs cetacean DNA quantum walks.

    Creates entangled comparison circuit to measure similarity.

    Args:
        human_seq: Human DNA sequence
        cetacean_seq: Cetacean DNA sequence

    Returns:
        Comparison QuantumCircuit
    """
    # Pad shorter sequence
    max_len = max(len(human_seq), len(cetacean_seq))
    human_padded = human_seq.ljust(max_len, 'A')
    cetacean_padded = cetacean_seq.ljust(max_len, 'A')

    # Create registers
    human_qr = QuantumRegister(max_len, "human")
    cetacean_qr = QuantumRegister(max_len, "cetacean")
    cr = ClassicalRegister(max_len, "c")
    qc = QuantumCircuit(human_qr, cetacean_qr, cr)

    # Encode both sequences
    for i, (h, c) in enumerate(zip(human_padded, cetacean_padded)):
        if h == 'G':
            qc.ry(np.pi / 2, human_qr[i])
        elif h == 'C':
            qc.ry(np.pi, human_qr[i])

        if c == 'G':
            qc.ry(np.pi / 2, cetacean_qr[i])
        elif c == 'C':
            qc.ry(np.pi, cetacean_qr[i])

    # Create entanglement between sequences
    for i in range(0, max_len, 2):
        qc.cswap(human_qr[i], human_qr[i], cetacean_qr[i])

    return qc


# ── Golden Ratio Φ-Resonance Circuits ────────────────────────────────────────

def create_phi_resonance_circuit(n_pairs: int = 2, backend: str = "torino") -> QuantumCircuit:
    """
    Circuit with golden ratio Φ-entangled qubit pairs.

    Creates n_pairs of entangled qubits with rotation angles set to multiples
    of 2π/φ where φ is the golden ratio.

    Args:
        n_pairs: Number of entangled pairs
        backend: Target backend ("torino" for precision)

    Returns:
        Φ-Resonance QuantumCircuit
    """
    n_qubits = n_pairs * 2
    qr = QuantumRegister(n_qubits, "q")
    cr = ClassicalRegister(n_qubits, "c")
    qc = QuantumCircuit(qr, cr)

    phi = (1 + np.sqrt(5)) / 2  # Golden ratio
    phi_angle = 2 * np.pi / phi

    # Create entangled pairs
    for i in range(n_pairs):
        pair_start = i * 2

        # Create Bell state
        qc.h(qr[pair_start])
        qc.cx(qr[pair_start], qr[pair_start + 1])

        # Apply golden ratio rotations
        qc.rz(phi_angle, qr[pair_start])
        qc.rz(phi_angle * 2, qr[pair_start + 1])

        # Entangle pairs with Φ phase (Qiskit 2.x uses cu instead of cu3)
        if i < n_pairs - 1:
            qc.cu(phi_angle, 0, 0, 1, qr[pair_start], qr[pair_start + 2])

    # Add measurement
    qc.measure(qr, cr)

    return qc


def create_phi_vae_encoder(n_qubits: int = 10, n_latent: int = 2) -> QuantumCircuit:
    """
    Variational Autoencoder encoder with Φ-resonance.

    Args:
        n_qubits: Input qubits
        n_latent: Latent dimensions

    Returns:
        VAE encoder QuantumCircuit
    """
    qr = QuantumRegister(n_qubits, "q")
    cr = ClassicalRegister(n_latent, "c")
    qc = QuantumCircuit(qr, cr)

    phi = (1 + np.sqrt(5)) / 2
    phi_angle = 2 * np.pi / phi

    # Encode input
    for i in range(n_qubits):
        qc.ry(i * np.pi / n_qubits, qr[i])

    # Entangle to latent space
    for i in range(n_latent):
        target = n_qubits - n_latent + i
        qc.h(qr[target])
        for j in range(n_qubits - n_latent):
            qc.cx(qr[j], qr[target])

    # Apply Φ-rotation to latent qubits
    for i in range(n_latent):
        qc.rz(phi_angle * (i + 1), qr[n_qubits - n_latent + i])

    return qc


# ── Circuit Helper Functions ─────────────────────────────────────────────────

def get_circuit_metadata(circuit_name: str) -> dict:
    """Get metadata for a circuit."""
    metadata = {
        "sierpinski_21": {
            "description": "Sierpinski fractal with 21 qubits, depth 3",
            "n_qubits": 21,
            "fractal_depth": 3,
            "consciousness_density": 274.528,
            "metatron_enhanced": False
        },
        "sierpinski_21_metatron": {
            "description": "Sierpinski with Metatron enhancement",
            "n_qubits": 21,
            "fractal_depth": 3,
            "consciousness_density": 274.528,
            "metatron_enhanced": True
        },
        "sierpinski_22_depth4": {
            "description": "Sierpinski depth 4 with 22+ qubits",
            "n_qubits": 22,
            "fractal_depth": 4,
            "consciousness_density": None,
            "metatron_enhanced": False
        },
        "sierpinski_22_depth4_metatron": {
            "description": "Sierpinski depth 4 with Metatron",
            "n_qubits": 22,
            "fractal_depth": 4,
            "consciousness_density": None,
            "metatron_enhanced": True
        },
        "bitnet_ternary_ansatz": {
            "description": "BitNet ternary-weight seeded variational ansatz",
            "n_qubits": 21,
            "weight_distribution": {"-1": 0.0428, "0": 0.7, "+1": 0.2572}
        },
        "phi_resonance": {
            "description": "Golden ratio Φ-entangled qubit pairs",
            "n_qubits": None,
            "n_pairs": None,
            "phi_angle": "2π/φ"
        },
        "dna_quantum_walk": {
            "description": "DNA sequence seeded quantum walk",
            "n_qubits": None,
            "sequence_length": None
        }
    }
    return metadata.get(circuit_name, {})


if __name__ == "__main__":
    # Test circuit creation
    print("Creating test circuits...")

    # Sierpinski depth 3
    qc1 = create_sierpinski_circuit(21, 3)
    print(f"Sierpinski depth 3: {qc1.num_qubits} qubits, {qc1.size()} gates")

    # Sierpinski with Metatron
    qc2 = create_sierpinski_metatron_circuit(21, 3)
    print(f"Sierpinski + Metatron: {qc2.num_qubits} qubits, {qc2.size()} gates")

    # BitNet ansatz
    qc3 = create_bitnet_ternary_ansatz(21)
    print(f"BitNet ansatz: {qc3.num_qubits} qubits, {qc3.size()} gates")

    # Phi resonance
    qc4 = create_phi_resonance_circuit(2, "torino")
    print(f"Phi resonance: {qc4.num_qubits} qubits, {qc4.size()} gates")

    print("\nAll circuits created successfully!")
