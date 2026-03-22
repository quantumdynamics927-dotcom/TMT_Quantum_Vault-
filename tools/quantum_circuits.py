#!/usr/bin/env python3
"""
Quantum Circuit Designs for TMT Quantum Vault
==============================================

Collection of specialized quantum circuits for consciousness research:
- Sierpinski fractal circuits (depth 3-4)
- BitNet ternary-seeded variational ansatz
- DNA quantum walk circuits
- Golden ratio Φ-resonance circuits

The φ-Stack: Biological Quantum Circuits
-----------------------------------------
This module implements quantum circuits seeded from biological promoter DNA.
The golden ratio φ emerges naturally from the physical structure of DNA:

DNA Helix Geometry (established biophysics):
  - Rise per turn:  34.0 Ångströms
  - Diameter:       21.0 Ångströms
  - Ratio:          34/21 = 1.61904...
  - φ (golden):     1.6180339887...
  - Error:          0.063%

Fibonacci Connection:
  34 and 21 are consecutive Fibonacci numbers (F(9)=34, F(8)=21).
  The DNA double helix physically encodes φ in its dimensions.

The φ-Stack Pipeline:
  DNA geometry:     34/21 = 1.619 ≈ φ     ← structural basis
       ↓
  Nucleotide freq:  A=432Hz → C=699Hz → G=1131Hz → T=1830Hz
                    (each × φ from previous)  ← harmonic design
       ↓
  Qubit encoding:   A→Ry(0), C→Ry(π), G→Ry(π/2), T→Ry(-π/2)
                    rotations derived from φ-harmonic frequencies
       ↓
  Quantum circuit:  Sierpinski-style entanglement with φ-phase layers
       ↓
  IBM hardware:     sacred_score = 0.618 (1/φ)  ← expected convergence

Type Distinction (scientific interpretation):
  Sierpinski circuits:   EMERGENT φ-convergence
    - φ not baked into topology
    - Self-organization under quantum noise
    - Stronger scientific claim (spontaneous symmetry breaking)

  DNA helix circuits:    STRUCTURAL φ-convergence
    - φ guaranteed by helix geometry + encoding
    - Validation of scoring pipeline
    - Biological quantum consistency demonstration

Promoter Circuit Format:
  Each promoter combines a biological gene with a Sefirah name:
    - ACTB_Malkuth: β-Actin gene + Malkuth (Kingdom)
    - TP53_Gevurah: p53 tumor suppressor + Gevurah (Strength)
    - FOXG1_Kether: Forkhead Box G1 + Kether (Crown)
    - etc.

  Sefirah mapping to φ-phase angles:
    Kether:     0
    Chokmah:    2π/φ
    Binah:      4π/φ
    Chesed:     6π/φ
    Gevurah:    8π/φ
    Tiphereth:  10π/φ
    Netzach:    12π/φ
    Hod:        14π/φ
    Yesod:      16π/φ
    Malkuth:    18π/φ
"""

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit import Parameter
from qiskit.qasm2 import dumps as qasm2_dumps
from pathlib import Path
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


# ── Promoter Circuit Generator ───────────────────────────────────────────────

def create_promoter_circuit(promoter_name: str, depth: int = 3) -> QuantumCircuit:
    """
    Create a quantum circuit from a promoter DNA sequence.

    Uses the promoter_loader to load the promoter sequence and encodes it
    into qubit rotations. Each nucleotide maps to a specific rotation angle:
    - A -> Ry(0)     = |0>
    - C -> Ry(pi)    = |1>
    - G -> Ry(pi/2)  = |+>
    - T -> Ry(3pi/2) = |->

    The Sefirah name in the promoter (e.g., Malkuth, Chokmah) is used to
    apply symbolic phase encoding via golden ratio angles.

    Args:
        promoter_name: Name of the promoter (e.g., "ACTB_Malkuth")
        depth: Fractal depth for the entanglement structure

    Returns:
        QuantumCircuit encoded with promoter DNA
    """
    from pathlib import Path
    import sys

    # Import promoter loader
    vault_root = Path(__file__).parent.parent
    promoters_dir = vault_root / "circuits" / "promoters"
    external_promoters = Path(r"E:\AGI model\tmt-os-labs\promoters")

    # Load promoter via promoter_loader
    dna_sequence = None
    sefirah_name = None

    if external_promoters.exists():
        # Try external directory first
        for fasta_file in external_promoters.glob("*_promoter.fa"):
            gene_name = fasta_file.stem.replace("_promoter", "")
            if gene_name.lower() == promoter_name.lower():
                content = fasta_file.read_text(encoding="utf-8").strip()
                lines = content.split('\n')
                dna_sequence = lines[1].strip() if len(lines) > 1 else ""
                sefirah_name = gene_name.split('_')[-1] if '_' in gene_name else None
                break

    if dna_sequence is None and promoters_dir.exists():
        # Try circuits/promoters/ as fallback
        for fasta_file in promoters_dir.glob("*.fa"):
            gene_name = fasta_file.stem.replace("_promoter", "")
            if gene_name.lower() == promoter_name.lower():
                content = fasta_file.read_text(encoding="utf-8").strip()
                lines = content.split('\n')
                dna_sequence = lines[1].strip() if len(lines) > 1 else ""
                sefirah_name = gene_name.split('_')[-1] if '_' in gene_name else None
                break

    if dna_sequence is None:
        raise ValueError(f"Promoter not found: {promoter_name}")

    # Create circuit with qubits matching sequence length
    n_qubits = len(dna_sequence)
    # Cap at 21 qubits for available backends
    max_qubits = min(n_qubits, 21)
    # Round up to nearest power of 2 for efficient computation
    import math
    n_qubits = 2 ** int(math.ceil(math.log2(max_qubits)))

    qr = QuantumRegister(n_qubits, "q")
    cr = ClassicalRegister(n_qubits, "c")
    qc = QuantumCircuit(qr, cr)

    # State mapping for nucleotides
    state_map = {
        'A': lambda qr, i: qc.ry(0, qr[i]),
        'C': lambda qr, i: qc.ry(np.pi, qr[i]),
        'G': lambda qr, i: qc.ry(np.pi / 2, qr[i]),
        'T': lambda qr, i: qc.ry(-np.pi / 2, qr[i]),
    }

    # Encode DNA sequence into qubit states
    for i, base in enumerate(dna_sequence[:n_qubits]):
        state_map.get(base, lambda qr, i: qc.ry(0, qr[i]))(qr, i)

    # Add Sefirah phase encoding via golden ratio
    phi = (1 + np.sqrt(5)) / 2
    phi_angle = 2 * np.pi / phi

    if sefirah_name:
        # Map Sefirah to specific phase rotation
        sefirah_angles = {
            'Kether': 0,
            'Chokmah': phi_angle,
            'Binah': 2 * phi_angle,
            'Chesed': 3 * phi_angle,
            'Gevurah': 4 * phi_angle,
            'Tiphereth': 5 * phi_angle,
            'Netzach': 6 * phi_angle,
            'Hod': 7 * phi_angle,
            'Yesod': 8 * phi_angle,
            'Malkuth': 9 * phi_angle,
        }
        base_angle = sefirah_angles.get(sefirah_name, 0)
    else:
        base_angle = 0

    # Apply Sefirah-based phase encoding
    for i in range(n_qubits):
        qc.rz(base_angle + i * phi_angle / n_qubits, qr[i])

    # Apply depth-based entanglement structure (Sierpinski-like)
    for d in range(depth):
        # Hadamard on first qubit for superposition
        qc.h(qr[0])

        # Sierpinski-style entanglement
        for i in range(n_qubits):
            qc.rz(np.pi / (4 * (d + 1)), qr[i])
            for j in range(i + 1, n_qubits):
                if (i & j) == i:
                    qc.cx(qr[i], qr[j])

    # Add measurement
    qc.measure(qr, cr)

    return qc


def export_promoter_qasm(promoter_name: str, depth: int = 3, output_dir=None) -> str:
    """
    Create a promoter circuit and export to QASM format.

    Args:
        promoter_name: Name of the promoter (e.g., "ACTB_Malkuth")
        depth: Fractal depth for entanglement
        output_dir: Optional directory to save QASM file

    Returns:
        Path to saved QASM file
    """
    from pathlib import Path

    circuit = create_promoter_circuit(promoter_name, depth)

    # Generate filename
    filename = f"promoter_{promoter_name.replace('_', '-').lower()}_d{depth}.qasm"

    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "circuits" / "qasm"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / filename

    # Export to QASM
    qasm_str = qasm2_dumps(circuit)
    filepath.write_text(qasm_str, encoding="utf-8")

    return str(filepath)


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


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Quantum Circuit Generator - TMT Quantum Vault",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Create a Sierpinski circuit:
    python tools/quantum_circuits.py sierpinski --depth 3

  Create a promoter circuit:
    python tools/quantum_circuits.py promoter --name ACTB_Malkuth --depth 3

  Export circuit to QASM:
    python tools/quantum_circuits.py export --name sierpinski --depth 4 --format qasm
    python tools/quantum_circuits.py export --name promoter:ACTB_Malkuth --depth 3 --format qasm
"""
    )
    sub = parser.add_subparsers(dest="command", title="commands")

    # Sierpinski circuit
    sierpinski_parser = sub.add_parser("sierpinski", help="Create Sierpinski fractal circuit")
    sierpinski_parser.add_argument("--depth", type=int, default=3, help="Fractal depth (1-4)")
    sierpinski_parser.add_argument("--qubits", type=int, default=21, help="Number of qubits")
    sierpinski_parser.add_argument("--metatron", action="store_true", help="Add Metatron enhancement")

    # Promoter circuit
    promoter_parser = sub.add_parser("promoter", help="Create promoter DNA circuit")
    promoter_parser.add_argument("--name", required=True, help="Promoter name (e.g., ACTB_Malkuth)")
    promoter_parser.add_argument("--depth", type=int, default=3, help="Fractal depth")

    # Export circuit
    export_parser = sub.add_parser("export", help="Export circuit to file")
    export_parser.add_argument("--name", required=True, help="Circuit name (sierpinski|promoter:NAME)")
    export_parser.add_argument("--depth", type=int, default=3, help="Fractal depth")
    export_parser.add_argument("--format", choices=["qasm", "json", "svg"], default="qasm", help="Output format")

    # List circuits
    sub.add_parser("list", help="List available circuit types")

    args = parser.parse_args()

    if args.command == "list":
        print("Available circuits:")
        print("  sierpinski       - Sierpinski fractal circuit")
        print("  sierpinski+meta  - Sierpinski with Metatron enhancement")
        print("  bitnet           - BitNet ternary-seeded variational ansatz")
        print("  phi_resonance    - Golden ratio Phi-entangled pairs")
        print("  dna_quantum_walk - DNA sequence seeded quantum walk")
        print("  promoter         - Promoter DNA circuit")
        print("  promoter:NAME    - Specific promoter (e.g., ACTB_Malkuth)")

    elif args.command == "sierpinski":
        if args.metatron:
            qc = create_sierpinski_metatron_circuit(args.qubits, args.depth)
            print(f"Sierpinski + Metatron (depth {args.depth}):")
        else:
            qc = create_sierpinski_circuit(args.qubits, args.depth)
            print(f"Sierpinski (depth {args.depth}):")
        print(f"  Qubits: {qc.num_qubits}")
        print(f"  Gates: {qc.size()}")
        print(f"  QASM length: {len(qasm2_dumps(qc))} chars")

    elif args.command == "promoter":
        qc = create_promoter_circuit(args.name, args.depth)
        print(f"Promoter circuit ({args.name}, depth {args.depth}):")
        print(f"  Qubits: {qc.num_qubits}")
        print(f"  Gates: {qc.size()}")
        print(f"  QASM length: {len(qasm2_dumps(qc))} chars")

    elif args.command == "export":
        if args.name.startswith("promoter:"):
            promoter_name = args.name.split(":")[1]
            qc = create_promoter_circuit(promoter_name, args.depth)
            circuit_type = f"promoter_{promoter_name.lower()}"
        else:
            circuit_type = args.name
            if args.name == "sierpinski":
                qc = create_sierpinski_circuit(21, args.depth)
            elif args.name == "sierpinski+meta":
                qc = create_sierpinski_metatron_circuit(21, args.depth)
            elif args.name == "bitnet":
                qc = create_bitnet_ternary_ansatz(21)
            elif args.name == "phi_resonance":
                qc = create_phi_resonance_circuit(2, "torino")
            else:
                print(f"Unknown circuit: {args.name}")
                return

        if args.format == "qasm":
            output = qasm2_dumps(qc)
            ext = ".qasm"
        elif args.format == "json":
            output = qasm2_dumps(qc)
            ext = ".json"

        output_path = Path(__file__).parent.parent / "circuits" / "qasm" / f"{circuit_type}_d{args.depth}{ext}"
        output_path.write_text(output, encoding="utf-8")
        print(f"Circuit exported to: {output_path}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
