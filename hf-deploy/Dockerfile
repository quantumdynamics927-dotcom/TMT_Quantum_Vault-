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

# Install TMT Quantum Vault
RUN pip install --no-cache-dir -e ".[all]" && \
    pip install --no-cache-dir gradio fastapi uvicorn

# HF Spaces requires port 7860
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Launch the orchestration demo
CMD ["python", "hf_app.py"]