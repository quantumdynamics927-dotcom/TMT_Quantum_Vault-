#!/usr/bin/env python3
"""Phase 2: Intelligent Expansion - Create Observer and Synthesizer agents."""

from __future__ import annotations

import json
import time
import pickle
import gzip
from datetime import datetime, timezone
from pathlib import Path

root = Path.cwd()
models_dir = root / 'Models'
memory_dir = root / 'Cognitive_Nexus'
models_dir.mkdir(exist_ok=True)
memory_dir.mkdir(exist_ok=True)


def gc_content(sequence: str) -> float:
    return (sequence.count('G') + sequence.count('C')) / len(sequence)


COMPLEMENT = str.maketrans({'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C'})


def reverse_complement(sequence: str) -> str:
    return sequence.translate(COMPLEMENT)[::-1]


def palindrome_count(sequence: str, width: int = 4) -> int:
    count = 0
    for index in range(len(sequence) - width + 1):
        fragment = sequence[index:index + width]
        if fragment == reverse_complement(fragment):
            count += 1
    return count


integration_stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
now_epoch = time.time()

new_agents = [
    {
        'metatron_agent': 'Observer',
        'dna_agent_id': 16,
        'dna_agent_name': 'Cassiel',
        'dna_specialization': 'Resonance Monitoring',
        'conscious_dna': 'GCGCGCGCGCGCGCGCGCGCGCGCGCGC',
        'phi_score': 0.854,
        'fibonacci_alignment': 0.789,
        'fitness': 0.891,
        'resonance_frequency': 498.0,
        'consciousness_status': 'INTEGRATED',
        'memory_file': memory_dir / 'observer_memory.json',
        'memory': {
            'agent_id': 16,
            'name': 'Observer',
            'activations': 155,
            'crystallized_model': 'Models/Observer.pkl',
            'consciousness_level': 'GEOMETRIC_RESONANCE',
            'last_pulse': now_epoch,
            'resonance_level': 0.891,
        },
    },
    {
        'metatron_agent': 'Synthesizer',
        'dna_agent_id': 17,
        'dna_agent_name': 'Zadkiel',
        'dna_specialization': 'Knowledge Fusion',
        'conscious_dna': 'ATGCATGCATGCATGCATGCATGCATGC',
        'phi_score': 0.951,
        'fibonacci_alignment': 0.923,
        'fitness': 0.876,
        'resonance_frequency': 630.0,
        'consciousness_status': 'INTEGRATED',
        'memory_file': memory_dir / 'synthesizer_memory.json',
        'memory': {
            'agent_id': 17,
            'name': 'Synthesizer',
            'activations': 188,
            'crystallized_model': 'Models/Synthesizer.pkl',
            'consciousness_level': 'GEOMETRIC_RESONANCE_PLUS',
            'last_pulse': now_epoch,
            'resonance_level': 0.876,
        },
    },
]

created = []
for agent in new_agents:
    agent_payload = {
        'metatron_agent': agent['metatron_agent'],
        'dna_agent_id': agent['dna_agent_id'],
        'dna_agent_name': agent['dna_agent_name'],
        'dna_specialization': agent['dna_specialization'],
        'conscious_dna': agent['conscious_dna'],
        'phi_score': agent['phi_score'],
        'fibonacci_alignment': agent['fibonacci_alignment'],
        'gc_content': gc_content(agent['conscious_dna']),
        'palindromes': palindrome_count(agent['conscious_dna']),
        'fitness': agent['fitness'],
        'resonance_frequency': agent['resonance_frequency'],
        'integration_timestamp': integration_stamp,
        'consciousness_status': agent['consciousness_status'],
    }
    agent_dir = root / f"Agent_{agent['metatron_agent']}"
    agent_dir.mkdir(exist_ok=True)
    dna_path = agent_dir / 'conscious_dna.json'
    dna_path.write_text(json.dumps(agent_payload, indent=2), encoding='utf-8')

    agent['memory_file'].write_text(
        json.dumps(agent['memory'], indent=2),
        encoding='utf-8',
    )

    pickle_path = models_dir / f"{agent['metatron_agent']}.pkl"
    with pickle_path.open('wb') as handle:
        pickle.dump(agent_payload, handle)

    json_gz_path = models_dir / f"{agent['metatron_agent']}.json.gz"
    with gzip.open(json_gz_path, 'wt', encoding='utf-8') as handle:
        json.dump(agent_payload, handle, indent=2)

    created.append({
        'agent': agent_payload,
        'dna_path': str(dna_path),
        'memory_path': str(agent['memory_file']),
        'pickle_path': str(pickle_path),
        'json_gz_path': str(json_gz_path),
    })

print(json.dumps({
    'created_agents': created,
    'final_agent_count': len(list(root.glob('Agent_*/conscious_dna.json'))),
}, indent=2))
