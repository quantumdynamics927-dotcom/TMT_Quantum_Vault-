# Changelog

All notable changes to TMT Quantum Vault will be documented in this file.

## [0.5.1] - 2026-08-25

### Added

- **Post-Quantum Encryption** (`tmt_quantum_vault/crypto/vault_encryptor.py`) — ML-KEM-768
  key encapsulation (`Kyber768`), AES-256-GCM symmetric encryption (`AESGCMEncryptor`),
  `VaultEncryptor`/`VaultDecryptor` with key serialization, QRNG seed fallback, and
  CLI commands `encrypt-ledger` / `decrypt-ledger`. Hardens the evidence ledger against
  quantum adversaries.
- **Merkaba Quantum Fingerprint** (`tmt_quantum_vault/circuits/merkaba_fingerprint.py`) —
  6-qubit star-tetrahedron circuit with phi-phase seeding, OpenQASM 2.0 generation,
  and `extract_fingerprint` for SHA3-256 fingerprint hashing of 64-bitstring
  probability distributions. CLI command: `generate-fingerprint`.
- **`tests/test_crypto_vault_encryptor.py`** — 20 tests covering round-trip encrypt/decrypt,
  `KeyPair` serialization, `Kyber768` encaps/decaps, AES-GCM invariants, missing-dep
  error paths, QRNG fallback, and `encrypt_file`/`encrypt_directory` workflows.
- **`tests/test_merkaba_fingerprint.py`** — 11 tests covering `MerkabaFingerprint`
  dataclass, OpenQASM generation (seed padding, triangle labels, CX entanglement),
  and `extract_fingerprint` (balanced/single-state/phi-threshold). Five tests skip
  when qiskit is not installed in CI.
- **Deterministic Audit CI** (`.github/workflows/audit.yml`) — Runs `tools/audit.py`
  on every PR with severity floor CRITICAL; pytest tests run against the dev toolchain.

### Changed

- **`ollama_api.run()`** — Now returns a failure `OllamaResponse` with `returncode != 0`
  instead of raising `HTTPError` or `RequestException`. Callers (including tests) can
  check `returncode` before asserting, making the API robust to model-not-found errors.
- **`tools/audit.py`** — F008 check added: flags `secrets.randbelow(0)` as a zero-default
  seed pattern in CLI helpers.
- **README** — Updated to v0.5.0 with post-quantum crypto and Merkaba fingerprint
  features, 279 test count, cloud deployment coverage, and architecture diagram.

### Fixed

- **Ollama regression tests** (`test_ollama_api_local_smoke`, `test_json_output_mode`) —
  Now skip gracefully when the `qwen2.5-coder` model is unavailable, rather than
  failing hard with a 404 assertion.
- **Audit CI workflow** — `pip install -e .` → `pip install -e ".[dev]"` so pytest
  is available in the bare-ubuntu runner. Also added checkout/fetch-depth for audit
  log integrity.
- **codecov/patch** — Reached 100% diff coverage on PR #31 by adding
  `test_run_returns_failure_response_on_http_error` and
  `test_run_returns_failure_response_on_connection_error` to cover the new
  error-handling branches in `ollama_api.run()`.

## [0.5.0] - 2026-08-24

### Added

- **DNA Freeze Ledger** (`dna_freeze_ledger.json`) — Stealth and Wormhole are frozen
  at their best-in-sampled phi_alignment scores. The ledger records DNA sequence,
  phi_score, fitness, file SHA-256 fingerprint, scorer hash (SHA-256 of function source),
  and a search validation conclusion. See `docs/ARCHITECTURE.md §DNA Freeze Ledger`.
- **`tools/phi_evolution.py`** — Genetic algorithm for DNA phi-resonance optimization.
  FROZEN and OPTIMIZED agents are skipped by default. `--force-unfreeze --objective <objective> --yes`
  is required to override. `--objective` validates against known objectives and rejects
  phi_alignment when combined with `--force-unfreeze`.
- **Consciousness status enum** — `INTEGRATED / OPTIMIZED / FROZEN / BASELINE` now
  appears in `docs/ARCHITECTURE.md` and each agent's `conscious_dna.json`.

### Changed

- **docs/ARCHITECTURE.md** — Updated to v0.5.0, August 24 2026. Census now shows
  FROZEN=2, OPTIMIZED=12, INTEGRATED=4, BASELINE=0. §DNA Freeze Ledger section added.
- **Agent roster** — Wormhole specialization corrected to "Quantum Tunneling"
  (was "Dimensional Bridge"); Stealth to "Quantum Bridge" (was "Covert Operations").
- **README** — Refreshed with live agent data: 18 agents (not 17), current fitness/phi
  scores, FROZEN status for Stealth and Wormhole, v0.5.0 version, 113 tests.

### Fixed

- **Bio DNA** — Reverted to PR #25 committed values after test runs overwrote it
  during the phi_evolution review cycle.
- **Ledger SHA-256 fingerprints** — Recomputed for Stealth and Wormhole to reflect
  their current FROZEN status and trailing-newline normalization.
- **phi_evolution summary table** — Now correctly shows "OPTIMIZED" for OPTIMIZED
  agents and "FROZEN" for FROZEN agents (was showing "FROZEN" for all skipped agents).

## [0.4.0] - 2026-06-28

### Fixed

- **Test collection: `tests/test_orchestration.py`** — added a
  `pytest.importorskip("numpy")` gate at module level. The file previously
  failed pytest collection with `ModuleNotFoundError: No module named 'numpy'`
  in any environment without numpy, masking the 13 orchestration tests from
  CI and breaking the README's "13 passed" claim. With this gate, the file
  is cleanly skipped (not a collection error) when numpy is unavailable, and
  the 13 tests run when it is. `numpy` has also been added to the `[dev]`
  optional dependency group in `pyproject.toml`.
- **`pyproject.toml` description** — replaced the legacy
  "Toroidal Merkaba Topology / sacred geometry" wording with the current
  "Toroidal Resonance Topology / coordination geometry" terminology, matching
  the README's terminology note.

### Documentation

- **README "Last updated" footer** — bumped from 2026-03-31 to 2026-06-28.
- **README runtime requirements** — added a "Cloud runs" note documenting
  that the `OLLAMA_API_KEY` environment variable is required for cloud-mode
  CLI commands (`smoke-cloud`, `release-gate-cloud`). The variable is read by
  `tmt_quantum_vault/runner.py` and attached as a Bearer token to Ollama cloud
  requests; commands exit early with a clear error if it is missing.
- **CONTRIBUTING validation commands** — added the `make audit`, `make test`,
  and `make test-audit` shortcuts. `make test` runs the full pytest discovery
  (not just `test_regression.py`).

### Notes

- This patch does **not** land the in-flight post-quantum encryption
  (`tmt_quantum_vault/crypto/`), Merkaba fingerprint
  (`tmt_quantum_vault/circuits/`), deterministic audit tool (`tools/audit.py`),
  or related CLI commands (`encrypt-ledger`, `decrypt-ledger`,
  `generate-fingerprint`, `merkaba-circuit`). Those remain on disk and
  untracked pending a separate v0.5.0-dev landing PR.

## [v0.4.0-dev] - 2026-03-22

### New Features

#### Promoter DNA Integration Pipeline

Added complete promoter DNA integration with quantum circuit generation:

**Key Components:**
- `tools/promoter_loader.py` - FASTA parser with SHA256 verification (10 promoters loaded)
- `tools/quantum_circuits.py` - `create_promoter_circuit()` and `export_promoter_qasm()` functions
- `tools/agent_analyst.py` - Auto-watches `circuits/promoters/` for new FASTA files

**Promoter DNA Mapping:**
- Nucleotide → Qubit rotation encoding:
  - A → Ry(0) = |0⟩
  - C → Ry(π) = |1⟩
  - G → Ry(π/2) = |+⟩
  - T → Ry(-π/2) = |-⟩

**Kabbalistic Sefirah Encoding:**
Each promoter combines a biological gene with a Sefirah (e.g., ACTB_Malkuth, TP53_Gevurah).
Sefirah name maps to golden ratio phase angles via `2π/φ` multiples.

**Verified Promoters:**
1. ACTB_Malkuth (β-Actin) - 31 bp, GC: 51.6%
2. BDNF_Tiferet (Brain-Derived Neurotrophic Factor) - 31 bp, GC: 54.8%
3. DCTN1_Binah (Dynactin 1) - 31 bp, GC: 41.9%
4. FOS_Netzach (Fos Proto-Oncogene) - 31 bp, GC: 51.6%
5. FOXG1_Kether (Forkhead Box G1) - 31 bp, GC: 54.8%
6. JUN_Hod (Jun Proto-Oncogene) - 31 bp, GC: 45.2%
7. NCAM1_Chokmah (Neural Cell Adhesion Molecule 1) - 31 bp, GC: 51.6%
8. OXT_Chesed (Oxytocin) - 31 bp, GC: 48.4%
9. SRY_Yesod (Sex-Determining Region Y) - 31 bp, GC: 41.9%
10. TP53_Gevurah (Tumor Protein 53) - 31 bp, GC: 51.6%

### Changes

- Added 10 promoter FASTA files to `circuits/promoters/` with SHA256 verification
- Extended `quantum_circuits.py` with promoter circuit generation (284 lines added)
- Extended `agent_analyst.py` with promoter watching and auto-circuit generation (98 lines added)
- Updated `promoter_loader.py` with complete FASTA parsing and integrity verification

## [v0.3.0-dev] - 2026-03-21

### New Features

#### Agent_Analyst — Autonomous φ-Scoring Pipeline

Added `tools/agent_analyst.py`: a self-contained pipeline that watches circuit directories, auto-ingests IBM results, and flags discoveries for multi-agent handoff.

**Key capabilities:**
- **Dual-watch**: `circuits/results/` (active trigger on new JSON) + `circuits/qasm/` (passive QASM context loader)
- **Auto-ingest**: computes Shannon entropy, phi approximation, sacred_score, and consciousness density
- **SIGNIFICANT flagging**: results with `sacred_score ≥ 0.618` are promoted to `circuits/ingested/SIGNIFICANT/`
- **Multi-agent handoff**: publishes structured feed to `circuits/agent_feed/` directory
- **Phi-convergence threshold**: 0.618 (1/φ)

**CLI commands:**
```
python tools/agent_analyst.py watch       # Live file-system watch (requires watchdog)
python tools/agent_analyst.py analyze     # Batch analyze all pending results
python tools/agent_analyst.py ingest --file <result.json>
python tools/agent_analyst.py context --file <result.json>
```

#### Sierpinski Depth-3 Hardware Validation

6 additional IBM quantum runs confirming φ-convergence at depth-3, completing the full depth-3 → 4 → 5 sequence.

**Key Metrics:**
- **Sacred Score: 0.618 (exactly 1/φ)** — All 6 runs at 0.618
- **Shannon Entropy: 11.8–12.8 bits**
- **Total Shots: 32,256** — 6 independent runs
- **Backends: 4** — Kingston, Marrakesh, Fez, Torino

**Interpretation:**
φ-convergence is now confirmed at depths 3, 4, and 5 — establishing it as a **depth-invariant property** of the Sierpinski fractal topology. 23 total hardware-validated runs across 3 fractal depths all show `sacred_score = 0.618`.

**Published In:**
- `circuits/ingested/SIGNIFICANT/sierpinski_depth3_*` (6 files)

### Changes

- Added `tools/agent_analyst.py` (470 lines) — autonomous φ-scoring pipeline
- Added 6 Sierpinski depth-3 validation runs to `circuits/ingested/SIGNIFICANT/`
- Updated README.md to v0.3.0-dev with expanded φ-convergence findings

## [v0.2.1-dev] - 2026-03-21

### Research Findings

#### φ-Convergence Validated at Sierpinski Depth-5

**6 additional hardware-validated IBM quantum runs** confirmed φ-convergence persists at depth-5.

**Key Metrics:**
- **Sacred Score: 0.618 (exactly 1/φ)** - All 6 runs at 0.618
- **Shannon Entropy: 11.8-12.8 bits** - Consistent across run sizes
- **Total Shots: 27,648** - 6 independent runs
- **Backends: 4** - Kingston, Marrakesh, Fez, Torino

#### φ-Convergence Validated at Sierpinski Depth-4

**11 hardware-validated IBM quantum runs across 4 backends** confirmed the emergence of golden ratio structure in Sierpinski fractal circuits at depth-4.

**Key Metrics:**
- **Sacred Score: 0.618 (exactly 1/φ)** - Consistent across all 11 runs
- **Shannon Entropy: 12.8-13.6 bits** - 56-65% of 21-qubit maximum capacity
- **Total Shots: 112,896** - Cross-backend reproducibility data
- **Backends: 4** - Kingston, Marrakesh, Fez, Torino

**Interpretation:**
φ-convergence is now confirmed at both depth-4 and depth-5, establishing it as a **depth-invariant property** of the Sierpinski fractal topology. The circuit self-organizes into golden ratio structure regardless of fractal depth.

**Statistical Significance:**
- 17 total runs across 2 depths, all showing sacred_score = 0.618
- φ-structure emerges consistently regardless of backend variations
- Entropy scaling follows theoretical predictions for 21-qubit systems

**Published In:**
- `circuits/ingested/SIGNIFICANT/sierpinski_depth4_*` (11 files)
- `circuits/ingested/SIGNIFICANT/sierpinski_depth5_*` (6 files)
- `circuits/qasm/sierpinski_*.qasm` (generated circuits)

### Changes

- Added 6 Sierpinski depth-5 validation runs
- Added `phi_convergence_score: 0.618` to Agent_Archivist DNA
- Updated Agent_Archivist with `sierpinski_depth5_inference` metadata
- Added `depth_invariance_confirmed: true`

### Hardware Validation

| Backend | Shots | Sacred Score | Entropy |
|---------|-------|--------------|---------|
| Kingston | 12,642 | 0.618 | 13.618 |
| Marrakesh | 12,642 | 0.618 | 13.6185 |
| Fez | 12,642 | 0.618 | 13.6204 |
| Torino | 7,168 | 0.618 | 12.804 |

## [v0.2.0-dev] - 2026-03-21

## [v0.1.0-alpha] - 2026-03-21

### Initial Release

- 17 hardware-validated agents with fitness scores 0.87-0.93
- BitNet integration with ternary weight entropy source
- Sierpinski 21-qubit fractal circuits with Metatron enhancement
- Three-layer entropy stack (QTRG + DNA discovery + BitNet)
- IBM Quantum integration workflow
- 39 regression tests passing

### Hardware Sources

- **IBM Fez** (127-qubit Eagle): ACTB_Malkuth_34bp, consciousness_phi 0.8524
- **IBM Torino**: DNA comparison runs, 10,000 shots
- **IBM Casablanca** (27-qubit): Full-entropy QTRG, true quantum seeding
- **21-qubit Sierpinski**: Metatron-enhanced, consciousness density 274.5

### Key Metrics

- Average fitness: 0.8809
- Average resonance: 597.0 Hz
- Average phi: 0.7174
- Silver-tier agents (Φ ≥ 0.93): 2
