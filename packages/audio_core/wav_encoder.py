"""Safe deterministic PCM WAV export for normalized audio samples."""

from __future__ import annotations

import os
import tempfile
import wave
from pathlib import Path

import numpy as np

from .models import FloatSamples

_SUPPORTED_BIT_DEPTHS = frozenset({16, 24, 32})


def encode_wav(
    path: str | Path,
    samples: FloatSamples,
    sample_rate_hz: int,
    *,
    bit_depth: int = 24,
    dither: bool = False,
    overwrite: bool = False,
) -> Path:
    """Atomically write finite normalized samples as an integer PCM WAV file.

    Samples must be two-dimensional in ``[-1, 1]``. Existing files are protected by
    default; callers must explicitly opt in to replacement.
    """
    destination = Path(path)
    _validate_export(destination, samples, sample_rate_hz, bit_depth, overwrite)
    encoded = _encode_pcm(samples, bit_depth, dither=dither)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{destination.stem}.",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        with wave.open(str(temporary_path), "wb") as output:
            output.setnchannels(samples.shape[1])
            output.setsampwidth(bit_depth // 8)
            output.setframerate(sample_rate_hz)
            output.writeframes(encoded)
        os.replace(temporary_path, destination)
    except OSError as error:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise OSError(f"Unable to write WAV output: {destination}") from error
    return destination


def _validate_export(
    destination: Path,
    samples: FloatSamples,
    sample_rate_hz: int,
    bit_depth: int,
    overwrite: bool,
) -> None:
    """Validate output and audio contracts before any temporary file is created."""
    if destination.suffix.lower() not in {".wav", ".wave"}:
        raise ValueError("WAV output path must use a .wav or .wave suffix")
    if not destination.parent.is_dir():
        raise ValueError("WAV output directory does not exist")
    if destination.exists() and not overwrite:
        raise FileExistsError(f"WAV output already exists: {destination}")
    if bit_depth not in _SUPPORTED_BIT_DEPTHS:
        raise ValueError("WAV output bit depth must be 16, 24, or 32")
    if sample_rate_hz < 1:
        raise ValueError("WAV output sample rate must be positive")
    if samples.ndim != 2 or samples.shape[0] < 1 or samples.shape[1] < 1:
        raise ValueError("WAV output samples must have shape (frames, channels)")
    if not np.isfinite(samples).all() or np.max(np.abs(samples)) > 1.0:
        raise ValueError("WAV output samples must be finite and normalized to [-1, 1]")


def _encode_pcm(samples: FloatSamples, bit_depth: int, *, dither: bool = False) -> bytes:
    """Quantize samples with optional deterministic TPDF dither."""
    scale = (1 << (bit_depth - 1)) - 1
    prepared = np.asarray(samples, dtype=np.float64)
    if dither:
        generator = np.random.default_rng(0)
        triangular = generator.random(prepared.shape) - generator.random(prepared.shape)
        prepared = prepared + triangular / scale
    quantized = np.rint(np.clip(prepared, -1.0, 1.0) * scale).astype(np.int32)
    if bit_depth == 16:
        return quantized.astype("<i2").tobytes()
    if bit_depth == 32:
        return quantized.astype("<i4").tobytes()
    packed = quantized.reshape(-1, 1).astype("<i4").view(np.uint8)[:, :3]
    return packed.tobytes()
