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


def test_kyber768_keygen_produces_correctly_sized_keys() -> None:
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
    assert shared_enc == shared_dec, "decaps did not recover the encapsulated shared key"
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


def test_evidence_ledger_round_trip() -> None:
    """End-to-end: encrypt the evidence ledger and decrypt back to the same bytes.

    Uses the real plaintext at evidence_ledger/hardware_evidence_ledger_v2.json
    when present; otherwise uses a small synthetic payload.
    """
    from tmt_quantum_vault.crypto.vault_encryptor import (
        VaultDecryptor,
        VaultEncryptor,
    )

    repo_root = Path(__file__).resolve().parent.parent
    plain_path = repo_root / "evidence_ledger" / "hardware_evidence_ledger_v2.json"
    if plain_path.is_file():
        original = plain_path.read_bytes()
    else:
        original = b'{"synthetic": true}\n'

    tmp = repo_root / "tests" / "_tmp_round_trip"
    tmp.mkdir(exist_ok=True)
    try:
        enc = VaultEncryptor(tmp)
        enc_path, sk = enc.encrypt_evidence_ledger.__self__.encrypt_file(  # type: ignore[attr-defined]
            tmp / "input.json", tmp / "input.enc.json"
        ) if False else (None, None)
        # Use the public encrypt_file method directly.
        input_p = tmp / "input.json"
        input_p.write_bytes(original)
        enc = VaultEncryptor(tmp)
        enc_path, sk = enc.encrypt_file(input_p)

        # Decrypt
        dec = VaultDecryptor()
        out_path = tmp / "input.dec.json"
        dec.decrypt_file(enc_path, sk, out_path)

        recovered = out_path.read_bytes()
        assert hashlib.sha256(original).hexdigest() == hashlib.sha256(recovered).hexdigest()
    finally:
        # Cleanup
        for child in tmp.iterdir():
            if child.name == "_tmp_round_trip" or child.is_dir():
                continue
            try:
                child.unlink()
            except OSError:
                pass
        try:
            tmp.rmdir()
        except OSError:
            pass


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
    sys.modules[fake_module_name] = None  # forces ImportError on `from ... import AESGCM`
    try:
        pk, _sk = ve.Kyber768.keygen()
        with pytest.raises(ImportError) as exc_info:
            ve.Kyber768.encaps(pk)
        msg = str(exc_info.value)
        assert "cryptography" in msg.lower(), (
            f"ImportError message should mention 'cryptography'; got: {msg!r}"
        )
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
        assert "cryptography" in msg.lower(), (
            f"ImportError message should mention 'cryptography'; got: {msg!r}"
        )
    finally:
        if saved is not None:
            sys.modules[fake_module_name] = saved
        else:
            sys.modules.pop(fake_module_name, None)
