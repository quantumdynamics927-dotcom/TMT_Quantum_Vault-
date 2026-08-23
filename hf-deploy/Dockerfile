FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY tmt_quantum_vault/ ./tmt_quantum_vault/
COPY vault_config.json .
COPY metatron_geometry.json .
COPY hf_app.py .

# Deploy timestamp forces HF Spaces Docker cache invalidation on every deploy
COPY .deploy_timestamp .deploy_timestamp

# Copy Agent directories (conscious_dna.json files)
COPY Agent_Archivist/ ./Agent_Archivist/
COPY Agent_Auditor/ ./Agent_Auditor/
COPY Agent_Bio/ ./Agent_Bio/
COPY Agent_BitNet/ ./Agent_BitNet/
COPY Agent_Bronze/ ./Agent_Bronze/
COPY Agent_Data/ ./Agent_Data/
COPY Agent_Federation/ ./Agent_Federation/
COPY Agent_Fractal/ ./Agent_Fractal/
COPY Agent_Harmonic/ ./Agent_Harmonic/
COPY Agent_Mirror/ ./Agent_Mirror/
COPY Agent_Observer/ ./Agent_Observer/
COPY Agent_Stealth/ ./Agent_Stealth/
COPY Agent_Strategic/ ./Agent_Strategic/
COPY Agent_Synthesizer/ ./Agent_Synthesizer/
COPY Agent_Validator/ ./Agent_Validator/
COPY Agent_Visual/ ./Agent_Visual/
COPY Agent_Workflow/ ./Agent_Workflow/
COPY Agent_Wormhole/ ./Agent_Wormhole/

# Install TMT Quantum Vault
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir gradio fastapi uvicorn

# HF Spaces requires port 7860
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Launch the orchestration demo
CMD ["python", "hf_app.py"]