#!/usr/bin/env python3
"""Build and validate a deliberately tiny, safe subset of a GGUF file.

This is a format-learning fixture, not a model converter or a general GGUF
loader.  It accepts only the exact subset written by ``build_toy_gguf``:
GGUF v3, two known metadata value types, and F32 tensors.  Its bounded parser
is intentionally useful for checking header, metadata, tensor offsets, and
alignment without downloading or opening a real model.
"""

from __future__ import annotations

import argparse
import math
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final


MAGIC: Final[bytes] = b"GGUF"
VERSION: Final[int] = 3
VALUE_TYPE_UINT32: Final[int] = 4
VALUE_TYPE_STRING: Final[int] = 8
GGML_TYPE_F32: Final[int] = 0
MAX_FILE_BYTES: Final[int] = 1 << 20
MAX_COUNT: Final[int] = 32
MAX_STRING_BYTES: Final[int] = 4096


class FormatError(ValueError):
    """Raised when a fixture violates this teaching parser's strict subset."""


@dataclass(frozen=True)
class TensorInfo:
    name: str
    shape: tuple[int, ...]
    ggml_type: int
    offset: int
    byte_length: int


@dataclass(frozen=True)
class ToyGguf:
    version: int
    metadata: dict[str, int | str]
    tensors: tuple[TensorInfo, ...]
    data_offset: int
    byte_length: int


class Reader:
    """A length-bounded little-endian reader with explicit size limits."""

    def __init__(self, payload: bytes) -> None:
        if len(payload) > MAX_FILE_BYTES:
            raise FormatError(f"fixture exceeds {MAX_FILE_BYTES} bytes")
        self.payload = payload
        self.position = 0

    def take(self, size: int) -> bytes:
        if size < 0 or self.position + size > len(self.payload):
            raise FormatError("truncated field")
        result = self.payload[self.position : self.position + size]
        self.position += size
        return result

    def u32(self) -> int:
        return struct.unpack("<I", self.take(4))[0]

    def u64(self) -> int:
        return struct.unpack("<Q", self.take(8))[0]

    def string(self) -> str:
        size = self.u64()
        if size > MAX_STRING_BYTES:
            raise FormatError(f"string is larger than {MAX_STRING_BYTES} bytes")
        try:
            return self.take(size).decode("utf-8")
        except UnicodeDecodeError as error:
            raise FormatError("string is not valid UTF-8") from error


def append_string(buffer: bytearray, value: str) -> None:
    encoded = value.encode("utf-8")
    buffer.extend(struct.pack("<Q", len(encoded)))
    buffer.extend(encoded)


def append_metadata_string(buffer: bytearray, key: str, value: str) -> None:
    append_string(buffer, key)
    buffer.extend(struct.pack("<I", VALUE_TYPE_STRING))
    append_string(buffer, value)


def append_metadata_u32(buffer: bytearray, key: str, value: int) -> None:
    append_string(buffer, key)
    buffer.extend(struct.pack("<I", VALUE_TYPE_UINT32))
    buffer.extend(struct.pack("<I", value))


def align_up(value: int, alignment: int) -> int:
    if alignment < 8 or alignment > 4096 or alignment & (alignment - 1):
        raise ValueError("alignment must be a power of two from 8 through 4096")
    return (value + alignment - 1) & -alignment


def build_toy_gguf() -> bytes:
    """Return one deterministic, valid-for-this-lesson GGUF v3 byte string."""
    alignment = 32
    values = (-1.0, -0.25, 0.5, 1.25)
    buffer = bytearray()
    buffer.extend(MAGIC)
    buffer.extend(struct.pack("<IQQ", VERSION, 1, 2))
    append_metadata_string(buffer, "general.architecture", "toy")
    append_metadata_u32(buffer, "general.alignment", alignment)
    append_string(buffer, "toy.weight")
    buffer.extend(struct.pack("<I", 1))
    buffer.extend(struct.pack("<Q", len(values)))
    buffer.extend(struct.pack("<IQ", GGML_TYPE_F32, 0))
    data_offset = align_up(len(buffer), alignment)
    buffer.extend(b"\x00" * (data_offset - len(buffer)))
    buffer.extend(struct.pack("<4f", *values))
    return bytes(buffer)


def checked_product(shape: tuple[int, ...]) -> int:
    result = 1
    for dimension in shape:
        if not 1 <= dimension <= 4096:
            raise FormatError("tensor dimension is outside the fixture limit")
        result *= dimension
        if result > MAX_FILE_BYTES // 4:
            raise FormatError("tensor element count is too large")
    return result


def parse_toy_gguf(payload: bytes) -> ToyGguf:
    """Parse and validate only the documented toy subset; never execute data."""
    reader = Reader(payload)
    if reader.take(4) != MAGIC:
        raise FormatError("not a GGUF magic value")
    version = reader.u32()
    if version != VERSION:
        raise FormatError(f"expected GGUF v{VERSION}, found v{version}")
    tensor_count = reader.u64()
    metadata_count = reader.u64()
    if not 1 <= tensor_count <= MAX_COUNT or metadata_count > MAX_COUNT:
        raise FormatError("unreasonable tensor or metadata count")

    metadata: dict[str, int | str] = {}
    for _ in range(metadata_count):
        key = reader.string()
        if not key or key in metadata:
            raise FormatError("metadata key is empty or duplicated")
        value_type = reader.u32()
        if value_type == VALUE_TYPE_STRING:
            value: int | str = reader.string()
        elif value_type == VALUE_TYPE_UINT32:
            value = reader.u32()
        else:
            raise FormatError(f"unsupported metadata value type {value_type}")
        metadata[key] = value

    architecture = metadata.get("general.architecture")
    alignment = metadata.get("general.alignment")
    if architecture != "toy":
        raise FormatError("toy fixture requires general.architecture=toy")
    if not isinstance(alignment, int):
        raise FormatError("toy fixture needs an integer general.alignment")
    tensor_info_start = reader.position
    try:
        data_offset = align_up(tensor_info_start + _tensor_info_size(reader, tensor_count), alignment)
    except ValueError as error:
        raise FormatError(str(error)) from error

    # Re-read tensor infos after calculating their exact fixed/variable length.
    # A second bounded Reader avoids speculative offsets into tensor data.
    tensor_reader = Reader(payload)
    tensor_reader.position = tensor_info_start
    tensors: list[TensorInfo] = []
    for _ in range(tensor_count):
        name = tensor_reader.string()
        ndim = tensor_reader.u32()
        if not 1 <= ndim <= 4:
            raise FormatError("toy tensors need one through four dimensions")
        shape = tuple(tensor_reader.u64() for _ in range(ndim))
        ggml_type = tensor_reader.u32()
        relative_offset = tensor_reader.u64()
        if not name or ggml_type != GGML_TYPE_F32:
            raise FormatError("toy fixture accepts named F32 tensors only")
        byte_length = checked_product(shape) * 4
        tensors.append(TensorInfo(name, shape, ggml_type, relative_offset, byte_length))
    if tensor_reader.position > data_offset:
        raise FormatError("tensor information overlaps aligned data")

    ranges: list[tuple[int, int]] = []
    for tensor in tensors:
        if tensor.offset % alignment:
            raise FormatError(f"tensor {tensor.name!r} offset is not aligned to {alignment} bytes")
        start = data_offset + tensor.offset
        end = start + tensor.byte_length
        if start < data_offset or end > len(payload):
            raise FormatError(f"tensor {tensor.name!r} points outside the file")
        ranges.append((start, end))
    if any(right[0] < left[1] for left, right in zip(sorted(ranges), sorted(ranges)[1:])):
        raise FormatError("tensor byte ranges overlap")

    return ToyGguf(version, metadata, tuple(tensors), data_offset, len(payload))


def _tensor_info_size(reader: Reader, tensor_count: int) -> int:
    """Measure tensor infos without trusting their offsets or materializing them."""
    start = reader.position
    for _ in range(tensor_count):
        reader.string()
        ndim = reader.u32()
        if not 1 <= ndim <= 4:
            raise FormatError("toy tensors need one through four dimensions")
        reader.take(8 * ndim + 4 + 8)
    return reader.position - start


def symmetric_int4_error(values: tuple[float, ...]) -> dict[str, float]:
    """Return deterministic error metrics for a simple teaching-only 4-bit grid."""
    if not values or not all(math.isfinite(value) for value in values):
        raise ValueError("values must be non-empty finite numbers")
    scale = max(abs(value) for value in values) / 7.0 or 1.0
    reconstructed = tuple(max(-7, min(7, round(value / scale))) * scale for value in values)
    errors = tuple(approximation - reference for reference, approximation in zip(values, reconstructed))
    return {
        "scale": scale,
        "mae": sum(abs(error) for error in errors) / len(errors),
        "max_abs": max(abs(error) for error in errors),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        type=Path,
        help="write the toy fixture only to a path that does not already exist",
    )
    args = parser.parse_args(argv)
    payload = build_toy_gguf()
    parsed = parse_toy_gguf(payload)
    metrics = symmetric_int4_error((-1.0, -0.25, 0.5, 1.25))
    print(f"toy GGUF: {parsed.byte_length} bytes; data starts at byte {parsed.data_offset}")
    print(f"metadata: {parsed.metadata}")
    print(f"tensor: {parsed.tensors[0].name} shape={parsed.tensors[0].shape} offset=0")
    print("teaching-only symmetric INT4: " + ", ".join(f"{key}={value:.6f}" for key, value in metrics.items()))
    if args.write is not None:
        destination = args.write
        if not destination.parent.is_dir():
            parser.error("--write parent directory must already exist")
        if destination.exists() or destination.is_symlink():
            parser.error("refusing to overwrite or replace an existing path")
        destination.write_bytes(payload)
        print(f"wrote new toy fixture: {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
