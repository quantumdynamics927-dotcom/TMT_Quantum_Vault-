#!/usr/bin/env python3
"""
Tests for tmt_quantum_vault.circuits.merkaba_fingerprint — the Merkaba
6-qubit star-tetrahedron quantum fingerprint circuit.
"""
from __future__ import annotations

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# Data classes
# ══════════════════════════════════════════════════════════════════════════════


def test_merkaba_fingerprint_to_dict() -> None:
    """MerkabaFingerprint.to_dict round-trips through from_dict."""
    from tmt_quantum_vault.circuits.merkaba_fingerprint import MerkabaFingerprint

    fp = MerkabaFingerprint(
        fingerprint_hash="abc123",
        phi_score=0.618,
        dominant_state="000000",
        entropy_bits=6.0,
    )
    d = fp.to_dict()
    assert d["fingerprint_hash"] == "abc123"
    assert d["phi_score"] == 0.618
    assert d["dominant_state"] == "000000"
    assert d["entropy_bits"] == 6.0
    assert d["seed_source"] == "unknown"
    assert d["backend"] == "unknown"
    assert d["shots"] == 1024


def test_merkaba_fingerprint_from_dict() -> None:
    """MerkabaFingerprint.from_dict recreates the fingerprint."""
    from tmt_quantum_vault.circuits.merkaba_fingerprint import MerkabaFingerprint

    raw = {
        "fingerprint_hash": "def456",
        "phi_score": 0.71,
        "dominant_state": "111111",
        "entropy_bits": 5.5,
        "seed_source": "test",
        "backend": "simulator",
        "shots": 2048,
    }
    fp = MerkabaFingerprint.from_dict(raw)
    assert fp.fingerprint_hash == "def456"
    assert fp.phi_score == 0.71
    assert fp.dominant_state == "111111"
    assert fp.seed_source == "test"
    assert fp.backend == "simulator"
    assert fp.shots == 2048


# ══════════════════════════════════════════════════════════════════════════════
# OpenQASM generation (no qiskit required)
# ══════════════════════════════════════════════════════════════════════════════


def test_openqasm_seed_short_pads_to_6() -> None:
    """Seed shorter than 6 bytes is padded with zeros."""
    from tmt_quantum_vault.circuits.merkaba_fingerprint import (
        create_merkaba_circuit_openqasm,
    )

    qasm = create_merkaba_circuit_openqasm(b"x")
    assert "rz(" in qasm
    assert "OPENQASM 2.0" in qasm
    assert "qreg q[6]" in qasm
    assert "creg c[6]" in qasm


def test_openqasm_seed_exact_6_uses_all_bytes() -> None:
    """Seed of exactly 6 bytes is consumed: 3 upward + 3 downward rz rotations."""
    from tmt_quantum_vault.circuits.merkaba_fingerprint import (
        create_merkaba_circuit_openqasm,
    )

    qasm = create_merkaba_circuit_openqasm(b"abcdef")
    # 3 upward + 3 downward = 6 seed-driven rz calls
    # (Layer 4 phi-interference adds 6 more, total 12)
    assert qasm.count("rz(") == 12


def test_openqasm_contains_both_triangle_labels() -> None:
    """QASM output labels both upward and downward tetrahedron layers."""
    from tmt_quantum_vault.circuits.merkaba_fingerprint import (
        create_merkaba_circuit_openqasm,
    )

    qasm = create_merkaba_circuit_openqasm(b"seed16")
    assert "upward" in qasm.lower() or "Layer 1" in qasm
    assert "downward" in qasm.lower() or "Layer 2" in qasm


def test_openqasm_merkaba_entanglement_present() -> None:
    """QASM includes the Merkaba inter-tetrahedron CX gates."""
    from tmt_quantum_vault.circuits.merkaba_fingerprint import (
        create_merkaba_circuit_openqasm,
    )

    qasm = create_merkaba_circuit_openqasm(b"merkaba")
    # Should have cx gates between upward and downward tetrahedra
    assert "cx" in qasm.lower()


# ══════════════════════════════════════════════════════════════════════════════
# Quantum circuit (requires qiskit)
# ══════════════════════════════════════════════════════════════════════════════


def test_merkaba_circuit_requires_minimum_6_qubits() -> None:
    """The Merkaba circuit has exactly 6 qubits and 6 classical bits."""
    pytest.importorskip("qiskit")
    from tmt_quantum_vault.circuits.merkaba_fingerprint import (
        create_merkaba_fingerprint_circuit,
    )

    qc = create_merkaba_fingerprint_circuit(b"test_seed_bytes")
    assert qc.num_qubits() == 6
    assert qc.num_clbits() == 6


def test_merkaba_circuit_seed_short_is_padded() -> None:
    """Seed shorter than 6 bytes does not raise — it is padded."""
    pytest.importorskip("qiskit")
    from tmt_quantum_vault.circuits.merkaba_fingerprint import (
        create_merkaba_fingerprint_circuit,
    )

    # Should not raise
    qc = create_merkaba_fingerprint_circuit(b"x")
    assert qc.num_qubits() == 6


# ══════════════════════════════════════════════════════════════════════════════
# Fingerprint extraction
# ══════════════════════════════════════════════════════════════════════════════


def test_extract_fingerprint_balanced_counts() -> None:
    """extract_fingerprint returns a valid fingerprint from a balanced distribution."""
    pytest.importorskip("qiskit")
    from tmt_quantum_vault.circuits.merkaba_fingerprint import (
        MerkabaFingerprint,
        extract_fingerprint,
    )

    # Uniform distribution over 64 basis states
    counts = {format(i, "06b"): 16 for i in range(64)}
    fp = extract_fingerprint(counts, shots=1024)
    assert isinstance(fp, MerkabaFingerprint)
    assert len(fp.fingerprint_hash) == 64  # hex SHA3-256 = 64 chars
    assert 0.0 <= fp.phi_score <= 1.0
    assert fp.dominant_state in [format(i, "06b") for i in range(64)]


def test_extract_fingerprint_single_state() -> None:
    """All shots in one state produces a clear dominant_state."""
    pytest.importorskip("qiskit")
    from tmt_quantum_vault.circuits.merkaba_fingerprint import (
        extract_fingerprint,
    )

    counts = {"000000": 1024}
    fp = extract_fingerprint(counts, shots=1024)
    assert fp.dominant_state == "000000"
    assert fp.entropy_bits == 0.0


def test_extract_fingerprint_phi_threshold() -> None:
    """phi_score is computed from golden-ratio proximity of state probabilities."""
    pytest.importorskip("qiskit")
    from tmt_quantum_vault.circuits.merkaba_fingerprint import (
        extract_fingerprint,
    )

    # A phi-resonant distribution (not uniform)
    counts = {"000000": 512, "111111": 512}
    fp = extract_fingerprint(counts, shots=1024)
    assert isinstance(fp.phi_score, float)
    assert 0.0 <= fp.phi_score <= 1.0
