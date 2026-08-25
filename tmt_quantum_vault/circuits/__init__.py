"""
Quantum Circuit Modules for TMT Quantum Vault.

This package provides specialized quantum circuits for the TMT ecosystem:

- merkaba_fingerprint: 6-qubit Merkaba (star tetrahedron) fingerprint generator
- sierpinski_topology: Recursive fractal quantum circuits

Usage:
    from tmt_quantum_vault.circuits.merkaba_fingerprint import (
        create_merkaba_fingerprint_circuit,
        extract_fingerprint,
        MerkabaFingerprintGenerator,
    )

    from tmt_quantum_vault.circuits.sierpinski_topology import (
        SierpinskiGenerator,
        SierpinskiCircuitSpec,
    )
"""

from tmt_quantum_vault.circuits.merkaba_fingerprint import (
    MERKABA_QUBITS,
    MERKABA_STATES,
    PHI,
    MerkabaFingerprint,
    MerkabaFingerprintGenerator,
    create_merkaba_circuit_openqasm,
    create_merkaba_fingerprint_circuit,
    extract_fingerprint,
    generate_fingerprint_cli,
)

__all__ = [
    # Constants
    "PHI",
    "MERKABA_QUBITS",
    "MERKABA_STATES",
    # Merkaba fingerprint
    "MerkabaFingerprint",
    "MerkabaFingerprintGenerator",
    "create_merkaba_fingerprint_circuit",
    "create_merkaba_circuit_openqasm",
    "extract_fingerprint",
    "generate_fingerprint_cli",
]
