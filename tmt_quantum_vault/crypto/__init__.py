"""
Quantum-Secure Cryptography for TMT Quantum Vault.

This module provides post-quantum cryptographic primitives for protecting
sensitive vault artifacts using NIST-standardized algorithms.

Modules:
    vault_encryptor: ML-KEM-768 + AES-256-GCM encryption for evidence ledger

Usage:
    from tmt_quantum_vault.crypto import VaultEncryptor, VaultDecryptor

    # Encrypt
    encryptor = VaultEncryptor(vault_path=Path("."))
    enc_path, sk = encryptor.encrypt_evidence_ledger()

    # Decrypt
    decryptor = VaultDecryptor()
    plaintext_path = decryptor.decrypt_file(enc_path, sk)
"""

from tmt_quantum_vault.crypto.vault_encryptor import (
    ALGORITHM_AES_256_GCM,
    ALGORITHM_ML_KEM_768,
    AESGCMEncryptor,
    EncryptedArtifact,
    KeyPair,
    Kyber768,
    VaultDecryptor,
    VaultEncryptor,
    decrypt_ledger_cli,
    encrypt_ledger_cli,
)

__all__ = [
    # Constants
    "ALGORITHM_ML_KEM_768",
    "ALGORITHM_AES_256_GCM",
    # Classes
    "EncryptedArtifact",
    "KeyPair",
    "Kyber768",
    "AESGCMEncryptor",
    "VaultEncryptor",
    "VaultDecryptor",
    # CLI
    "encrypt_ledger_cli",
    "decrypt_ledger_cli",
]
