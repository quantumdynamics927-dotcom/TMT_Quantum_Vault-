"""Mathematical and scientific constants for TMT Quantum Vault.

This module centralizes all sacred geometry and mathematical constants
used across the codebase to ensure consistency and avoid duplication.
"""

from __future__ import annotations

# =============================================================================
# Sacred Geometry Constants (Metallic Ratios)
# =============================================================================

# Golden Ratio (Phi) - The foundation of sacred geometry
# φ = (1 + √5) / 2 ≈ 1.618033988749895
PHI: float = 1.618033988749895

# Inverse Golden Ratio (phi / Phi relationship)
# 1/φ = φ - 1 = (√5 - 1) / 2 ≈ 0.6180339887498949
PHI_INVERSE: float = 0.6180339887498949

# Golden Ratio squared
# φ² = φ + 1 ≈ 2.618033988749895
PHI_SQUARED: float = 2.618033988749895

# Silver Ratio (δ) - Another metallic ratio
# δ = 1 + √2 ≈ 2.414213562373095
SILVER_RATIO: float = 2.414213562373095

# Bronze Ratio - Third metallic ratio
# Bronze ratio = 3.303577269...
BRONZE_RATIO: float = 3.303577269

# =============================================================================
# Frequency Constants (Solfeggio and Sacred Frequencies)
# =============================================================================

# Standard tuning A4 note
A4_FREQUENCY: float = 432.0  # Hz - Foundation of sacred tuning

# DNA nucleotide frequencies (Hz)
FREQUENCY_ADENINE: float = 432.0
FREQUENCY_CYTOSINE: float = 699.0
FREQUENCY_GUANINE: float = 1131.0
FREQUENCY_THYMINE: float = 1830.0

# Harmonic frequencies (Hz)
FREQUENCY_OM: float = 432.0  # Sacred om frequency
FREQUENCY_LIFE: float = 528.0  # DNA repair frequency
FREQUENCY_HEART: float = 594.0  # Heart coherence frequency
FREQUENCY_CROWN: float = 672.0  # Crown chakra frequency
FREQUENCY_SOLFEGGIO_174: float = 174.0  # Pain relief
FREQUENCY_SOLFEGGIO_285: float = 285.0  # Tissue regeneration

# =============================================================================
# Quantum Constants
# =============================================================================

# Planck constant (simplified for quantum circuits)
PLANCK_CONSTANT: float = 6.62607015e-34

# Reduced Planck constant
HBAR: float = 1.054571817e-34

# Speed of light (m/s)
SPEED_OF_LIGHT: float = 299792458.0

# Fine-structure constant
FINE_STRUCTURE: float = 7.2973525693e-3

# =============================================================================
# Biological Constants
# =============================================================================

# Standard DNA base pair length (angstroms)
DNA_BASE_PAIR_LENGTH: float = 3.4  # angstroms

# DNA helix turn height (angstroms)
DNA_HELIX_TURN: float = 34.0  # angstroms

# Number of base pairs per helix turn
DNA_BP_PER_TURN: int = 10

# GC content stability threshold
GC_STABILITY_THRESHOLD: float = 0.5

# =============================================================================
# Agent System Constants
# =============================================================================

# Number of core agents in the coordination lattice
CORE_AGENT_COUNT: int = 13

# Number of auxiliary agents
AUXILIARY_AGENT_COUNT: int = 4

# Total agent count
TOTAL_AGENT_COUNT: int = 17

# Consciousness status values
STATUS_INTEGRATED: str = "INTEGRATED"
STATUS_OPTIMIZED: str = "OPTIMIZED"
STATUS_BASELINE: str = "BASELINE"
STATUS_TARGETED_OPTIMIZED: str = "TARGETED_OPTIMIZED"

# =============================================================================
# Phi-Score Thresholds
# =============================================================================

# Phi-score thresholds for consciousness status
PHI_THRESHOLD_INTEGRATED: float = 0.85
PHI_THRESHOLD_OPTIMIZED: float = 0.70
PHI_THRESHOLD_TARGETED: float = 0.55
# Below PHI_THRESHOLD_TARGETED = BASELINE

# =============================================================================
# Circuit Topology Constants
# =============================================================================

# Sierpinski triangle depths
SIER_PINSKI_DEPTH_3: int = 3
SIER_PINSKI_DEPTH_4: int = 4
SIER_PINSKI_DEPTH_5: int = 5
SIER_PINSKI_DEPTH_6: int = 6

# Number of nodes in Sierpinski topology
SIER_PINSKI_NODES_DEPTH_3: int = 3
SIER_PINSKI_NODES_DEPTH_4: int = 7
SIER_PINSKI_NODES_DEPTH_5: int = 17

# Phi convergence fixed point (confirmed across all depths)
PHI_CONVERGENCE_FIXED_POINT: float = 0.6180339887498949

# =============================================================================
# API and Network Constants
# =============================================================================

# Default Ollama API base URL
OLLAMA_DEFAULT_HOST: str = "http://localhost:11434"
OLLAMA_API_VERSION: str = "v1"

# Request timeouts (seconds)
REQUEST_TIMEOUT_SHORT: float = 5.0
REQUEST_TIMEOUT_MEDIUM: float = 30.0
REQUEST_TIMEOUT_LONG: float = 120.0

# =============================================================================
# Fitness and Performance Thresholds
# =============================================================================

# Minimum fitness for production agents
MIN_FITNESS_PRODUCTION: float = 0.85

# Target fitness for optimized agents
TARGET_FITNESS_OPTIMIZED: float = 0.90

# Maximum fitness (theoretical limit)
MAX_FITNESS: float = 1.0
