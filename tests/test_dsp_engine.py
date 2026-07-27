"""Tests for deterministic DSP processor contracts."""

from pathlib import Path

import numpy as np
import pytest

from packages.analysis_engine.metrics import integrated_lufs
from packages.analysis_engine.models import AnalysisResult
from packages.audio_core import decode_wav
from packages.dsp_engine import (
    AutomaticMasteringService,
    BassControlProcessor,
    DeEsserProcessor,
    DeterministicMasteringService,
    DspPipeline,
    DynamicEqualizerProcessor,
    GainProcessor,
    HighPassProcessor,
    LimiterProcessor,
    MasteringPolicy,
    MasteringSettings,
    OversampledClipperProcessor,
    SaturationProcessor,
    TonalEqualizerProcessor,
)


def test_gain_processor_scales_without_mutating_input() -> None:
    samples = np.full((8, 2), 0.25, dtype=np.float64)

    output = GainProcessor(6.0206).process(samples, 48_000)

    assert output == pytest.approx(np.full((8, 2), 0.5))
    assert samples == pytest.approx(np.full((8, 2), 0.25))


def test_pipeline_applies_processors_in_order() -> None:
    samples = np.ones((4, 1), dtype=np.float64)

    output = DspPipeline((GainProcessor(6.0206), GainProcessor(-6.0206))).process(samples, 48_000)

    assert output == pytest.approx(samples)


def test_gain_processor_rejects_invalid_audio() -> None:
    with pytest.raises(ValueError, match="shape"):
        GainProcessor(0.0).process(np.array([1.0]), 48_000)


def test_limiter_enforces_linked_stereo_ceiling() -> None:
    samples = np.tile(np.array([[2.0, 1.0]], dtype=np.float64), (2_000, 1))

    output = LimiterProcessor(-6.0206).process(samples, 48_000)

    assert np.max(np.abs(output)) <= 0.50001
    assert output[1_000, 1] / output[1_000, 0] == pytest.approx(0.5, abs=1e-4)


def test_limiter_rejects_ceiling_above_full_scale() -> None:
    with pytest.raises(ValueError, match="at or below"):
        LimiterProcessor(0.1)


def test_mastering_service_reports_deterministic_processor_order() -> None:
    samples = np.array([[1.0], [0.25]], dtype=np.float64)

    result = DeterministicMasteringService().master(
        samples,
        48_000,
        MasteringSettings(input_gain_db=6.0206, ceiling_dbfs=-1.0),
    )

    assert result.applied_processors == (
        "high_pass",
        "three_band_equalizer",
        "dynamic_equalizer",
        "bass_control",
        "de_esser",
        "gain",
        "saturation",
        "oversampled_clipper",
        "true_peak_limiter",
    )
    assert np.max(np.abs(result.samples)) <= 10 ** (-1.0 / 20.0)
    assert np.max(np.abs(result.samples)) > 0.0
    assert result.output_lufs is None
    assert result.output_true_peak_dbfs <= -1.0
    assert samples == pytest.approx(np.array([[1.0], [0.25]], dtype=np.float64))


def test_automatic_mastering_bounds_loudness_gain_and_records_decision() -> None:
    analysis = _analysis_result(lufs=-30.0)
    service = AutomaticMasteringService(MasteringPolicy(maximum_gain_adjustment_db=6.0))

    result = service.master(np.array([[0.25]], dtype=np.float64), 48_000, analysis)

    assert result.decision.requested_gain_db == pytest.approx(16.0)
    assert result.decision.settings.input_gain_db == pytest.approx(6.0)
    assert result.decision.gain_was_bounded is True
    assert result.decision.peak_headroom_gain_db == pytest.approx(2.0)
    assert result.decision.limited_by_peak_headroom is False
    assert result.render.applied_processors[-1] == "true_peak_limiter"


def test_tonal_equalizer_boosts_selected_frequency_without_mutating_input() -> None:
    sample_rate_hz = 48_000
    time = np.arange(sample_rate_hz) / sample_rate_hz
    samples = (0.1 * np.sin(2 * np.pi * 1_000 * time))[:, np.newaxis]

    output = TonalEqualizerProcessor(mid_gain_db=6.0).process(samples, sample_rate_hz)

    assert np.sqrt(np.mean(output**2)) > np.sqrt(np.mean(samples**2)) * 1.8
    assert np.max(np.abs(samples)) == pytest.approx(0.1)


def test_oversampled_clipper_is_bypassed_at_zero_and_controls_driven_peaks() -> None:
    samples = np.linspace(-1.0, 1.0, 4_800, dtype=np.float64)[:, np.newaxis]

    bypassed = OversampledClipperProcessor(0.0).process(samples, 48_000)
    clipped = OversampledClipperProcessor(6.0).process(samples, 48_000)

    assert np.array_equal(bypassed, samples)
    assert np.max(np.abs(clipped)) <= 1.01
    assert np.sqrt(np.mean(clipped**2)) < np.sqrt(np.mean(samples**2))
    assert clipped.shape == samples.shape


def test_oversampled_clipper_does_not_amplify_quiet_bass_fundamental() -> None:
    sample_rate_hz = 48_000
    time = np.arange(sample_rate_hz) / sample_rate_hz
    bass = (0.03 * np.sin(2 * np.pi * 60 * time))[:, np.newaxis]

    clipped = OversampledClipperProcessor(6.0).process(bass, sample_rate_hz)

    assert np.sqrt(np.mean(clipped**2)) <= np.sqrt(np.mean(bass**2)) * 1.01


def test_high_pass_rejects_subsonic_energy_and_preserves_audible_tone() -> None:
    sample_rate_hz = 48_000
    time = np.arange(sample_rate_hz * 2) / sample_rate_hz
    subsonic = np.sin(2 * np.pi * 8 * time)
    audible = np.sin(2 * np.pi * 1_000 * time)

    filtered_subsonic = HighPassProcessor(25.0).process(subsonic[:, np.newaxis], sample_rate_hz)
    filtered_audible = HighPassProcessor(25.0).process(audible[:, np.newaxis], sample_rate_hz)

    assert np.sqrt(np.mean(filtered_subsonic[-sample_rate_hz:] ** 2)) < 0.02
    assert np.sqrt(np.mean(filtered_audible[-sample_rate_hz:] ** 2)) > 0.69


@pytest.mark.parametrize(
    ("processor", "frequency_hz"),
    (
        (
            DynamicEqualizerProcessor(
                center_hz=2_500.0,
                threshold_dbfs=-30.0,
                maximum_reduction_db=6.0,
            ),
            2_500.0,
        ),
        (
            BassControlProcessor(
                crossover_hz=140.0,
                threshold_dbfs=-30.0,
                maximum_reduction_db=6.0,
            ),
            80.0,
        ),
        (
            DeEsserProcessor(
                center_hz=7_000.0,
                threshold_dbfs=-30.0,
                maximum_reduction_db=6.0,
            ),
            7_000.0,
        ),
    ),
)
def test_frequency_selective_dynamics_reduce_trigger_band(
    processor: DynamicEqualizerProcessor | BassControlProcessor | DeEsserProcessor,
    frequency_hz: float,
) -> None:
    sample_rate_hz = 48_000
    time = np.arange(sample_rate_hz) / sample_rate_hz
    samples = (0.5 * np.sin(2 * np.pi * frequency_hz * time))[:, np.newaxis]

    output = processor.process(samples, sample_rate_hz)

    assert np.sqrt(np.mean(output[-24_000:] ** 2)) < np.sqrt(np.mean(samples[-24_000:] ** 2))
    assert output.shape == samples.shape


def test_saturation_is_repeatable_bypassed_at_zero_and_changes_driven_signal() -> None:
    samples = np.linspace(-0.8, 0.8, 4_800, dtype=np.float64)[:, np.newaxis]

    bypassed = SaturationProcessor(0.0).process(samples, 48_000)
    first = SaturationProcessor(0.5).process(samples, 48_000)
    second = SaturationProcessor(0.5).process(samples, 48_000)

    assert np.array_equal(bypassed, samples)
    assert np.array_equal(first, second)
    assert not np.array_equal(first, samples)


def test_automatic_mastering_preserves_gain_when_loudness_is_unavailable() -> None:
    decision = AutomaticMasteringService().decide(_analysis_result(lufs=None))

    assert decision.settings.input_gain_db == 0.0
    assert decision.requested_gain_db is None
    assert decision.peak_headroom_gain_db is None
    assert "unavailable" in decision.reason


def test_automatic_mastering_keeps_loudness_gain_when_peak_has_sufficient_headroom() -> None:
    decision = AutomaticMasteringService().decide(_analysis_result(lufs=-18.0, peak_dbfs=-12.0))

    assert decision.settings.input_gain_db == pytest.approx(4.0)
    assert decision.peak_headroom_gain_db == pytest.approx(11.0)
    assert decision.limited_by_peak_headroom is False


def test_driven_master_increases_loudness_while_enforcing_true_peak_ceiling() -> None:
    sample_rate_hz = 48_000
    time = np.arange(sample_rate_hz * 3) / sample_rate_hz
    body = 0.12 * np.sin(2 * np.pi * 110 * time)
    transients = np.zeros_like(body)
    transients[::2_400] = 0.85
    samples = (body + transients)[:, np.newaxis]
    source_lufs = integrated_lufs(samples, sample_rate_hz)
    assert source_lufs is not None
    service = AutomaticMasteringService(
        MasteringPolicy(
            target_lufs=-9.0,
            maximum_gain_adjustment_db=12.0,
            ceiling_dbfs=-1.0,
            clipper_drive_db=2.0,
        )
    )

    mastered = service.master(
        samples,
        sample_rate_hz,
        _analysis_result(lufs=source_lufs, peak_dbfs=-1.4),
    )

    assert mastered.render.output_lufs is not None
    assert mastered.render.output_lufs > source_lufs
    assert mastered.render.output_true_peak_dbfs <= -1.0 + 1e-9


def test_automatic_mastering_is_repeatable_safe_and_reaches_target_when_unbounded() -> None:
    sample_rate_hz = 48_000
    time = np.arange(sample_rate_hz * 5) / sample_rate_hz
    samples = (0.1 * np.sin(2 * np.pi * 1_000 * time))[:, np.newaxis]
    policy = MasteringPolicy(target_lufs=-14.0)
    analysis = _analysis_result(
        lufs=integrated_lufs(samples, sample_rate_hz),
        peak_dbfs=-20.0,
    )
    service = AutomaticMasteringService(policy)

    first = service.master(samples, sample_rate_hz, analysis)
    second = service.master(samples, sample_rate_hz, analysis)

    assert first.decision.policy == policy
    assert first.decision.gain_was_bounded is False
    assert first.render.output_lufs == pytest.approx(policy.target_lufs, abs=0.1)
    assert np.array_equal(first.render.samples, second.render.samples)
    assert np.max(np.abs(first.render.samples)) <= 10 ** (policy.ceiling_dbfs / 20.0)
    assert integrated_lufs(first.render.samples, sample_rate_hz) == pytest.approx(
        policy.target_lufs, abs=0.1
    )


def test_automatic_mastering_exports_auditable_wav(tmp_path: Path) -> None:
    output_path = tmp_path / "master.wav"

    exported = AutomaticMasteringService().master_to_wav(
        np.array([[0.25], [-0.25]], dtype=np.float64),
        48_000,
        _analysis_result(lufs=-18.0, peak_dbfs=-12.0),
        output_path,
    )

    decoded = decode_wav(output_path)

    assert exported.output_path == output_path
    assert exported.dither_applied is True
    assert exported.mastering.decision.settings.input_gain_db == pytest.approx(4.0)
    assert decoded.samples == pytest.approx(exported.mastering.render.samples, abs=2.5e-7)


def _analysis_result(lufs: float | None, peak_dbfs: float = -3.0) -> AnalysisResult:
    return AnalysisResult(
        duration_seconds=1.0,
        sample_rate_hz=48_000,
        bit_depth=24,
        channels=2,
        lufs=lufs,
        rms_dbfs=-18.0,
        peak_dbfs=peak_dbfs,
        true_peak_dbfs=-3.0,
        dynamic_range_db=9.0,
        crest_factor_db=6.0,
        bpm=None,
        musical_key=None,
        stereo_width=0.5,
        phase_correlation=1.0,
        spectral_centroid_hz=1_000.0,
    )
