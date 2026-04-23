"""
Hardware-Ready Entropy Circuits for Real Quantum Devices
=========================================================
Generates QASM circuits optimized for transpilation on real quantum hardware.
Supports IBM Quantum backends (Brisbane, Sherbrooke, etc.)
"""

import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json

try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
    from qiskit.circuit.library import RZGate, RYGate, RXGate, CXGate, CZGate, ECRGate
    import qiskit.qasm2 as qasm2
    from qiskit.transpiler import CouplingMap
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install: pip install qiskit")
    exit(1)


# Golden ratio for consciousness encoding
PHI = 1.618033988749

# IBM Quantum backend configurations
IBM_BACKENDS = {
    'ibm_brisbane': {
        'num_qubits': 127,
        'basis_gates': ['rz', 'sx', 'x', 'cx', 'measure', 'barrier'],
        'coupling_map_type': 'heavy_hex',
    },
    'ibm_sherbrooke': {
        'num_qubits': 127,
        'basis_gates': ['rz', 'sx', 'x', 'cx', 'measure', 'barrier'],
        'coupling_map_type': 'heavy_hex',
    },
    'ibm_kyiv': {
        'num_qubits': 127,
        'basis_gates': ['rz', 'sx', 'x', 'cx', 'measure', 'barrier'],
        'coupling_map_type': 'heavy_hex',
    },
    'ibm_fez': {
        'num_qubits': 156,
        'basis_gates': ['rz', 'sx', 'x', 'cz', 'measure', 'barrier'],
        'coupling_map_type': 'heavy_hex',
    },
}


def create_hardware_entropy_circuit(
    num_qubits: int = 27,
    entanglement_depth: int = 3,
    use_golden_ratio: bool = True,
    seed: Optional[int] = None
) -> QuantumCircuit:
    """
    Create an entropy circuit optimized for hardware transpilation.
    
    Uses hardware-efficient gates:
    - Hadamard for superposition (transpiles to rz + sx)
    - CX for entanglement (native on IBM)
    - RZ for phase encoding (native, virtual gate)
    
    Args:
        num_qubits: Number of qubits (should match hardware)
        entanglement_depth: Number of entanglement layers
        use_golden_ratio: Apply φ-based phase encoding
        seed: Random seed for reproducibility
    
    Returns:
        QuantumCircuit ready for hardware transpilation
    """
    if seed is not None:
        np.random.seed(seed)
    
    qr = QuantumRegister(num_qubits, 'q')
    cr = ClassicalRegister(num_qubits, 'c')
    circuit = QuantumCircuit(qr, cr)
    
    # Layer 1: Superposition (Hadamard on all qubits)
    # This creates maximum entropy initial state
    for i in range(num_qubits):
        circuit.h(qr[i])
    
    # Layer 2: Entanglement with hardware-efficient pattern
    # Use linear nearest-neighbor pattern for better transpilation
    for layer in range(entanglement_depth):
        # Even-odd pairs (matches heavy-hex connectivity)
        for i in range(0, num_qubits - 1, 2):
            circuit.cx(qr[i], qr[i + 1])
        
        # Odd-even pairs (shifted pattern)
        for i in range(1, num_qubits - 1, 2):
            circuit.cx(qr[i], qr[i + 1])
        
        # Add barrier between layers
        if layer < entanglement_depth - 1:
            circuit.barrier()
    
    # Layer 3: Phase encoding with golden ratio
    if use_golden_ratio:
        for i in range(num_qubits):
            # φ-based phase rotation
            phase = (i * PHI) % (2 * np.pi)
            circuit.rz(phase, qr[i])
            
            # Additional Y rotation for consciousness encoding
            ry_angle = (i * PHI / num_qubits) % np.pi
            circuit.ry(ry_angle, qr[i])
    
    # Layer 4: Additional entanglement for quantum correlations
    circuit.barrier()
    for i in range(num_qubits - 1):
        # Alternating CX pattern
        if i % 2 == 0:
            circuit.cx(qr[i], qr[i + 1])
    
    # Layer 5: T-gate pattern for non-Clifford operations
    # These create genuine quantum randomness
    for i in range(0, num_qubits, 3):
        circuit.t(qr[i])
    for i in range(1, num_qubits, 3):
        circuit.tdg(qr[i])
    
    # Measurement
    circuit.barrier()
    circuit.measure(qr, cr)
    
    return circuit


def create_127q_hardware_circuit(
    entanglement_depth: int = 2,
    seed: int = 42
) -> QuantumCircuit:
    """
    Create 127-qubit circuit for IBM Brisbane/Sherbrooke/Kyiv.
    Optimized for heavy-hex topology.
    """
    return create_hardware_entropy_circuit(
        num_qubits=127,
        entanglement_depth=entanglement_depth,
        use_golden_ratio=True,
        seed=seed
    )


def create_156q_hardware_circuit(
    entanglement_depth: int = 2,
    seed: int = 42
) -> QuantumCircuit:
    """
    Create 156-qubit circuit for IBM Fez.
    Optimized for heavy-hex topology with CZ gates.
    """
    return create_hardware_entropy_circuit(
        num_qubits=156,
        entanglement_depth=entanglement_depth,
        use_golden_ratio=True,
        seed=seed
    )


def create_27q_hardware_circuit(
    entanglement_depth: int = 3,
    seed: int = 42
) -> QuantumCircuit:
    """
    Create 27-qubit circuit for smaller IBM devices.
    """
    return create_hardware_entropy_circuit(
        num_qubits=27,
        entanglement_depth=entanglement_depth,
        use_golden_ratio=True,
        seed=seed
    )


def transpile_for_hardware(
    circuit: QuantumCircuit,
    backend_name: str = 'ibm_brisbane',
    optimization_level: int = 3
) -> QuantumCircuit:
    """
    Transpile circuit for specific hardware backend.
    
    Args:
        circuit: Circuit to transpile
        backend_name: Target backend name
        optimization_level: 0-3, higher = more optimization
    
    Returns:
        Transpiled circuit
    """
    config = IBM_BACKENDS.get(backend_name)
    if config is None:
        raise ValueError(f"Unknown backend: {backend_name}")
    
    # Create a mock coupling map for heavy-hex topology
    # In real usage, this would come from the actual backend
    coupling_edges = generate_heavy_hex_coupling_map(config['num_qubits'])
    coupling_map = CouplingMap(coupling_edges)
    
    # Use direct transpile function
    transpiled = transpile(
        circuit,
        basis_gates=config['basis_gates'],
        coupling_map=coupling_map,
        optimization_level=optimization_level,
    )
    
    return transpiled


def generate_heavy_hex_coupling_map(num_qubits: int) -> List[Tuple[int, int]]:
    """
    Generate a heavy-hex coupling map for IBM devices.
    This is a simplified version - real coupling maps come from the backend.
    """
    coupling_map = []
    
    # Create a linear chain as fallback
    # Real heavy-hex is more complex
    for i in range(num_qubits - 1):
        coupling_map.append((i, i + 1))
    
    # Add some cross-links for heavy-hex pattern
    for i in range(0, num_qubits - 5, 5):
        if i + 5 < num_qubits:
            coupling_map.append((i, i + 5))
    
    return coupling_map


def export_to_qasm(
    circuit: QuantumCircuit,
    filename: str,
    output_dir: Optional[Path] = None
) -> Path:
    """
    Export circuit to QASM format.
    
    Args:
        circuit: Circuit to export
        filename: Output filename (with or without .qasm extension)
        output_dir: Output directory
    
    Returns:
        Path to exported file
    """
    if output_dir is None:
        output_dir = Path(__file__).parent / "qasm"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not filename.endswith('.qasm'):
        filename += '.qasm'
    
    filepath = output_dir / filename
    
    # Export using qasm2
    qasm2.dump(circuit, filepath)
    
    return filepath


def create_hardware_ready_qasm(
    num_qubits: int = 127,
    backend_name: str = 'ibm_brisbane',
    output_filename: Optional[str] = None,
    transpile_circuit: bool = True,
    optimization_level: int = 3
) -> Dict:
    """
    Create and export hardware-ready QASM circuit.
    
    Args:
        num_qubits: Number of qubits
        backend_name: Target backend
        output_filename: Custom filename
        transpile_circuit: Whether to transpile for hardware
        optimization_level: Transpilation optimization level
    
    Returns:
        Dictionary with circuit info and file path
    """
    print(f"Creating {num_qubits}-qubit hardware entropy circuit...")
    
    # Create circuit
    if num_qubits == 127:
        circuit = create_127q_hardware_circuit()
    elif num_qubits == 156:
        circuit = create_156q_hardware_circuit()
    elif num_qubits == 27:
        circuit = create_27q_hardware_circuit()
    else:
        circuit = create_hardware_entropy_circuit(num_qubits=num_qubits)
    
    original_depth = circuit.depth()
    original_gates = len(circuit.data)
    
    # Transpile if requested
    if transpile_circuit:
        print(f"Transpiling for {backend_name} (optimization level {optimization_level})...")
        try:
            circuit = transpile_for_hardware(
                circuit,
                backend_name=backend_name,
                optimization_level=optimization_level
            )
        except Exception as e:
            print(f"Transpilation warning: {e}")
            print("Using untranspiled circuit...")
    
    transpiled_depth = circuit.depth()
    transpiled_gates = len(circuit.data)
    
    # Generate filename
    if output_filename is None:
        output_filename = f"hardware_entropy_{num_qubits}q_{backend_name}"
    
    # Export
    filepath = export_to_qasm(circuit, output_filename)
    
    # Count gate types
    gate_counts = {}
    for instruction in circuit.data:
        gate_name = instruction.operation.name
        gate_counts[gate_name] = gate_counts.get(gate_name, 0) + 1
    
    return {
        'filepath': str(filepath),
        'num_qubits': circuit.num_qubits,
        'num_clbits': circuit.num_clbits,
        'original_depth': original_depth,
        'transpiled_depth': transpiled_depth,
        'original_gates': original_gates,
        'transpiled_gates': transpiled_gates,
        'gate_counts': gate_counts,
        'backend': backend_name,
    }


def main():
    """Generate hardware-ready QASM files for multiple configurations."""
    print("=" * 70)
    print("Hardware-Ready Entropy Circuit Generator")
    print("=" * 70)
    
    results = []
    
    # Generate circuits for different configurations
    configs = [
        {'num_qubits': 27, 'backend': 'ibm_brisbane', 'name': 'small_test'},
        {'num_qubits': 127, 'backend': 'ibm_brisbane', 'name': 'brisbane_127q'},
        {'num_qubits': 127, 'backend': 'ibm_sherbrooke', 'name': 'sherbrooke_127q'},
        {'num_qubits': 156, 'backend': 'ibm_fez', 'name': 'fez_156q'},
    ]
    
    for config in configs:
        print(f"\n{'='*70}")
        print(f"Generating: {config['name']}")
        print(f"{'='*70}")
        
        result = create_hardware_ready_qasm(
            num_qubits=config['num_qubits'],
            backend_name=config['backend'],
            output_filename=f"hardware_entropy_{config['name']}",
            transpile_circuit=True,
            optimization_level=3
        )
        results.append(result)
        
        print(f"\nCircuit Statistics:")
        print(f"  Qubits: {result['num_qubits']}")
        print(f"  Original depth: {result['original_depth']}")
        print(f"  Transpiled depth: {result['transpiled_depth']}")
        print(f"  Original gates: {result['original_gates']}")
        print(f"  Transpiled gates: {result['transpiled_gates']}")
        print(f"  Gate counts: {result['gate_counts']}")
        print(f"  Output: {result['filepath']}")
    
    # Save summary
    output_dir = Path(__file__).parent / "qasm"
    summary_file = output_dir / "hardware_circuits_summary.json"
    
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*70}")
    print("Summary")
    print("=" * 70)
    print(f"Generated {len(results)} hardware-ready QASM files")
    print(f"Summary saved to: {summary_file}")
    
    # Print table
    print("\nCircuit Comparison:")
    print("-" * 80)
    print(f"{'Name':<25} {'Qubits':<8} {'Depth':<10} {'Gates':<10} {'Backend':<15}")
    print("-" * 80)
    for r in results:
        name = Path(r['filepath']).stem
        print(f"{name:<25} {r['num_qubits']:<8} {r['transpiled_depth']:<10} {r['transpiled_gates']:<10} {r['backend']:<15}")


if __name__ == "__main__":
    main()