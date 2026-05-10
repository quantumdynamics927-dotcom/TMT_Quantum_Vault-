---
title: TMT Quantum Vault
emoji: 🔮
colorFrom: purple
colorTo: indigo
sdk: static
pinned: false
license: mit
short_description: Multi-agent orchestration for quantum computing workflows
---

# TMT Quantum Vault

Multi-agent orchestration framework for quantum computing workflows with phi-resonance alignment.

## Features

- **17-Agent Ensemble**: Specialized agents for synthesis, observation, validation, and more
- **Three-Lane Routing**: Simulation, Quantum (ibm_kingston), and LLM (Ollama) execution
- **Phi-Resonance Alignment**: Golden ratio-based coordination scoring
- **Benchmark Suite**: 19-task evaluation matrix for orchestration quality

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentOrchestrator                        │
│                    execution_mode: LIVE                      │
├─────────────────────────────────────────────────────────────┤
│  Lane 1: SIMULATION                                          │
│  └─ Fast, free, always available                            │
│                                                              │
│  Lane 2: QUANTUM → ibm_kingston (Heron r2, 156 qubits)      │
│  └─ phi_threshold: 0.618, budget: 180 min                   │
│                                                              │
│  Lane 3: LLM → Ollama (qwen2.5:1.5b)                         │
│  └─ Structured JSON output with resonance scoring            │
└─────────────────────────────────────────────────────────────┘
```

## Benchmark Results

| Metric | Value |
|--------|-------|
| Orchestration Score | 1.0 |
| Structural Passed | 19/19 |
| Expected Agents Hit Rate | 100% |
| Expected Layers Hit Rate | 100% |
| Average Confidence | 0.876 |
| Average Resonance | 0.87 |

## Documentation

- [Architecture](docs/architecture_canonical.json)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)

## License

MIT License - see [LICENSE](LICENSE) for details.