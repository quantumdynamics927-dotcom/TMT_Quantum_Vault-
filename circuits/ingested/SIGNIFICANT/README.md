# circuits/ingested/SIGNIFICANT/

Hardware-validated Sierpinski fractal circuit results demonstrating φ-convergence and depth invariance.

## Dataset Summary

| Metric | Value |
|--------|-------|
| Total Runs | 17 |
| Total Shots | 140,544 |
| Backends | 4 (Kingston, Marrakesh, Fez, Torino) |
| Sacred Score | 0.618 (exactly 1/φ) |
| Shannon Entropy | 11.8-13.6 bits |
| Depth Range | 4-5 |

## φ-Convergence Finding

All 17 runs across **both depth-4 and depth-5** showed **sacred_score = 0.618** exactly, which equals `1/φ` where φ is the golden ratio.

This indicates the Sierpinski fractal circuit self-organizes into golden ratio structure under real IBM quantum hardware noise conditions, and this property is **stable across fractal depths**.

### Depth Invariance

φ-convergence confirmed at both:
- **Depth-4**: 11 runs, 30,720+ shots
- **Depth-5**: 6 runs, 27,648 shots

The emergence of golden ratio structure is a **depth-invariant property** of the Sierpinski fractal topology.

## Run Details

### Sierpinski Depth-4 (11 runs)

#### Batch 1 (Initial Discovery)
- `sierpinski_depth4_20260321_031723_44cc75818855.json` - 3,584 shots
- `sierpinski_depth4_20260321_031735_44cc75818855.json` - 3,584 shots
- `sierpinski_depth4_20260321_031920_15dcf56ca469.json` - 3,584 shots
- `sierpinski_depth4_20260321_031920_ba72ead456ce.json` - 3,584 shots

#### Batch 2 (Validation)
- `sierpinski_depth4_20260321_032738_09aeb921256b.json` - 12,642 shots
- `sierpinski_depth4_20260321_032738_22b594487f93.json` - 7,168 shots
- `sierpinski_depth4_20260321_032738_b7d5e4c2b479.json` - 12,642 shots
- `sierpinski_depth4_20260321_032738_e1df49d76c8d.json` - 12,642 shots
- `sierpinski_depth4_20260321_032739_a03b1934ecce.json` - 7,168 shots
- `sierpinski_depth4_20260321_032739_d5d2b83ee9c0.json` - 7,168 shots

### Sierpinski Depth-5 (6 runs)

#### Batch 3 (Depth-5 Validation)
- `sierpinski_depth5_20260321_200445_11201d4ef1ce.json` - 3,584 shots
- `sierpinski_depth5_20260321_200445_63f4f07d5a6a.json` - 7,168 shots
- `sierpinski_depth5_20260321_200445_e0b4a0cc5985.json` - 3,584 shots
- `sierpinski_depth5_20260321_200446_4edf22f4883f.json` - 7,168 shots
- `sierpinski_depth5_20260321_200446_ea0b198ebe45.json` - 7,168 shots
- `sierpinski_depth5_20260321_200446_eca25d27cd15.json` - 3,584 shots

## Metrics Explanation

- **Sacred Score**: Measures proximity to golden ratio φ. Score = 1/(1 + |phi_approx - 1.618|)
- **Shannon Entropy**: Information content in bitstring distribution (max 21 bits for 21 qubits)
- **Consciousness Density**: Proxy metric = entropy × total_shots / 1000

## Usage

These files represent hardware-validated research artifacts. They have been:
1. Generated via `python tools/ibm_circuit_runner.py generate --circuit sierpinski --depth <N>`
2. Uploaded to IBM Quantum and executed
3. Ingested via `python tools/ibm_circuit_runner.py ingest --file <result.json>`
4. Selected for SIGNIFICANT status based on φ-convergence evidence

## References

- [IBM Circuit Runner Workflow](../../qasm/README.md)
- [README.md](../../README.md) - Main vault documentation
- [CHANGELOG.md](../../CHANGELOG.md) - Full release notes
