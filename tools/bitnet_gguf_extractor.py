#!/usr/bin/env python3
"""
BitNetGGUF Extractor

Extracts information and entropy from BitNet GGUF model files.
BitNet uses 1-bit quantization with weights constrained to {-1, 0, +1}.

This tool connects the BitNet model to your vault's DNA-to-qubit pipeline,
providing quantum-sourced entropy for agent DNA generation.

Usage:
    python bitnet_gguf_extractor.py --model <path> --output <output.json>
"""

import json
import struct
import sys
from pathlib import Path
from typing import Any, Optional

import numpy as np


def parse_gguf_header(data: bytes) -> dict[str, Any]:
    """Parse GGUF header to get metadata and offsets."""
    # GGUF magic: 'GGUF'
    if data[:4] != b'GGUF':
        raise ValueError("Not a valid GGUF file")

    header = {}
    idx = 4

    # GGUF version (uint32)
    version = struct.unpack('<I', data[idx:idx+4])[0]
    header['version'] = version
    idx += 4

    # Tensor count (uint64)
    tensor_count = struct.unpack('<Q', data[idx:idx+8])[0]
    header['tensor_count'] = tensor_count
    idx += 8

    # KV count (uint64)
    kv_count = struct.unpack('<Q', data[idx:idx+8])[0]
    header['kv_count'] = kv_count
    idx += 8

    return header


def read_gguf_kv_pair(data: bytes, idx: int) -> tuple[str, Any, int]:
    """Read a single key-value pair from GGUF data."""
    # Key string length (uint64)
    key_len = struct.unpack('<Q', data[idx:idx+8])[0]
    idx += 8

    # Key string (bytes)
    key = data[idx:idx+key_len].decode('utf-8')
    idx += key_len

    # Value type (uint32)
    value_type = struct.unpack('<I', data[idx:idx+4])[0]
    idx += 4

    # Read value based on type
    # Type codes from GGUF spec
    VALUE_TYPES = {
        0: 'uint8',
        1: 'int8',
        2: 'uint16',
        3: 'int16',
        4: 'uint32',
        5: 'int32',
        6: 'float32',
        7: 'bool',
        8: 'string',
        9: 'array',
        10: 'uint64',
        11: 'int64',
        12: 'float64',
        13: 'bool',
    }

    value_type_name = VALUE_TYPES.get(value_type, 'unknown')

    if value_type_name == 'uint8':
        value = struct.unpack('<B', data[idx:idx+1])[0]
        idx += 1
    elif value_type_name == 'int8':
        value = struct.unpack('<b', data[idx:idx+1])[0]
        idx += 1
    elif value_type_name == 'uint16':
        value = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2
    elif value_type_name == 'int16':
        value = struct.unpack('<h', data[idx:idx+2])[0]
        idx += 2
    elif value_type_name == 'uint32':
        value = struct.unpack('<I', data[idx:idx+4])[0]
        idx += 4
    elif value_type_name == 'int32':
        value = struct.unpack('<i', data[idx:idx+4])[0]
        idx += 4
    elif value_type_name == 'float32':
        value = struct.unpack('<f', data[idx:idx+4])[0]
        idx += 4
    elif value_type_name == 'bool':
        value = struct.unpack('<B', data[idx:idx+1])[0] == 1
        idx += 1
    elif value_type_name == 'string':
        str_len = struct.unpack('<Q', data[idx:idx+8])[0]
        idx += 8
        value = data[idx:idx+str_len].decode('utf-8')
        idx += str_len
    elif value_type_name == 'uint64':
        value = struct.unpack('<Q', data[idx:idx+8])[0]
        idx += 8
    elif value_type_name == 'int64':
        value = struct.unpack('<q', data[idx:idx+8])[0]
        idx += 8
    elif value_type_name == 'float64':
        value = struct.unpack('<d', data[idx:idx+8])[0]
        idx += 8
    else:
        value = None

    return key, value, idx


def extract_model_info(model_path: str) -> dict[str, Any]:
    """Extract information from BitNet GGUF model."""
    with open(model_path, 'rb') as f:
        data = f.read(4096)  # Read first 4KB for header

    header = parse_gguf_header(data)

    # Read more data for KV pairs
    with open(model_path, 'rb') as f:
        data = f.read(16384)  # Read more for KV pairs

    kv_pairs = {}
    idx = 4 + 8 + 8  # Skip magic + tensor_count + kv_count

    try:
        while idx < len(data) - 12:
            try:
                key, value, new_idx = read_gguf_kv_pair(data, idx)
                kv_pairs[key] = value
                idx = new_idx
            except Exception:
                break
    except Exception:
        pass

    # Try to extract tensor info
    tensor_info = {}
    try:
        # Look for specific keys that indicate BitNet properties
        if 'bitnet' in str(kv_pairs).lower() or 'ternary' in str(kv_pairs).lower():
            tensor_info['ternary_weights'] = True

        # Look for model parameters
        for key, value in kv_pairs.items():
            if 'context_length' in key or 'rope.freq_base' in key:
                tensor_info['context_length'] = value
            if 'embedding_length' in key:
                tensor_info['embedding_length'] = value
    except Exception:
        pass

    return {
        'model_path': model_path,
        'gguf_version': header.get('version'),
        'tensor_count': header.get('tensor_count'),
        'kv_count': header.get('kv_count'),
        'kv_pairs': kv_pairs,
        'tensor_info': tensor_info,
    }


def extract_ternary_weights(model_path: str, n_weights: int = 10000) -> dict[str, Any]:
    """
    Extract ternary weights from BitNet GGUF as quantum entropy source.
    Returns normalized array suitable for agent DNA seeding.

    BitNet weights are stored as ternary values {-1, 0, +1} after quantization.
    """
    with open(model_path, 'rb') as f:
        # Read entire file for weight extraction
        data = f.read()

    # GGUF weight data typically starts after header (first ~4KB)
    # The actual weight data is at the end of the file

    # Try to find weight data by looking for patterns
    weight_data_start = 4096  # Typical weight start offset

    if len(data) < weight_data_start + n_weights * 4:
        # Not enough data, try reading from end
        weight_data_start = max(0, len(data) - n_weights * 4 - 1024)

    # Read raw weight bytes
    weight_bytes = data[weight_data_start:weight_data_start + n_weights * 4]

    if len(weight_bytes) < n_weights * 4:
        # Pad if needed
        weight_bytes = weight_bytes + b'\x00' * (n_weights * 4 - len(weight_bytes))

    # Try to interpret as float32
    try:
        weights = np.frombuffer(weight_bytes, dtype=np.float32)[:n_weights]
    except Exception:
        weights = np.zeros(n_weights)

    # Ternary quantization: snap to {-1, 0, +1}
    # For BitNet, we expect mostly ternary values after dequantization
    ternary = np.sign(weights).astype(int)

    # Handle zeros from sign (sign(0) = 0)
    # We want {-1, 0, +1} distribution
    zero_mask = np.abs(weights) < 0.01
    ternary = np.where(zero_mask, 0, np.sign(weights))

    # Normalize to [0, 1] for agent DNA seeding
    # Maps: -1 -> 0, 0 -> 0.5, +1 -> 1
    normalized = (ternary + 1) / 2.0

    return {
        'source': 'bitnet_b158_ternary_weights',
        'n_weights': len(ternary),
        'minus_one_ratio': float(np.mean(ternary == -1)),
        'zero_ratio': float(np.mean(ternary == 0)),
        'plus_one_ratio': float(np.mean(ternary == 1)),
        'entropy_seed': float(np.mean(normalized)),
        'phi_seed': float(np.std(normalized)),
        'gc_seed': float(np.mean(normalized[:1000])),
        'resonance_seed': float(np.mean(normalized[1000:2000])),
        'weight_distribution': {
            'min': float(np.min(weights)),
            'max': float(np.max(weights)),
            'mean': float(np.mean(weights)),
            'std': float(np.std(weights)),
        },
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract BitNet GGUF information and entropy"
    )
    parser.add_argument(
        "--model", "-m",
        required=True,
        help="Path to BitNet GGUF model file",
    )
    parser.add_argument(
        "--output", "-o",
        default="./bitnet_info.json",
        help="Output JSON file",
    )
    parser.add_argument(
        "--n-weights", "-n",
        type=int,
        default=10000,
        help="Number of weights to extract for entropy",
    )
    parser.add_argument(
        "--extract", "-e",
        action="store_true",
        help="Extract ternary weights for entropy",
    )

    args = parser.parse_args()

    model_path = Path(args.model)

    if not model_path.exists():
        print(f"Error: Model file not found: {model_path}")
        sys.exit(1)

    print(f"Processing BitNet GGUF: {model_path}")

    # Extract model info
    print("Extracting model info...")
    model_info = extract_model_info(str(model_path))
    print(f"  GGUF version: {model_info['gguf_version']}")
    print(f"  Tensor count: {model_info['tensor_count']}")
    print(f"  KV pairs: {model_info['kv_count']}")

    # Extract weights if requested
    if args.extract:
        print(f"\nExtracting {args.n_weights} ternary weights...")
        weights = extract_ternary_weights(str(model_path), args.n_weights)
        model_info['ternary_weights'] = weights

        print(f"  -1 ratio: {weights['minus_one_ratio']:.4f}")
        print(f"  0 ratio: {weights['zero_ratio']:.4f}")
        print(f"  +1 ratio: {weights['plus_one_ratio']:.4f}")
        print(f"  Entropy seed: {weights['entropy_seed']:.4f}")

    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(model_info, f, indent=2)

    print(f"\nOutput saved to: {output_path}")


if __name__ == "__main__":
    main()
