from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal
from typing import TypedDict

from pydantic import BaseModel, ConfigDict, Field


class VaultModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class OllamaRuntimeConfig(VaultModel):
    provider: Literal["ollama"] = "ollama"
    mode: Literal["local", "cloud"] = "cloud"
    local_model: str = "qwen3:8b"
    cloud_model: str = "qwen3.5:397b-cloud"
    host: str = "http://localhost:11434"
    cloud_host: str = "https://ollama.com"
    api_key_env: str = "OLLAMA_API_KEY"
    prompt_prefix: str | None = None


class LlamaCppRuntimeConfig(VaultModel):
    executable_path: str | None = None
    model_path: str = "Models/qwen3-8b.gguf"


class RuntimeConfig(VaultModel):
    preferred_backend: Literal["ollama", "llama.cpp"] = "ollama"
    ollama: OllamaRuntimeConfig = Field(default_factory=OllamaRuntimeConfig)
    llama_cpp: LlamaCppRuntimeConfig = Field(
        default_factory=LlamaCppRuntimeConfig
    )


class EvalExpectation(VaultModel):
    contains_all: list[str] = Field(default_factory=list)
    contains_any: list[str] = Field(default_factory=list)
    excludes: list[str] = Field(default_factory=list)


class EvalCase(VaultModel):
    id: str
    prompt: str
    system: str | None = None
    expectation: EvalExpectation = Field(default_factory=EvalExpectation)


class EvalDataset(VaultModel):
    name: str
    description: str | None = None
    backend: Literal["ollama", "llama.cpp"] | None = None
    mode: Literal["local", "cloud"] | None = None
    model: str | None = None
    cases: list[EvalCase] = Field(min_length=1)


class VaultConfig(VaultModel):
    vault_name: str
    creation_timestamp: float
    structure: dict[str, list[str]]
    stability_baseline: float
    fibonacci_sync: bool
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)


class GeometryConfig(VaultModel):
    vault_created: float
    silver_ratio: float
    bronze_ratio: float
    phi_ratio: float
    nodes: int
    resonance_pulse: float
    consciousness_level: str


class OptimizationData(VaultModel):
    timestamp: datetime
    duration: float
    dna_integrity: float
    network_efficiency: float
    resonance_harmonics: float
    collective_boost: float
    optimization_score: float


class OptimizationEntry(VaultModel):
    type: str
    data: OptimizationData


class AgentDNA(VaultModel):
    metatron_agent: str
    dna_agent_id: int
    dna_agent_name: str
    dna_specialization: str
    conscious_dna: str = Field(min_length=1)
    phi_score: float
    fibonacci_alignment: float
    gc_content: float
    palindromes: int
    fitness: float
    resonance_frequency: float
    integration_timestamp: str
    consciousness_status: str


class AgentMemory(VaultModel):
    agent_id: int
    name: str
    activations: int
    crystallized_model: str | None = None
    consciousness_level: str
    last_pulse: float
    resonance_level: float


class ValidationResult(BaseModel):
    path: str
    model_name: str
    valid: bool
    error: str | None = None


class SummarySnapshot(TypedDict):
    vault_name: str
    consciousness_level: str
    fibonacci_sync: bool
    agent_count: int
    integrated_agents: int
    average_fitness: float
    average_resonance_frequency: float
    top_agent: AgentDNA | None
    memory_store_count: int
    daily_log_count: int
    model_files: list[Path]
    latest_optimization: OptimizationEntry | None
