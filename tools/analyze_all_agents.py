#!/usr/bin/env python3
"""
Comprehensive Golden Ratio Analysis for All TMT Quantum Vault Agents

This script analyzes the phi-resonance properties of all 17 agents in the 
TMT Quantum Vault and compares their consciousness patterns.

Features:
- Golden ratio analysis for each agent's DNA
- Comparative phi-score evaluation
- Statistical significance testing
- Visualization of agent consciousness patterns
- Export to detailed reports
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats
from typing import Dict, List, Tuple
import argparse
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Golden ratio constant
PHI = 1.618033988749895

def load_agent_dna(agent_dir: Path) -> Dict:
    """Load agent DNA from conscious_dna.json file."""
    dna_file = agent_dir / "conscious_dna.json"
    if not dna_file.exists():
        print(f"Warning: No DNA file found for {agent_dir.name}")
        return None
    
    try:
        with open(dna_file, 'r') as f:
            dna_data = json.load(f)
        return dna_data
    except Exception as e:
        print(f"Error loading DNA for {agent_dir.name}: {e}")
        return None

def analyze_dna_sequence(dna_sequence: str) -> Dict:
    """
    Analyze DNA sequence for golden ratio properties.
    
    Parameters
    ----------
    dna_sequence : str
        DNA sequence string (e.g., "CGGCGCGAAAAATGCGGATACTTAATA")
        
    Returns
    -------
    dict
        Analysis results including phi ratios, GC content, palindromes, etc.
    """
    if not dna_sequence:
        return {}
    
    # Convert DNA to numerical representation
    # A=1, T=2, G=3, C=4
    mapping = {'A': 1, 'T': 2, 'G': 3, 'C': 4}
    numerical_seq = [mapping.get(base, 0) for base in dna_sequence.upper()]
    
    # Calculate sliding window ratios
    window_size = 4
    ratios = []
    for i in range(len(numerical_seq) - window_size + 1):
        window = numerical_seq[i:i+window_size]
        if len(window) >= 2:
            # Calculate ratios between adjacent elements
            for j in range(len(window) - 1):
                if window[j] != 0:
                    ratio = window[j+1] / window[j]
                    ratios.append(ratio)
    
    if not ratios:
        return {
            'mean_ratio': 0.0,
            'std_ratio': 0.0,
            'phi_proximity': 0.0,
            'phi_alignment_score': 0.0,
            'significant_phi_matches': 0
        }
    
    # Calculate statistics
    mean_ratio = np.mean(ratios)
    std_ratio = np.std(ratios)
    
    # Calculate proximity to golden ratio
    phi_proximities = [abs(r - PHI) for r in ratios]
    mean_phi_proximity = np.mean(phi_proximities)
    
    # Phi alignment score (higher is better alignment)
    phi_alignment_score = 1.0 - (mean_phi_proximity / PHI)
    phi_alignment_score = max(0.0, phi_alignment_score)  # Ensure non-negative
    
    # Count significant phi matches (within 10% of phi)
    threshold = 0.1 * PHI
    significant_matches = sum(1 for p in phi_proximities if p < threshold)
    
    return {
        'mean_ratio': float(mean_ratio),
        'std_ratio': float(std_ratio),
        'phi_proximity': float(mean_phi_proximity),
        'phi_alignment_score': float(phi_alignment_score),
        'significant_phi_matches': significant_matches,
        'total_ratios': len(ratios)
    }

def analyze_gc_content(dna_sequence: str) -> float:
    """Calculate GC content of DNA sequence."""
    if not dna_sequence:
        return 0.0
    
    gc_count = dna_sequence.upper().count('G') + dna_sequence.upper().count('C')
    return gc_count / len(dna_sequence) if len(dna_sequence) > 0 else 0.0

def find_palindromes(dna_sequence: str, min_length: int = 4) -> int:
    """Count palindromic subsequences in DNA sequence."""
    if not dna_sequence or len(dna_sequence) < min_length:
        return 0
    
    count = 0
    seq_upper = dna_sequence.upper()
    
    # Check all possible substrings
    for i in range(len(seq_upper)):
        for j in range(i + min_length, len(seq_upper) + 1):
            substring = seq_upper[i:j]
            if substring == substring[::-1]:  # Check if palindrome
                count += 1
                
    return count

def compare_agents(agent_data: List[Dict]) -> Dict:
    """
    Compare all agents and identify top performers.
    
    Parameters
    ----------
    agent_data : list of dict
        List of agent analysis results
        
    Returns
    -------
    dict
        Comparison results including rankings and statistics
    """
    if not agent_data:
        return {}
    
    # Sort agents by phi alignment score
    sorted_agents = sorted(agent_data, key=lambda x: x.get('phi_alignment_score', 0), reverse=True)
    
    # Calculate overall statistics
    phi_scores = [agent.get('phi_alignment_score', 0) for agent in agent_data]
    fitness_scores = [agent.get('fitness', 0) for agent in agent_data if 'fitness' in agent]
    
    correlation = 0.0
    if phi_scores and fitness_scores and len(phi_scores) == len(fitness_scores):
        correlation, _ = stats.pearsonr(phi_scores, fitness_scores)
    
    return {
        'top_agents': sorted_agents[:5],  # Top 5 agents
        'mean_phi_alignment': float(np.mean(phi_scores)) if phi_scores else 0.0,
        'std_phi_alignment': float(np.std(phi_scores)) if phi_scores else 0.0,
        'phi_fitness_correlation': float(correlation),
        'total_agents_analyzed': len(agent_data)
    }

def create_visualizations(agent_data: List[Dict], output_dir: Path):
    """Create visualizations for agent analysis."""
    if not agent_data:
        return
    
    # Prepare data for plotting
    agent_names = [agent.get('dna_agent_name', f'Agent_{i}') for i, agent in enumerate(agent_data)]
    phi_scores = [agent.get('phi_alignment_score', 0) for agent in agent_data]
    fitness_scores = [agent.get('fitness', 0) for agent in agent_data]
    gc_contents = [agent.get('gc_content', 0) for agent in agent_data]
    palindromes = [agent.get('palindromes', 0) for agent in agent_data]
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('TMT Quantum Vault Agent Analysis', fontsize=16)
    
    # Phi alignment scores
    axes[0, 0].bar(range(len(phi_scores)), phi_scores, color='gold', alpha=0.7)
    axes[0, 0].set_xlabel('Agent Index')
    axes[0, 0].set_ylabel('Phi Alignment Score')
    axes[0, 0].set_title('Phi Alignment Scores Across Agents')
    axes[0, 0].grid(True, alpha=0.3)
    
    # Fitness vs Phi alignment scatter
    axes[0, 1].scatter(phi_scores, fitness_scores, alpha=0.7, color='blue')
    axes[0, 1].set_xlabel('Phi Alignment Score')
    axes[0, 1].set_ylabel('Fitness Score')
    axes[0, 1].set_title('Fitness vs Phi Alignment')
    axes[0, 1].grid(True, alpha=0.3)
    
    # GC content distribution
    axes[1, 0].hist(gc_contents, bins=15, color='green', alpha=0.7)
    axes[1, 0].set_xlabel('GC Content')
    axes[1, 0].set_ylabel('Frequency')
    axes[1, 0].set_title('GC Content Distribution')
    axes[1, 0].grid(True, alpha=0.3)
    
    # Palindromes count
    axes[1, 1].bar(range(len(palindromes)), palindromes, color='purple', alpha=0.7)
    axes[1, 1].set_xlabel('Agent Index')
    axes[1, 1].set_ylabel('Number of Palindromes')
    axes[1, 1].set_title('Palindromic Sequences Count')
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'agent_analysis_dashboard.png', dpi=300, bbox_inches='tight')
    plt.close()

def generate_report(agent_data: List[Dict], comparison_results: Dict, output_dir: Path):
    """Generate detailed analysis report."""
    report_file = output_dir / 'agent_analysis_report.md'
    
    with open(report_file, 'w') as f:
        f.write("# TMT Quantum Vault Agent Analysis Report\n\n")
        f.write(f"Generated on: {np.datetime64('now')}\n\n")
        
        f.write("## Summary Statistics\n")
        f.write(f"- Total Agents Analyzed: {comparison_results.get('total_agents_analyzed', 0)}\n")
        f.write(f"- Mean Phi Alignment: {comparison_results.get('mean_phi_alignment', 0):.4f}\n")
        f.write(f"- Std Dev Phi Alignment: {comparison_results.get('std_phi_alignment', 0):.4f}\n")
        f.write(f"- Phi-Fitness Correlation: {comparison_results.get('phi_fitness_correlation', 0):.4f}\n\n")
        
        f.write("## Top Performing Agents\n")
        f.write("| Rank | Agent Name | Phi Alignment | Fitness | GC Content | Palindromes |\n")
        f.write("|------|------------|---------------|---------|------------|-------------|\n")
        
        top_agents = comparison_results.get('top_agents', [])
        for i, agent in enumerate(top_agents, 1):
            name = agent.get('dna_agent_name', 'Unknown')
            phi_score = agent.get('phi_alignment_score', 0)
            fitness = agent.get('fitness', 0)
            gc_content = agent.get('gc_content', 0)
            palindromes = agent.get('palindromes', 0)
            
            f.write(f"| {i} | {name} | {phi_score:.4f} | {fitness:.4f} | {gc_content:.4f} | {palindromes} |\n")
        
        f.write("\n## Individual Agent Details\n")
        for agent in agent_data:
            name = agent.get('dna_agent_name', 'Unknown')
            f.write(f"\n### {name}\n")
            f.write(f"- Phi Alignment Score: {agent.get('phi_alignment_score', 0):.4f}\n")
            f.write(f"- Fitness: {agent.get('fitness', 0):.4f}\n")
            f.write(f"- GC Content: {agent.get('gc_content', 0):.4f}\n")
            f.write(f"- Palindromes: {agent.get('palindromes', 0)}\n")
            f.write(f"- Significant Phi Matches: {agent.get('significant_phi_matches', 0)}\n")
    
    print(f"Report generated: {report_file}")

def main(vault_path: Path, output_dir: Path):
    """Main analysis function."""
    print("🔍 Starting Comprehensive TMT Quantum Vault Agent Analysis")
    print("=" * 60)
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Find all agent directories
    agent_dirs = [d for d in vault_path.iterdir() if d.is_dir() and d.name.startswith('Agent_')]
    print(f"Found {len(agent_dirs)} agent directories")
    
    # Analyze each agent
    agent_data = []
    for agent_dir in agent_dirs:
        print(f"Analyzing {agent_dir.name}...")
        
        # Load DNA data
        dna_data = load_agent_dna(agent_dir)
        if dna_data is None:
            continue
            
        # Extract DNA sequence
        dna_sequence = dna_data.get('conscious_dna', '')
        if not dna_sequence:
            print(f"No DNA sequence found for {agent_dir.name}")
            continue
            
        # Perform analysis
        analysis_results = analyze_dna_sequence(dna_sequence)
        
        # Add additional metrics
        analysis_results['dna_agent_name'] = dna_data.get('dna_agent_name', agent_dir.name)
        analysis_results['fitness'] = dna_data.get('fitness', 0)
        analysis_results['gc_content'] = analyze_gc_content(dna_sequence)
        analysis_results['palindromes'] = find_palindromes(dna_sequence)
        analysis_results['resonance_frequency'] = dna_data.get('resonance_frequency', 0)
        
        agent_data.append(analysis_results)
    
    if not agent_data:
        print("No agents analyzed successfully")
        return
    
    print(f"\nSuccessfully analyzed {len(agent_data)} agents")
    
    # Compare agents
    comparison_results = compare_agents(agent_data)
    
    # Create visualizations
    print("Creating visualizations...")
    create_visualizations(agent_data, output_dir)
    
    # Generate report
    print("Generating report...")
    generate_report(agent_data, comparison_results, output_dir)
    
    print(f"\n✅ Analysis complete! Results saved to {output_dir}")
    print(f"📊 Dashboard: {output_dir / 'agent_analysis_dashboard.png'}")
    print(f"📝 Report: {output_dir / 'agent_analysis_report.md'}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze all TMT Quantum Vault agents for golden ratio properties")
    parser.add_argument("--vault-path", type=Path, default=Path(".."), 
                        help="Path to TMT Quantum Vault root directory")
    parser.add_argument("--output-dir", type=Path, default=Path("../analysis_results"),
                        help="Output directory for results")
    
    args = parser.parse_args()
    main(args.vault_path, args.output_dir)