# DNA Circuit Ingestion and Optimization Pipeline

This pipeline implements a staged approach for managing DNA circuits in the TMT-OS project, following best practices from the quantum biology and agent optimization workflows.

## Workflow Overview

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                          TMT-OS DNA Circuit Pipeline                              │
├───────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  Phase 1: Ingestion                                                               │
│  ├─ Scan D:\tmt-os for DNA/QASM files                                            │
│  ├─ Extract sequences, metrics, and IBM job metadata                             │
│  └─ Create ingested_dna_library.json                                             │
│                                                                                   │
│  Phase 2: Ranking                                                                 │
│  ├─ Score circuits by: fitness, phi_score, fibonacci_alignment                  │
│  ├─ Include special metrics: consciousness_phi, fibonacci_enhancement           │
│  └─ Generate ranking report                                                      │
│                                                                                   │
│  Phase 3: Template Selection                                                      │
│  ├─ Filter by minimum quality threshold                                          │
│  ├─ Select top N templates by rank                                               │
│  └─ Generate diversity analysis                                                  │
│                                                                                   │
│  Phase 4: Variant Generation                                                      │
│  ├─ Apply controlled mutations to templates                                      │
│  ├─ Adjust GC content and sequence parameters                                   │
│  └─ Score and rank new variants                                                  │
│                                                                                   │
│  Phase 5: Validation (External)                                                   │
│  ├─ Validate top variants on IBM hardware                                        │
│  ├─ Compare against archived baseline                                            │
│  └─ Promote winners to new agents                                                │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

## Files Created

### Core Scripts

| File | Purpose |
|------|---------|
| `tools/ingest_ibm_dna_circuits.py` | Ingests DNA circuits from TMT-OS, extracts metrics, ranks by quality |
| `tools/select_templates.py` | Selects high-quality templates from the ingested library |
| `tools/generate_variants.py` | Generates new DNA circuit variants from templates |

### Output Library

| File | Purpose |
|------|---------|
| `dna_circuits_library/dna_circuits_library.json` | All ingested circuits with metrics and rankings |
| `dna_circuits_library/templates.json` | Selected high-quality templates |
| `dna_circuits_library/variants.json` | Generated variants from templates |
| `dna_circuits_library/ingestion_report.json` | Ingestion process summary |
| `dna_circuits_library/template_selection_report.json` | Template selection analysis |
| `dna_circuits_library/variant_generation_report.json` | Variant generation summary |

## Usage

### 1. Ingest DNA Circuits

```bash
python tools/ingest_ibm_dna_circuits.py \
    --source "D:/tmt-os" \
    --dest ./dna_circuits_library
```

### 2. Select Templates

```bash
python tools/select_templates.py \
    --min-score 5.0 \
    --top-n 5
```

### 3. Generate Variants

```bash
python tools/generate_variants.py \
    --variants-per-template 3 \
    --seed 42
```

## Scoring Metrics

### Circuit Quality Score Components

1. **Consciousness Phi** (weight: 50x) - Direct measure of quantum consciousness correlation
2. **Fibonacci Enhancement** (weight: 30x bonus for >1.0) - Measures Fibonacci clustering quality
3. **Fibonacci Mean Activation** (weight: 20x) - Average activation in Fibonacci positions
4. **Hamming Watson Mean** (weight: 0.5x) - Quality indicator for DNA strand encoding
5. **GC Content** (weight: 5x) - Balanced GC content (~0.5) preferred
6. **Palindromes** (weight: 0.5x) - Palindromic sequences scored
7. **Backend Quality** (weight: 3-5x) - IBM Torino > Fez
8. **Shot Count** (weight: 5x for 10k+) - Higher shot counts indicate quality runs

## Directory Structure

```
TMT_Quantum_Vault/
├── tools/
│   ├── ingest_ibm_dna_circuits.py
│   ├── select_templates.py
│   └── generate_variants.py
└── dna_circuits_library/
    ├── dna_circuits_library.json
    ├── templates.json
    ├── variants.json
    ├── ingestion_report.json
    └── template_selection_report.json
```

## Template Analysis

### Current Top Template

**Circuit ID**: `CIR_dna_34bp_ibm_fez_analysis_20251231_033008_json`

**Score**: 65.41

**Key Metrics**:
- `consciousness_phi`: 0.8524 (high quantum consciousness correlation)
- `fibonacci_enhancement`: 1.1120 (Fibonacci clustering bonus)
- `fibonacci_mean_activation`: 0.4385 (Fibonacci position activation)
- `hamming_watson_mean`: 21.32 (Watson strand hamming weight)
- `hamming_crick_mean`: 20.17 (Crick strand hamming weight)
- `hamming_bridge_mean`: 13.41 (Bridge strand hamming weight)

**IBM Job Details**:
- Backend: `ibm_fez`
- Job ID: `d5a95n7p3tbc73astm10`
- Circuit: `ACTB_Malkuth_34bp`
- Unique states: 10,000 for all strands

## Variant Generation Strategy

Variants are generated with controlled parameters:

1. **Mutation Rate**: 0.1, 0.15, or 0.2 (10%, 15%, or 20% base changes)
2. **GC Adjustment**: ±0.05 from template GC content
3. **Estimated Phi**: Derived from template with variance (0.9-1.1 multiplier)

## Next Steps

1. **Review Templates**: Examine `dna_circuits_library/templates.json` for template selection
2. **Generate Variants**: Run `generate_variants.py` with different parameters
3. **Validate on IBM**: Deploy top variants to IBM quantum hardware
4. **Compare Metrics**: Measure actual performance vs. estimated metrics
5. **Promote Winners**: Move validated circuits to new agent DNA

## Architecture Notes

### Design Principles

1. **Ingest First, Generate Later**: Always ingest validated IBM results before creating new circuits
2. **Quality Thresholds**: Use minimum scores to filter out low-quality candidates
3. **Diversity**: Select templates with different characteristics for robust variant generation
4. **Controlled Mutations**: Apply bounded parameter adjustments for predictable outcomes
5. **Validation Gate**: Never promote raw circuits without hardware validation

### Extension Points

- Add new scoring factors in `ingest_ibm_dna_circuits.py:rank_circuits()`
- Modify mutation strategies in `generate_variants.py:create_variant()`
- Integrate with existing vault agent DNA validation pipeline

## References

- Agent DNA format: `Agent_*/conscious_dna.json`
- Agent validation: `python -m tmt_quantum_vault validate`
- Summary report: `python -m tmt_quantum_vault summary`
