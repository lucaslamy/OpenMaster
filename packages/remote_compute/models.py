"""Validated, JSON-safe contracts shared with the RunPod worker."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from urllib.parse import urlsplit


def _validate_https_url(value: str, field: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError(f"{field} must be an HTTPS URL without embedded credentials")


@dataclass(frozen=True, slots=True)
class RemoteMasteringRequest:
    """One bounded mastering job using short-lived signed object-storage URLs."""

    source_url: str
    destination_url: str
    source_sha256: str
    target_lufs: float = -14.0
    maximum_gain_adjustment_db: float = 12.0
    ceiling_dbfs: float = -1.0
    eq_low_gain_db: float = 0.0
    eq_mid_gain_db: float = 0.0
    eq_high_gain_db: float = 0.0
    clipper_drive_db: float = 0.0
    limiter_lookahead_ms: float = 3.0
    limiter_release_ms: float = 80.0
    high_pass_enabled: bool = True
    high_pass_cutoff_hz: float = 25.0
    dynamic_eq_reduction_db: float = 0.0
    bass_control_reduction_db: float = 0.0
    de_esser_reduction_db: float = 0.0
    saturation_amount: float = 0.0
    bit_depth: int = 24

    def __post_init__(self) -> None:
        _validate_https_url(self.source_url, "source_url")
        _validate_https_url(self.destination_url, "destination_url")
        if len(self.source_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.source_sha256
        ):
            raise ValueError("source_sha256 must be a lowercase SHA-256 digest")
        if not all(
            math.isfinite(value)
            for value in (
                self.target_lufs,
                self.maximum_gain_adjustment_db,
                self.ceiling_dbfs,
                self.eq_low_gain_db,
                self.eq_mid_gain_db,
                self.eq_high_gain_db,
                self.clipper_drive_db,
                self.limiter_lookahead_ms,
                self.limiter_release_ms,
                self.high_pass_cutoff_hz,
                self.dynamic_eq_reduction_db,
                self.bass_control_reduction_db,
                self.de_esser_reduction_db,
                self.saturation_amount,
            )
        ):
            raise ValueError("Mastering policy values must be finite")
        if self.maximum_gain_adjustment_db < 0 or self.ceiling_dbfs > 0:
            raise ValueError("Remote mastering policy is outside safe bounds")
        if any(
            not -6.0 <= gain <= 6.0
            for gain in (self.eq_low_gain_db, self.eq_mid_gain_db, self.eq_high_gain_db)
        ):
            raise ValueError("Remote equalizer gains are outside safe bounds")
        if not 0.0 <= self.clipper_drive_db <= 12.0:
            raise ValueError("Remote clipper drive is outside safe bounds")
        if not 0.0 <= self.limiter_lookahead_ms <= 10.0:
            raise ValueError("Remote limiter lookahead is outside safe bounds")
        if not 10.0 <= self.limiter_release_ms <= 500.0:
            raise ValueError("Remote limiter release is outside safe bounds")
        if not 15.0 <= self.high_pass_cutoff_hz <= 80.0:
            raise ValueError("Remote high-pass cutoff is outside safe bounds")
        if any(
            not 0.0 <= reduction <= 12.0
            for reduction in (
                self.dynamic_eq_reduction_db,
                self.bass_control_reduction_db,
                self.de_esser_reduction_db,
            )
        ):
            raise ValueError("Remote selective dynamics are outside safe bounds")
        if not 0.0 <= self.saturation_amount <= 1.0:
            raise ValueError("Remote saturation amount is outside safe bounds")
        if self.bit_depth not in (16, 24, 32):
            raise ValueError("bit_depth must be 16, 24, or 32")

    def to_dict(self) -> dict[str, object]:
        """Return the exact RunPod handler input."""
        return asdict(self)
