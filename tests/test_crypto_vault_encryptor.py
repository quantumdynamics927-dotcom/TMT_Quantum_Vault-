#!/usr/bin/env python3
"""
Tests for tmt_quantum_vault.crypto.vault_encryptor — the post-quantum
encryption module.

These tests cover:
- Round-trip encrypt/decrypt integrity (SHA-256 of plaintext == decrypted).
- ML-KEM-768 secret key length constant.
- No-XOR-fallback regression test (catches F-004 coming back).
- ImportError behavior when the `cryptography` package is unavailable.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

# ══════════════════════════════════════════════════════════════════════════════
# STATIC INVARIANTS
# ══════════════════════════════════════════════════════════════════════════════


def test_no_xor_fallback_in_source() -> None:
    """The XOR fallback (F-004) must not return to vault_encryptor.py.

    This is a regression test: if anyone re-introduces a `bytes(a ^ b for ...)`
    fallback in the encaps/decaps paths, this test will fail.
    """
    src_path = (
        Path(__file__).resolve().parent.parent
        / "tmt_quantum_vault"
        / "crypto"
        / "vault_encryptor.py"
    )
    src = src_path.read_text(encoding="utf-8")
    # Match `bytes(a ^ b for ...)` style — any of these patterns is a regression.
    bad_patterns = [
        r"bytes\(\s*a\s*\^\s*b\s+for\b",
        r"\^\s*b\s+for\s+a,\s*b\s+in\s+zip",
    ]
    import re

    for pat in bad_patterns:
        assert not re.search(pat, src), (
            f"vault_encryptor.py contains XOR fallback pattern `{pat}`. "
            "This regresses F-004."
        )


def test_cryptography_is_a_hard_dependency_in_pyproject() -> None:
    """`cryptography` must be declared in [project].dependencies, not optional."""
    pp = Path(__file__).resolve().parent.parent / "pyproject.toml"
    text = pp.read_text(encoding="utf-8")
    # Find the [project.dependencies] block (the first one; not optional-dependencies)
    import re

    m = re.search(
        r"dependencies\s*=\s*\[([^\]]+)\]",
        text,
        re.DOTALL,
    )
    assert m, "Could not find [project].dependencies block in pyproject.toml"
    block = m.group(1).lower()
    assert "cryptography" in block, (
        "cryptography is not declared in [project].dependencies. "
        "It must be a hard dependency to prevent F-004 from regressing."
    )


# ══════════════════════════════════════════════════════════════════════════════
# ROUND-TRIP
# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# KeyPair
# ══════════════════════════════════════════════════════════════════════════════


def test_keypair_save_and_load(tmp_path: Path) -> None:
    """KeyPair.save/load round-trips the keypair correctly."""
    from tmt_quantum_vault.crypto.vault_encryptor import KeyPair

    pk = b"pk" * 16
    sk = b"sk" * 800
    kp = KeyPair(public_key=pk, secret_key=sk)

    pub_path = tmp_path / "pub.key"
    sec_path = tmp_path / "sec.key"
    kp.save(pub_path, sec_path)

    loaded = KeyPair.load(pub_path, sec_path)
    assert loaded.public_key == pk
    assert loaded.secret_key == sk


# ══════════════════════════════════════════════════════════════════════════════
# Kyber round-trip
# ══════════════════════════════════════════════════════════════════════════════


def test_kyber768_keygen_short_seed_pads_to_32() -> None:
    """seed shorter than 32 bytes is left-padded with zeros to reach 32."""
    from tmt_quantum_vault.crypto.vault_encryptor import Kyber768

    pk, sk = Kyber768.keygen(seed=b"short")
    assert len(pk) == 32
    assert len(sk) == 2400


def test_kyber768_keygen_returns_padded_secret_key() -> None:
    """keygen() returns a keypair; the public key is the seed (32 bytes) and
    the secret key is padded to KYBER_SECRET_KEY_SIZE.

    Note: this is a *demonstration* Kyber implementation (see module docstring
    at lines 142-145). The real ML-KEM-768 public key would be 1184 bytes;
    this one is the 32-byte seed. The KYBER_PUBLIC_KEY_SIZE constant is the
    *real* standard size, used only for output length-padding compatibility
    in the ciphertext layout.
    """
    from tmt_quantum_vault.crypto.vault_encryptor import (
        KYBER_SECRET_KEY_SIZE,
        Kyber768,
    )

    pk, sk = Kyber768.keygen()
    # The public key is the 32-byte seed in this demo implementation.
    assert len(pk) == 32
    # The secret key is padded to the standard ML-KEM-768 size.
    assert len(sk) == KYBER_SECRET_KEY_SIZE


def test_kyber768_round_trip_encaps_decaps() -> None:
    """encaps(public_key) returns a ciphertext that decaps(secret_key) reverses."""
    from tmt_quantum_vault.crypto.vault_encryptor import Kyber768

    pk, sk = Kyber768.keygen()
    ct, shared_enc = Kyber768.encaps(pk)
    shared_dec = Kyber768.decaps(ct, sk)
    assert (
        shared_enc == shared_dec
    ), "decaps did not recover the encapsulated shared key"
    assert len(shared_enc) == 32  # 256-bit shared key


def test_aesgcm_encrypt_decrypt_round_trip(tmp_path: Path) -> None:
    """AESGCMEncryptor.encrypt/decrypt is a faithful round-trip."""
    from tmt_quantum_vault.crypto.vault_encryptor import AESGCMEncryptor

    key = b"\x01" * 32
    nonce = b"\x02" * 12
    plaintext = b"the quick brown fox jumps over the lazy dog"
    ciphertext = AESGCMEncryptor.encrypt(key, plaintext, nonce)
    assert ciphertext != plaintext
    recovered = AESGCMEncryptor.decrypt(key, ciphertext, nonce)
    assert recovered == plaintext


def test_aesgcm_rejects_wrong_key(tmp_path: Path) -> None:
    """Wrong key → AEAD tag-mismatch raises (this is the property F-006 needs)."""
    from cryptography.exceptions import InvalidTag  # type: ignore[import-not-found]

    from tmt_quantum_vault.crypto.vault_encryptor import AESGCMEncryptor

    plaintext = b"secret"
    nonce = b"\x03" * 12
    ciphertext = AESGCMEncryptor.encrypt(b"\x01" * 32, plaintext, nonce)
    with pytest.raises(InvalidTag):
        AESGCMEncryptor.decrypt(b"\x99" * 32, ciphertext, nonce)


def test_aesgcm_rejects_wrong_nonce_length() -> None:
    """Wrong nonce length → ValueError."""
    from tmt_quantum_vault.crypto.vault_encryptor import AESGCMEncryptor

    key = b"\x01" * 32
    plaintext = b"secret"
    with pytest.raises(ValueError, match="Nonce must be"):
        AESGCMEncryptor.encrypt(key, plaintext, nonce=b"too-short")  # type: ignore[arg-type]


def test_aesgcm_decrypt_rejects_wrong_nonce_length() -> None:
    """Wrong nonce length on decrypt → ValueError."""
    from tmt_quantum_vault.crypto.vault_encryptor import AESGCMEncryptor

    key = b"\x01" * 32
    nonce = b"\x02" * 12
    ciphertext = AESGCMEncryptor.encrypt(key, b"plaintext", nonce)
    with pytest.raises(ValueError, match="Nonce must be"):
        AESGCMEncryptor.decrypt(key, ciphertext, nonce=b"too-short")  # type: ignore[arg-type]


def test_aesgcm_encrypt_generates_nonce_when_none_provided() -> None:
    """Passing nonce=None causes encrypt to generate a random nonce."""
    from tmt_quantum_vault.crypto.vault_encryptor import AESGCMEncryptor

    key = b"\x01" * 32
    ct1 = AESGCMEncryptor.encrypt(key, b"msg", nonce=None)
    ct2 = AESGCMEncryptor.encrypt(key, b"msg", nonce=None)
    # Two calls produce different ciphertexts (different nonces).
    assert ct1 != ct2


def test_qrng_seed_fallback_when_entropy_file_missing(tmp_path: Path) -> None:
    """When entropy_stack does not exist, _load_qrng_seed falls back to secrets.token_bytes."""
    from tmt_quantum_vault.crypto.vault_encryptor import VaultEncryptor

    enc = VaultEncryptor(tmp_path)
    seed = enc._load_qrng_seed()
    assert len(seed) == 32
    assert isinstance(seed, bytes)


def test_qrng_seed_fallback_when_entropy_file_empty(tmp_path: Path) -> None:
    """When entropy_stack/three_layer_entropy_stack.json exists but has no bits."""
    from tmt_quantum_vault.crypto.vault_encryptor import VaultEncryptor

    (tmp_path / "entropy_stack").mkdir()
    (tmp_path / "entropy_stack" / "three_layer_entropy_stack.json").write_text(
        '{"layer_1_casablanca_qtrg": {}}', encoding="utf-8"
    )
    enc = VaultEncryptor(tmp_path)
    seed = enc._load_qrng_seed()
    assert len(seed) == 32


def test_encrypt_file_round_trip(tmp_path: Path) -> None:
    """encrypt_file + decrypt_file recovers the original bytes."""
    from tmt_quantum_vault.crypto.vault_encryptor import (
        VaultDecryptor,
        VaultEncryptor,
    )

    input_p = tmp_path / "plain.json"
    input_p.write_text('{"test": true}', encoding="utf-8")

    enc = VaultEncryptor(tmp_path)
    enc_path, sk = enc.encrypt_file(input_p)
    # Output is written as JSON with leading newline.
    content = enc_path.read_text(encoding="utf-8")
    assert '"ciphertext"' in content

    dec = VaultDecryptor()
    out_path = tmp_path / "decrypted.json"
    dec.decrypt_file(enc_path, sk, out_path)

    assert out_path.read_text(encoding="utf-8") == '{"test": true}'


def test_encrypt_file_custom_output_path(tmp_path: Path) -> None:
    """output_path parameter overrides the default .enc.json suffix."""
    from tmt_quantum_vault.crypto.vault_encryptor import VaultEncryptor

    input_p = tmp_path / "plain.json"
    input_p.write_text('{"custom": true}', encoding="utf-8")
    custom_out = tmp_path / "my_output.enc.json"

    enc = VaultEncryptor(tmp_path)
    enc_path, _sk = enc.encrypt_file(input_p, output_path=custom_out)
    assert enc_path == custom_out
    assert '"ciphertext"' in enc_path.read_text(encoding="utf-8")


def test_encrypt_evidence_ledger_raises_when_missing(tmp_path: Path) -> None:
    """encrypt_evidence_ledger raises FileNotFoundError when ledger is absent."""
    from tmt_quantum_vault.crypto.vault_encryptor import VaultEncryptor

    enc = VaultEncryptor(tmp_path)
    with pytest.raises(FileNotFoundError, match="Evidence ledger not found"):
        enc.encrypt_evidence_ledger()


def test_encrypt_directory(tmp_path: Path) -> None:
    """encrypt_directory encrypts all matching files in a directory."""
    from tmt_quantum_vault.crypto.vault_encryptor import VaultDecryptor, VaultEncryptor

    (tmp_path / "a.json").write_text('{"a":1}', encoding="utf-8")
    (tmp_path / "b.json").write_text('{"b":2}', encoding="utf-8")
    (tmp_path / "c.txt").write_text("not json", encoding="utf-8")

    enc = VaultEncryptor(tmp_path)
    results = enc.encrypt_directory(tmp_path, pattern="*.json")
    assert len(results) == 2

    dec = VaultDecryptor()
    for (enc_path, sk), orig_name in zip(results, ["a.json", "b.json"], strict=True):
        out = tmp_path / f"dec_{orig_name}"
        dec.decrypt_file(enc_path, sk, out)
        assert out.read_text(encoding="utf-8") in ['{"a":1}', '{"b":2}']


def test_decrypt_file_unknown_format_raises(tmp_path: Path) -> None:
    """decrypt_file raises when the JSON does not contain required fields."""
    from tmt_quantum_vault.crypto.vault_encryptor import VaultDecryptor

    bad = tmp_path / "bad.json"
    bad.write_text('{"wrong": "structure"}', encoding="utf-8")

    dec = VaultDecryptor()
    with pytest.raises((KeyError, TypeError)):
        dec.decrypt_file(bad, b"x" * 2400, tmp_path / "out.json")


def test_evidence_ledger_round_trip(tmp_path: Path) -> None:
    """End-to-end: encrypt and decrypt back to the same bytes.

    Uses the real evidence ledger when present; otherwise uses synthetic payload.
    """
    from tmt_quantum_vault.crypto.vault_encryptor import (
        VaultDecryptor,
        VaultEncryptor,
    )

    repo_root = Path(__file__).resolve().parent.parent
    plain_path = repo_root / "evidence_ledger" / "hardware_evidence_ledger_v2.json"
    original = (
        plain_path.read_bytes() if plain_path.is_file() else b'{"synthetic": true}\n'
    )

    input_p = tmp_path / "input.json"
    input_p.write_bytes(original)

    enc = VaultEncryptor(tmp_path)
    enc_path, sk = enc.encrypt_file(input_p)

    dec = VaultDecryptor()
    out_path = tmp_path / "input.dec.json"
    dec.decrypt_file(enc_path, sk, out_path)

    assert (
        hashlib.sha256(original).hexdigest()
        == hashlib.sha256(out_path.read_bytes()).hexdigest()
    )


# ══════════════════════════════════════════════════════════════════════════════
# MISSING-DEPENDENCY BEHAVIOR
# ══════════════════════════════════════════════════════════════════════════════


def test_kyber_encaps_raises_clear_error_without_cryptography(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When `cryptography` is missing, Kyber768.encaps raises a clear ImportError.

    This is the fix for F-004: previously, the missing-dep case silently
    downgraded to XOR. Now it must fail loudly.
    """
    # Force the inner import to fail by hiding the module.
    import tmt_quantum_vault.crypto.vault_encryptor as ve

    _ = ve.Kyber768.encaps  # type: ignore[attr-defined]  # ensure module loaded

    # Patch the *inner* `from cryptography...` import to raise ImportError.
    # The cleanest way: monkey-patch `sys.modules['cryptography']` to None,
    # then ensure the `except ImportError` branch is what we exercise.
    # However, `cryptography` is already imported elsewhere in this process.
    # So we test the actual import-failure path by using a sub-package.
    fake_module_name = "cryptography.hazmat.primitives.ciphers.aead"

    saved = sys.modules.get(fake_module_name)
    sys.modules[fake_module_name] = (
        None  # forces ImportError on `from ... import AESGCM`
    )
    try:
        pk, _sk = ve.Kyber768.keygen()
        with pytest.raises(ImportError) as exc_info:
            ve.Kyber768.encaps(pk)
        msg = str(exc_info.value)
        assert (
            "cryptography" in msg.lower()
        ), f"ImportError message should mention 'cryptography'; got: {msg!r}"
    finally:
        if saved is not None:
            sys.modules[fake_module_name] = saved
        else:
            sys.modules.pop(fake_module_name, None)


def test_kyber_decaps_raises_clear_error_without_cryptography(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When `cryptography` is missing, Kyber768.decaps raises a clear ImportError."""
    import tmt_quantum_vault.crypto.vault_encryptor as ve

    fake_module_name = "cryptography.hazmat.primitives.ciphers.aead"
    saved = sys.modules.get(fake_module_name)
    sys.modules[fake_module_name] = None
    try:
        _pk, sk = ve.Kyber768.keygen()
        # Build a dummy ciphertext of correct length to reach the import.
        ct = b"\x00" * ve.KYBER_CIPHERTEXT_SIZE
        with pytest.raises(ImportError) as exc_info:
            ve.Kyber768.decaps(ct, sk)
        msg = str(exc_info.value)
        assert (
            "cryptography" in msg.lower()
        ), f"ImportError message should mention 'cryptography'; got: {msg!r}"
    finally:
        if saved is not None:
            sys.modules[fake_module_name] = saved
        else:
            sys.modules.pop(fake_module_name, None)
