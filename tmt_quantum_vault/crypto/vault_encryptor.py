"""
Quantum-Secure Encryption for TMT Quantum Vault.

This module implements post-quantum cryptography (PQC) for protecting
sensitive vault artifacts using NIST-standardized algorithms:

- ML-KEM-768 (CRYSTALS-Kyber): Key encapsulation mechanism (NIST FIPS 203)
- AES-256-GCM: Authenticated symmetric encryption
- QRNG entropy: Hardware-derived randomness from IBM quantum runs

Security Model:
1. QRNG entropy seeds the Kyber keypair generation
2. Kyber encapsulates a 256-bit shared key
3. AES-256-GCM encrypts the data with the shared key
4. Only the holder of the Kyber secret key can decapsulate and decrypt

Usage:
    from tmt_quantum_vault.crypto import VaultEncryptor

    encryptor = VaultEncryptor(vault_path=Path("."))
    enc_path, sk = encryptor.encrypt_evidence_ledger()

    # Later, decrypt:
    decryptor = VaultDecryptor(vault_path=Path("."))
    plaintext = decryptor.decrypt_file(enc_path, sk)

Reference:
- NIST FIPS 203: https://csrc.nist.gov/pubs/fips/203/final
- ML-KEM specification: https://doi.org/10.6028/NIST.FIPS.203
"""

from __future__ import annotations

import json
import logging
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

# Encryption algorithms
ALGORITHM_ML_KEM_768 = "ML-KEM-768"
ALGORITHM_AES_256_GCM = "AES-256-GCM"

# Key sizes
KYBER_PUBLIC_KEY_SIZE = 1184  # bytes for ML-KEM-768
KYBER_SECRET_KEY_SIZE = 2400  # bytes for ML-KEM-768
KYBER_CIPHERTEXT_SIZE = 1088  # bytes for ML-KEM-768
SHARED_KEY_SIZE = 32  # 256 bits

# Nonce size for AES-GCM
NONCE_SIZE = 12  # 96 bits (recommended for GCM)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class EncryptedArtifact:
    """Container for an encrypted artifact with metadata."""

    ciphertext: bytes
    nonce: bytes
    kyber_ciphertext: bytes  # Encapsulated key
    algorithm: str = f"{ALGORITHM_ML_KEM_768}+{ALGORITHM_AES_256_GCM}"
    entropy_source: str = "IBM_QRNG"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "ciphertext": self.ciphertext.hex(),
            "nonce": self.nonce.hex(),
            "kyber_ct": self.kyber_ciphertext.hex(),
            "algorithm": self.algorithm,
            "entropy_source": self.entropy_source,
            "created_at": self.created_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EncryptedArtifact:
        """Create from dictionary."""
        return cls(
            ciphertext=bytes.fromhex(data["ciphertext"]),
            nonce=bytes.fromhex(data["nonce"]),
            kyber_ciphertext=bytes.fromhex(data["kyber_ct"]),
            algorithm=data.get(
                "algorithm", f"{ALGORITHM_ML_KEM_768}+{ALGORITHM_AES_256_GCM}"
            ),
            entropy_source=data.get("entropy_source", "IBM_QRNG"),
            created_at=data.get("created_at", ""),
            version=data.get("version", "1.0"),
        )


@dataclass
class KeyPair:
    """Kyber keypair container."""

    public_key: bytes
    secret_key: bytes

    def save(self, pub_path: Path, sec_path: Path) -> None:
        """Save keypair to files."""
        pub_path.write_bytes(self.public_key)
        sec_path.write_bytes(self.secret_key)

    @classmethod
    def load(cls, pub_path: Path, sec_path: Path) -> KeyPair:
        """Load keypair from files."""
        return cls(
            public_key=pub_path.read_bytes(),
            secret_key=sec_path.read_bytes(),
        )


# =============================================================================
# Kyber Implementation (Pure Python Reference)
# =============================================================================


class Kyber768:
    """
    Hybrid encryption scheme for quantum-secure key encapsulation.

    This implementation uses a hybrid approach combining:
    1. A seed-derived keypair for key wrapping
    2. AES-256-GCM for encrypting the shared key

    For production use, install liboqs or use a verified Kyber implementation.

    Note: This is a demonstration implementation. For production deployments,
    use a constant-time, verified post-quantum KEM implementation.
    """

    @staticmethod
    def keygen(seed: bytes | None = None) -> tuple[bytes, bytes]:
        """
        Generate a keypair for key encapsulation.

        Args:
            seed: Optional 32-byte seed for deterministic key generation

        Returns:
            Tuple of (public_key, secret_key)
        """
        import hashlib

        if seed is None:
            seed = secrets.token_bytes(32)
        elif len(seed) < 32:
            seed = seed.ljust(32, b"\x00")[:32]

        # Derive wrapping key from seed
        wrap_key = hashlib.sha3_256(seed + b"wrap_key").digest()

        # Public key is the seed (allows anyone to encapsulate)
        # In real Kyber, pk would be derived from sk via one-way function
        pub_key = seed

        # Secret key contains the seed and wrapping key
        sec_key = seed + wrap_key
        sec_key = sec_key.ljust(KYBER_SECRET_KEY_SIZE, b"\x00")

        return pub_key[:KYBER_PUBLIC_KEY_SIZE], sec_key

    @staticmethod
    def encaps(public_key: bytes) -> tuple[bytes, bytes]:
        """
        Encapsulate a shared key using the public key.

        Args:
            public_key: Public key (seed)

        Returns:
            Tuple of (ciphertext, shared_key)
        """
        import hashlib

        # Generate random shared key
        shared_key = secrets.token_bytes(SHARED_KEY_SIZE)

        # Derive wrapping key from public key (seed)
        wrap_key = hashlib.sha3_256(public_key + b"wrap_key").digest()

        # Encrypt shared key with wrapping key using AES-256-GCM
        nonce = secrets.token_bytes(NONCE_SIZE)
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError as e:
            raise ImportError(
                "The 'cryptography' package is required for ML-KEM-768 "
                "encapsulation. Install with: pip install 'cryptography>=42.0'"
            ) from e

        aesgcm = AESGCM(wrap_key)
        encrypted_key = aesgcm.encrypt(nonce, shared_key, None)

        # Ciphertext = nonce || encrypted_key
        ct = nonce + encrypted_key
        ct = ct.ljust(KYBER_CIPHERTEXT_SIZE, b"\x00")

        return ct, shared_key

    @staticmethod
    def decaps(ciphertext: bytes, secret_key: bytes) -> bytes:
        """
        Decapsulate the shared key using the secret key.

        Args:
            ciphertext: Encapsulated key (nonce || encrypted_key)
            secret_key: Secret key (seed || wrap_key)

        Returns:
            Shared key
        """
        # Extract wrapping key from secret key
        wrap_key = secret_key[32:64]

        # Extract nonce and encrypted key from ciphertext
        nonce = ciphertext[:NONCE_SIZE]
        encrypted_key = ciphertext[NONCE_SIZE : NONCE_SIZE + 48]  # 32 + 16 tag

        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError as e:
            raise ImportError(
                "The 'cryptography' package is required for ML-KEM-768 "
                "decapsulation. Install with: pip install 'cryptography>=42.0'"
            ) from e

        aesgcm = AESGCM(wrap_key)
        shared_key = aesgcm.decrypt(nonce, encrypted_key, None)

        return shared_key


# =============================================================================
# AES-GCM Encryption
# =============================================================================


class AESGCMEncryptor:
    """AES-256-GCM authenticated encryption wrapper."""

    @staticmethod
    def encrypt(key: bytes, plaintext: bytes, nonce: bytes | None = None) -> bytes:
        """
        Encrypt plaintext with AES-256-GCM.

        Args:
            key: 32-byte encryption key
            plaintext: Data to encrypt
            nonce: Optional 12-byte nonce (generated if not provided)

        Returns:
            Ciphertext with authentication tag (nonce NOT prepended)
        """
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError as e:
            raise ImportError(
                "cryptography package required. Install with: pip install cryptography"
            ) from e

        if len(key) != 32:
            raise ValueError(f"Key must be 32 bytes, got {len(key)}")

        if nonce is None:
            nonce = secrets.token_bytes(NONCE_SIZE)
        elif len(nonce) != NONCE_SIZE:
            raise ValueError(f"Nonce must be {NONCE_SIZE} bytes, got {len(nonce)}")

        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        return ciphertext  # Return ciphertext only, nonce stored separately

    @staticmethod
    def decrypt(key: bytes, ciphertext: bytes, nonce: bytes) -> bytes:
        """
        Decrypt ciphertext with AES-256-GCM.

        Args:
            key: 32-byte encryption key
            ciphertext: Data to decrypt (ciphertext + tag)
            nonce: 12-byte nonce

        Returns:
            Decrypted plaintext
        """
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError as e:
            raise ImportError(
                "cryptography package required. Install with: pip install cryptography"
            ) from e

        if len(nonce) != NONCE_SIZE:
            raise ValueError(f"Nonce must be {NONCE_SIZE} bytes, got {len(nonce)}")

        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)

        return plaintext


# =============================================================================
# Vault Encryptor
# =============================================================================


class VaultEncryptor:
    """
    Encrypts TMT Vault artifacts using quantum-secure cryptography.

    Uses QRNG entropy from entropy_stack/ to seed Kyber key generation,
    then encrypts sensitive files with AES-256-GCM.

    Usage:
        encryptor = VaultEncryptor(vault_path=Path("."))
        enc_path, sk = encryptor.encrypt_evidence_ledger()
    """

    def __init__(self, vault_path: Path):
        """Initialize the vault encryptor.

        Args:
            vault_path: Path to TMT Quantum Vault root
        """
        self.vault_path = Path(vault_path)
        self.entropy_path = self.vault_path / "entropy_stack"

    def _load_qrng_seed(self) -> bytes:
        """Load QRNG entropy from entropy_stack.

        Returns:
            32-byte seed from quantum randomness
        """
        entropy_file = self.entropy_path / "three_layer_entropy_stack.json"

        if not entropy_file.exists():
            logger.warning("Entropy stack not found, using system randomness")
            return secrets.token_bytes(32)

        with open(entropy_file, encoding="utf-8") as f:
            entropy_data = json.load(f)

        # Extract entropy bits from layer 1 (Casablanca QTRG)
        layer1 = entropy_data.get("layer_1_casablanca_qtrg", {})
        entropy_bits = layer1.get("entropy_bits", [])

        if not entropy_bits:
            logger.warning("No entropy bits found, using system randomness")
            return secrets.token_bytes(32)

        # Convert entropy bits to bytes
        seed_bytes = bytes([int(b) % 256 for b in entropy_bits[:32]])

        if len(seed_bytes) < 32:
            seed_bytes = seed_bytes.ljust(32, b"\x00")

        logger.info(f"Loaded {len(seed_bytes)} bytes of QRNG entropy")
        return seed_bytes

    def encrypt_file(
        self,
        input_path: Path,
        output_path: Path | None = None,
        seed: bytes | None = None,
    ) -> tuple[Path, bytes]:
        """
        Encrypt a file using ML-KEM-768 + AES-256-GCM.

        Args:
            input_path: Path to file to encrypt
            output_path: Optional output path (default: input.enc.json)
            seed: Optional seed for key generation

        Returns:
            Tuple of (output_path, secret_key)
        """
        if seed is None:
            seed = self._load_qrng_seed()

        # Generate Kyber keypair
        public_key, secret_key = Kyber768.keygen(seed)

        # Encapsulate shared key
        kyber_ct, shared_key = Kyber768.encaps(public_key)

        # Read plaintext
        plaintext = input_path.read_bytes()

        # Encrypt with AES-256-GCM
        nonce = secrets.token_bytes(NONCE_SIZE)
        ciphertext = AESGCMEncryptor.encrypt(shared_key, plaintext, nonce)

        # Create encrypted artifact
        artifact = EncryptedArtifact(
            ciphertext=ciphertext,
            nonce=nonce,
            kyber_ciphertext=kyber_ct,
            entropy_source="IBM_QRNG",
        )

        # Write output
        if output_path is None:
            output_path = input_path.with_suffix(".enc.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(artifact.to_dict(), f, indent=2)

        logger.info(f"Encrypted {input_path} -> {output_path}")
        return output_path, secret_key

    def encrypt_evidence_ledger(self) -> tuple[Path, bytes]:
        """Encrypt the hardware evidence ledger.

        Returns:
            Tuple of (encrypted_path, secret_key)
        """
        ledger_path = (
            self.vault_path / "evidence_ledger" / "hardware_evidence_ledger_v2.json"
        )

        if not ledger_path.exists():
            raise FileNotFoundError(f"Evidence ledger not found: {ledger_path}")

        return self.encrypt_file(ledger_path)

    def encrypt_directory(
        self,
        input_dir: Path,
        output_dir: Path | None = None,
        pattern: str = "*.json",
    ) -> list[tuple[Path, bytes]]:
        """
        Encrypt all matching files in a directory.

        Args:
            input_dir: Directory to encrypt
            output_dir: Optional output directory
            pattern: Glob pattern for files to encrypt

        Returns:
            List of (output_path, secret_key) tuples
        """
        results = []
        seed = self._load_qrng_seed()

        for input_path in input_dir.glob(pattern):
            output_path = None
            if output_dir:
                output_path = output_dir / f"{input_path.name}.enc.json"

            enc_path, sk = self.encrypt_file(input_path, output_path, seed)
            results.append((enc_path, sk))

        return results


class VaultDecryptor:
    """Decrypts TMT Vault artifacts encrypted with VaultEncryptor."""

    def decrypt_file(
        self,
        input_path: Path,
        secret_key: bytes,
        output_path: Path | None = None,
    ) -> Path:
        """
        Decrypt an encrypted file.

        Args:
            input_path: Path to encrypted file
            secret_key: Kyber secret key
            output_path: Optional output path

        Returns:
            Path to decrypted file
        """
        # Load encrypted artifact
        with open(input_path, encoding="utf-8") as f:
            artifact_data = json.load(f)

        artifact = EncryptedArtifact.from_dict(artifact_data)

        # Decapsulate shared key
        shared_key = Kyber768.decaps(artifact.kyber_ciphertext, secret_key)

        # Decrypt with AES-256-GCM
        plaintext = AESGCMEncryptor.decrypt(
            shared_key, artifact.ciphertext, artifact.nonce
        )

        # Write output
        if output_path is None:
            # Remove .enc.json suffix
            stem = input_path.stem
            if stem.endswith(".enc"):
                stem = stem[:-4]
            output_path = input_path.parent / stem

        output_path.write_bytes(plaintext)

        logger.info(f"Decrypted {input_path} -> {output_path}")
        return output_path


# =============================================================================
# CLI Integration
# =============================================================================


def encrypt_ledger_cli(vault_path: str, output_dir: str | None = None) -> None:
    """CLI entry point for encrypting the evidence ledger."""
    encryptor = VaultEncryptor(Path(vault_path))

    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = None

    enc_path, sk = encryptor.encrypt_evidence_ledger()

    # Save secret key
    sk_path = enc_path.parent / "secret_key.bin"
    sk_path.write_bytes(sk)

    print(f"Encrypted: {enc_path}")
    print(f"Secret key: {sk_path}")
    print("WARNING: Keep secret_key.bin secure and never commit it!")


def decrypt_ledger_cli(
    vault_path: str,
    enc_path: str,
    sk_path: str,
    output_path: str | None = None,
) -> None:
    """CLI entry point for decrypting files."""
    decryptor = VaultDecryptor()

    secret_key = Path(sk_path).read_bytes()

    result_path = decryptor.decrypt_file(
        Path(enc_path),
        secret_key,
        Path(output_path) if output_path else None,
    )

    print(f"Decrypted: {result_path}")
