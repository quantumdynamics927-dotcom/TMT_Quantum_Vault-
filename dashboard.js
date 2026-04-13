async function fetchJson(path) {
  const response = await fetch(path, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Failed to load ${path}: ${response.status}`);
  }
  return response.json();
}

function formatNumber(value, digits = 4) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '--';
  }
  return Number(value).toFixed(digits);
}

function formatPValue(value) {
  if (value === null || value === undefined) {
    return '--';
  }
  const numeric = Number(value);
  if (numeric < 0.001) {
    return numeric.toExponential(2);
  }
  return numeric.toFixed(4);
}

async function renderIndexDashboard() {
  const state = document.getElementById('dashboard-load-state');
  if (!state) {
    return;
  }

  try {
    const [benchmark, scientific, bitnet, research] = await Promise.all([
      fetchJson('benchmark_results.json'),
      fetchJson('scientific_validation_report.json'),
      fetchJson('bitnet_benchmark_report.json'),
      fetchJson('research_status.json'),
    ]);

    document.getElementById('extended17-fitness').textContent = formatNumber(
      benchmark.extended17.aggregate_metrics.average_fitness,
      4,
    );
    document.getElementById('extended17-meta').textContent =
      `Extended-17 phi ${formatNumber(benchmark.extended17.aggregate_metrics.average_phi, 4)} · ${benchmark.extended17.node_count} nodes`;

    document.getElementById('validation-pass-rate').textContent = `${Math.round(scientific.summary.pass_rate * 100)}%`;
    document.getElementById('validation-meta').textContent =
      `${scientific.summary.passed}/${scientific.summary.total_tests} tests passed · empirical claims ${scientific.summary.claim_classes.empirical}`;

    document.getElementById('bitnet-score').textContent = formatNumber(
      bitnet.overall_improvement_score.combined_score,
      4,
    );
    document.getElementById('bitnet-meta').textContent =
      `Phi alignment baseline ${formatNumber(bitnet.phi_alignment.baseline, 4)} → bitnet ${formatNumber(bitnet.phi_alignment.bitnet, 4)}`;

    const cleanCount = research.measurements.filter((item) => item.measurement_class === 'measurement_clean').length;
    document.getElementById('research-clean-count').textContent = String(cleanCount);
    document.getElementById('research-meta').textContent =
      `${research.measurements.length} synced runs · ${research.cloud_model_results.length} cloud benchmarks tracked`;

    const rows = benchmark.extended17.agents
      .slice()
      .sort((left, right) => right.fitness - left.fitness)
      .slice(0, 5)
      .map((agent) => `
        <tr>
          <td>${agent.name}</td>
          <td>${formatNumber(agent.fitness, 4)}</td>
          <td>${formatNumber(agent.phi_score, 4)}</td>
          <td>${formatNumber(agent.resonance_frequency, 1)} Hz</td>
        </tr>
      `)
      .join('');
    document.querySelector('#top-agents-table tbody').innerHTML = rows;

    state.textContent = `Loaded benchmark_results.json, scientific_validation_report.json, bitnet_benchmark_report.json, and research_status.json at ${research.generated_at}.`;
  } catch (error) {
    state.textContent = `Dashboard load error: ${error.message}`;
  }
}

async function renderResearchStatus() {
  const page = document.getElementById('research-status-page');
  if (!page) {
    return;
  }

  const state = document.getElementById('research-load-state');
  try {
    const [research, scientific] = await Promise.all([
      fetchJson('research_status.json'),
      fetchJson('scientific_validation_report.json'),
    ]);

    document.getElementById('research-summary').textContent =
      `Synced from AGI-model ${research.source_snapshot.generated_at} · provider purity target ${research.measurement_vocabulary.provider_purity_target}.`;

    const measurementRows = research.measurements.map((item) => `
      <tr>
        <td>${item.label}</td>
        <td>${item.measurement_class}</td>
        <td>${item.provider_path}</td>
        <td>${item.provider_purity ?? '--'}</td>
        <td>${formatNumber(item.mean_phi_resonance, 4)}</td>
        <td>${formatNumber(item.null_baseline_mean, 4)}</td>
        <td>${formatNumber(item.effect_size, 4)}</td>
        <td>${formatPValue(item.p_value)}</td>
      </tr>
    `).join('');
    document.querySelector('#measurement-status-table tbody').innerHTML = measurementRows;

    const cloudRows = research.cloud_model_results.map((item) => `
      <tr>
        <td>${item.model}</td>
        <td>${item.status}</td>
        <td>${item.target_prompt_family}</td>
        <td>${item.measurement_target}</td>
        <td>${item.notes}</td>
      </tr>
    `).join('');
    document.querySelector('#cloud-model-table tbody').innerHTML = cloudRows;

    const scientificSummary = document.getElementById('scientific-sync-summary');
    scientificSummary.textContent =
      `${scientific.summary.passed}/${scientific.summary.total_tests} scientific validation tests passed · statistical inference failures ${scientific.categories.statistical_inference.failed}.`;

    state.textContent = `Loaded research_status.json and scientific_validation_report.json successfully.`;
  } catch (error) {
    state.textContent = `Research status load error: ${error.message}`;
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  await renderIndexDashboard();
  await renderResearchStatus();
});