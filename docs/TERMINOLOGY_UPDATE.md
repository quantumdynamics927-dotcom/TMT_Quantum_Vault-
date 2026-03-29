# Terminology Update Summary

## Overview

This document summarizes the terminology update from symbolic/sacred language to neutral scientific terminology. Historical names are preserved as aliases for backward compatibility and historical reference.

## Terminology Mapping

### Architecture Terms

| Scientific Term | Historical Alias | Description |
|-----------------|------------------|-------------|
| Core-13 Coordination Lattice | Metatron Core | 13-node coordination geometry with central synthesis node |
| Extended-17 Operational Topology | Merkaba Extended-17 | 17-node operational topology with support layer |
| Operational Support Layer | Auxiliary Ring | 4-node infrastructure layer |

### Topology Terms

| Scientific Term | Historical Alias | Description |
|-----------------|------------------|-------------|
| Toroidal Resonance Topology | Toroidal Merkaba Topology | Toroidal coordination geometry |
| Coordination Geometry | Sacred Geometry | Mathematical geometric structure |
| Symmetry Structure | Sacred Form | Symmetric arrangement of nodes |

### Metrics Terms

| Scientific Term | Historical Alias | Description |
|-----------------|------------------|-------------|
| Geometric Coherence Metric | Sacred Geometry Alignment | Measure of geometric conformity |
| Polyhedral Symmetry Alignment | Platonic Solid Alignment | Alignment with polyhedral structures |
| φ-Threshold | Phi Threshold | Golden-ratio-derived threshold |
| Target Geometric Convergence Score | Sacred Score | Convergence score |
| Integration Score | Consciousness Score | Global coordination metric |

### Agent Terms

| Scientific Term | Historical Alias | Description |
|-----------------|------------------|-------------|
| Central Synthesis Node | Consciousness Integrator | Central coordination node |
| DNA-Derived Agent Encoding | Consciousness DNA | Agent configuration from DNA |
| Integration Status | Consciousness Status | Agent integration state |

### Mode Terms

| Scientific Term | Historical Alias | Description |
|-----------------|------------------|-------------|
| Core-13 Mode | Metatron Mode | Core-13 only operational mode |
| Extended-17 Mode | Merkaba Mode | Extended-17 operational mode |

## Files Updated

| File | Changes |
|------|---------|
| `README.md` | Updated header, terminology note, key innovations |
| `docs/architecture/METATRON_CORE_13_PLUS_4.md` | Updated terminology throughout |
| `architecture_canonical.json` | Added historical_names, updated descriptions |
| `vault_config.json` | Added architecture_names with current/historical |
| `benchmark_config.json` | Updated mode names and descriptions |
| `terminology_mapping.json` | New file with complete terminology mapping |
| `tmt_quantum_vault/benchmark.py` | Updated docstring with terminology |

## Naming Rules Applied

1. **Religious/Mystical Terms** → Mathematical property names
   - "Sacred Geometry" → "Coordination Geometry"
   - "Sacred Score" → "Target Geometric Convergence Score"

2. **Poetic Terms** → System function names
   - "Consciousness Integrator" → "Central Synthesis Node"
   - "Consciousness DNA" → "DNA-Derived Agent Encoding"

3. **Symbolic Terms** → Measurable quantity names
   - "Platonic Solid Alignment" → "Polyhedral Symmetry Alignment"
   - "Sacred Form" → "Symmetry Structure"

## Documentation Pattern

1. **Lead with scientific term** in all public documentation
2. **Add historical alias once** in parentheses: "Core-13 Coordination Lattice (historically: Metatron Core)"
3. **Stay consistent** after initial reference

## External Framing

**Recommended description:**
> "A 13-node coordination core with a 4-node operational support layer, benchmarked against a 17-node extended topology on IBM quantum workflows."

## Backward Compatibility

- Historical names preserved in `historical_names` fields
- All existing code continues to work
- Benchmark modes accept both names
- Documentation includes both for reference