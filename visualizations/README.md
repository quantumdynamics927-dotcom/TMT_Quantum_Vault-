# TMT Quantum Vault Visualizations

Interactive visualizations for quantum consciousness research.

## Phi-Resonance Quantum State (`phi_resonance.html`)

WebGL visualization using Three.js that demonstrates the relationship between phase alignment and the Golden Ratio (φ ≈ 1.618).

**Features:**
- Icosahedron geometry (Platonic solid whose vertices are defined by φ)
- Real-time vertex jitter based on deviation from φ
- Entanglement fidelity metric (100% at φ, decreasing with deviation)
- Smooth harmonic pulsing when aligned with Golden Ratio

**Usage:**
1. Open `phi_resonance.html` in a browser
2. Adjust the Phase Alignment slider (0 to π)
3. Observe structural coherence peak at φ ≈ 1.618
4. Fidelity reaches 100% when phase aligns with Golden Ratio

**Mathematical Foundation:**
- Icosahedron vertices: (±1, ±φ, 0), (0, ±1, ±φ), (±φ, 0, ±1)
- Entanglement fidelity: `100 - |phase - φ| / max_deviation * 150`
- Vertex jitter: proportional to deviation from φ

---

## Sierpinski Quantum Circuit (`sierpinski_circuit.html`)

HTML5 Canvas visualization of scale-invariant quantum circuit topology.

**Features:**
- Recursive Sierpinski triangle fractal
- Adjustable recursion depth (0-6)
- Active sub-circuit count: 3^depth
- Pulsing animation showing quantum state coherence

**Usage:**
1. Open `sierpinski_circuit.html` in a browser
2. Adjust the Recursion Depth slider
3. Observe how macro-circuits recursively subdivide into localized quantum sub-circuits

**Mathematical Foundation:**
- Sierpinski triangle: Self-similar fractal with Hausdorff dimension log(3)/log(2) ≈ 1.585
- Scale-invariance: Each sub-triangle mirrors the whole
- Qubit mapping: Depth 1 → 3 qubits, Depth 2 → 9 qubits, Depth 3 → 27 qubits
- φ-connection: Pascal's triangle row sums follow Fibonacci sequence

---

## Integration with TMT Quantum Vault

These visualizations demonstrate the core principles implemented in `sierpinski_topology.py`:

| Visualization | Code Module | Concept |
|---------------|-------------|---------|
| Phi-Resonance | `orchestrator.py` | φ-gating threshold (≥0.618) for hardware routing |
| Sierpinski Circuit | `sierpinski_topology.py` | Scale-invariant entanglement structure |

**Running Ablation Studies:**

```python
from tmt_quantum_vault.orchestration import (
    SierpinskiGenerator,
    SierpinskiConfig,
    SIERPINSKI_ABLATIONS,
    AblationStudyRunner,
)

# Generate depth-3 Sierpinski circuit (27 qubits)
config = SierpinskiConfig(depth=3, metatron_overlay=True)
generator = SierpinskiGenerator(config)
spec = generator.generate()

# Run ablation to measure φ-contribution
runner = AblationStudyRunner(vault_path=Path("."))
study = runner.run_study()
```

---

## Browser Compatibility

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

No build step required - open HTML files directly in browser.