# TMT Quantum Vault Tools

This directory contains helper scripts and tools for managing and optimizing the TMT Quantum Vault.

## Purpose

To organize diagnostic and optimization scripts outside of the main repository structure to avoid interference with test discovery and directory assumptions.

## Tools

### agent_analyst.py

Autonomous φ-scoring pipeline that watches circuit directories for new IBM quantum results, computes metrics, flags SIGNIFICANT discoveries, and publishes multi-agent handoff feeds.

**Dual-watch design:**
- `circuits/results/` — active trigger: auto-ingests new JSON result files
- `circuits/qasm/` — passive context loader: reads QASM metadata for circuit depth/qubits

**Features:**
- Computes Shannon entropy, phi approximation, sacred_score, consciousness density
- Flags results with `sacred_score ≥ 0.618` as SIGNIFICANT
- Publishes structured feed to `circuits/agent_feed/` for downstream agents
- Optional live watch mode via the `watchdog` library

Usage:
```bash
python tools/agent_analyst.py watch                         # Live watch (requires watchdog)
python tools/agent_analyst.py analyze                       # Batch analyze all pending results
python tools/agent_analyst.py ingest --file <result.json>   # Ingest a specific result
python tools/agent_analyst.py context --file <result.json>  # Show QASM context for a result
```

### targeted_optimization.py

Performs second-pass optimization specifically for agents that are closest to but still below the 0.87 fitness threshold:
- Auditor (0.8609)
- Bio (0.8607)
- Fractal (0.8697)
- Visual (0.8697)

The optimization focuses on fine-tuning phi_score, fibonacci_alignment, GC content, palindromes, and resonance_frequency to push these agents above the 0.87 threshold.

Usage:
```bash
python targeted_optimization.py
```

## Process Improvement

This approach addresses the engineering lesson learned that temporary helper scripts in the repo root can interfere with test discovery or directory assumptions. By keeping diagnostics and optimization helpers under this dedicated `tools/` folder, we maintain a cleaner repository structure.