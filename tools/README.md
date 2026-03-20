# TMT Quantum Vault Tools

This directory contains helper scripts and tools for managing and optimizing the TMT Quantum Vault.

## Purpose

To organize diagnostic and optimization scripts outside of the main repository structure to avoid interference with test discovery and directory assumptions.

## Tools

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