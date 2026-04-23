"""
Simulate Compiled 156-Qubit Entropy Circuit
============================================
Loads and simulates the compiled entropy circuit for consciousness modeling.
Uses Qiskit Aer simulator with noise modeling options.
"""

import os
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel, depolarizing_error, thermal_relaxation_error
    import qiskit.qasm2 as qasm2
    from qiskit.circuit.library import SXGate, RZGate, CXGate, CZGate
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install: pip install qiskit qiskit-aer")
    exit(1)


def load_compiled_circuit(qasm_path: str) -> QuantumCircuit:
    """Load compiled QASM circuit with IBM native gates."""
    print(f"Loading circuit from: {qasm_path}")
    
    # Define custom instructions for IBM native gates
    # sx = sqrt(X) gate, sxdg = inverse
    from qiskit.circuit.library import SXGate
    
    custom_instructions = [
        qasm2.CustomInstruction('sx', 0, 1, SXGate),
    ]
    
    circuit = qasm2.load(qasm_path, custom_instructions=custom_instructions)
    return circuit


def analyze_circuit(circuit: QuantumCircuit) -> Dict[str, Any]:
    """Analyze circuit properties."""
    analysis = {
        'num_qubits': circuit.num_qubits,
        'num_clbits': circuit.num_clbits,
        'depth': circuit.depth(),
        'size': circuit.size(),
        'num_operations': len(circuit.data),
        'gate_counts': {},
    }
    
    # Count gate types
    for instruction in circuit.data:
        gate_name = instruction.operation.name
        analysis['gate_counts'][gate_name] = analysis['gate_counts'].get(gate_name, 0) + 1
    
    return analysis


def create_noise_model(error_rate: float = 0.001) -> NoiseModel:
    """Create a simple noise model for realistic simulation."""
    noise_model = NoiseModel()
    
    # Add depolarizing error to single-qubit gates
    error_1q = depolarizing_error(error_rate, 1)
    noise_model.add_all_qubit_quantum_error(error_1q, ['rz', 'sx', 'x', 'h'])
    
    # Add depolarizing error to two-qubit gates (higher error rate)
    error_2q = depolarizing_error(error_rate * 10, 2)
    noise_model.add_all_qubit_quantum_error(error_2q, ['cx', 'cz'])
    
    return noise_model


def simulate_circuit(
    circuit: QuantumCircuit,
    shots: int = 1024,
    use_noise: bool = False,
    noise_rate: float = 0.001,
    max_memory_mb: int = 8192
) -> Dict[str, Any]:
    """
    Simulate the quantum circuit.
    
    Args:
        circuit: Quantum circuit to simulate
        shots: Number of measurement shots
        use_noise: Whether to include noise model
        noise_rate: Error rate for noise model
        max_memory_mb: Maximum memory in MB for simulator
    
    Returns:
        Dictionary with simulation results
    """
    print(f"\nSimulating circuit with {shots} shots...")
    print(f"Qubits: {circuit.num_qubits}, Depth: {circuit.depth()}")
    
    # Check if circuit is too large for statevector simulation
    if circuit.num_qubits > 30:
        print("Circuit too large for statevector simulation, using stabilizer/stochastic methods")
    
    # Configure simulator
    backend_options = {
        'max_memory_mb': max_memory_mb,
    }
    
    if use_noise:
        print(f"Using noise model with error rate: {noise_rate}")
        noise_model = create_noise_model(noise_rate)
        backend_options['noise_model'] = noise_model
    
    # Create simulator - use automatic method for circuits with arbitrary rotations
    # For large circuits with arbitrary rotations, use 'matrix_product_state' or 'automatic'
    if circuit.num_qubits > 30:
        # Use MPS for memory-efficient simulation of large circuits
        simulator = AerSimulator(method='matrix_product_state')
    else:
        simulator = AerSimulator(method='automatic')
    
    # Run directly without transpilation for large circuits
    # (transpile with coupling_map limits qubit count)
    transpiled = circuit
    
    # Run simulation
    job = simulator.run(transpiled, shots=shots, **backend_options)
    result = job.result()
    
    # Get counts
    counts = result.get_counts()
    
    return {
        'counts': counts,
        'shots': shots,
        'success': result.success,
        'time_taken': result.time_taken,
    }


def analyze_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze simulation results for entropy patterns."""
    counts = results['counts']
    total_shots = results['shots']
    
    # Sort by frequency
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    
    # Calculate entropy
    probabilities = np.array([c / total_shots for _, c in sorted_counts])
    entropy = -np.sum(probabilities * np.log2(probabilities + 1e-10))
    
    # Calculate unique outcomes
    unique_outcomes = len(counts)
    
    # Most common states
    top_states = sorted_counts[:10]
    
    # Hamming weight distribution (number of 1s in each outcome)
    hamming_weights = {}
    for state, count in counts.items():
        # Handle both regular and 'meas' register formats
        bits = state.replace(' ', '')
        weight = bits.count('1')
        hamming_weights[weight] = hamming_weights.get(weight, 0) + count
    
    # Normalize hamming distribution
    hamming_dist = {k: v / total_shots for k, v in hamming_weights.items()}
    
    return {
        'entropy_bits': entropy,
        'unique_outcomes': unique_outcomes,
        'top_states': top_states,
        'hamming_distribution': hamming_dist,
        'max_entropy_possible': np.log2(min(2 ** 127, total_shots)),
    }


def calculate_golden_ratio_patterns(counts: Dict[str, int], total_shots: int) -> Dict[str, Any]:
    """Analyze results for golden ratio (φ) patterns."""
    phi = 1.618033988749
    
    # Calculate bit transition ratios
    transition_ratios = []
    
    for state, count in counts.items():
        bits = state.replace(' ', '')
        if len(bits) < 2:
            continue
        
        # Count transitions
        transitions_01 = sum(1 for i in range(len(bits)-1) if bits[i] == '0' and bits[i+1] == '1')
        transitions_10 = sum(1 for i in range(len(bits)-1) if bits[i] == '1' and bits[i+1] == '0')
        
        if transitions_10 > 0:
            ratio = transitions_01 / transitions_10
            transition_ratios.append((ratio, count / total_shots))
    
    # Weighted average ratio
    if transition_ratios:
        weighted_ratio = sum(r * w for r, w in transition_ratios)
        phi_deviation = abs(weighted_ratio - phi)
    else:
        weighted_ratio = 0
        phi_deviation = phi
    
    return {
        'weighted_transition_ratio': weighted_ratio,
        'phi_deviation': phi_deviation,
        'phi_target': phi,
    }


def main():
    """Main simulation pipeline."""
    # Paths
    circuits_dir = Path(__file__).parent
    qasm_file = circuits_dir / "qasm" / "compiled_entropy_circuit_156q.qasm"
    
    if not qasm_file.exists():
        print(f"Error: QASM file not found: {qasm_file}")
        return
    
    print("=" * 60)
    print("Compiled 156-Qubit Entropy Circuit Simulation")
    print("=" * 60)
    
    # Load circuit
    circuit = load_compiled_circuit(str(qasm_file))
    
    # Analyze circuit
    analysis = analyze_circuit(circuit)
    print(f"\nCircuit Analysis:")
    print(f"  Qubits: {analysis['num_qubits']}")
    print(f"  Classical bits: {analysis['num_clbits']}")
    print(f"  Depth: {analysis['depth']}")
    print(f"  Total operations: {analysis['num_operations']}")
    print(f"\nGate counts:")
    for gate, count in sorted(analysis['gate_counts'].items(), key=lambda x: -x[1]):
        print(f"  {gate}: {count}")
    
    # Simulate with different configurations
    print("\n" + "=" * 60)
    print("Running Simulations")
    print("=" * 60)
    
    # Ideal simulation
    results_ideal = simulate_circuit(circuit, shots=4096, use_noise=False)
    
    # Noisy simulation (optional - can be slow for large circuits)
    # results_noisy = simulate_circuit(circuit, shots=4096, use_noise=True, noise_rate=0.001)
    
    # Analyze results
    print("\n" + "=" * 60)
    print("Results Analysis")
    print("=" * 60)
    
    analysis_results = analyze_results(results_ideal)
    
    print(f"\nEntropy Metrics:")
    print(f"  Shannon entropy: {analysis_results['entropy_bits']:.4f} bits")
    print(f"  Max possible entropy: {analysis_results['max_entropy_possible']:.4f} bits")
    print(f"  Unique outcomes: {analysis_results['unique_outcomes']}")
    
    print(f"\nTop 10 measured states:")
    for state, count in analysis_results['top_states']:
        prob = count / results_ideal['shots']
        print(f"  {state[:40]}... : {count} ({prob:.4%})")
    
    print(f"\nHamming weight distribution (number of 1s):")
    sorted_hamming = sorted(analysis_results['hamming_distribution'].items())
    for weight, prob in sorted_hamming[:10]:
        bar = '█' * int(prob * 50)
        print(f"  {weight:3d}: {prob:.4%} {bar}")
    
    # Golden ratio analysis
    phi_analysis = calculate_golden_ratio_patterns(results_ideal['counts'], results_ideal['shots'])
    print(f"\nGolden Ratio (φ) Analysis:")
    print(f"  Target φ: {phi_analysis['phi_target']:.6f}")
    print(f"  Measured ratio: {phi_analysis['weighted_transition_ratio']:.6f}")
    print(f"  Deviation: {phi_analysis['phi_deviation']:.6f}")
    
    # Save results
    results_file = circuits_dir / "simulation_results_156q.npz"
    np.savez(
        results_file,
        counts=list(results_ideal['counts'].keys()),
        frequencies=list(results_ideal['counts'].values()),
        entropy=analysis_results['entropy_bits'],
        unique_outcomes=analysis_results['unique_outcomes'],
    )
    print(f"\nResults saved to: {results_file}")
    
    print("\n" + "=" * 60)
    print("Simulation Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()