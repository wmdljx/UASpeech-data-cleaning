"""Small waveform retrieval example based on historical normalized correlation.

Candidates are NOT automatically approved frame-index changes. The original
workflow also checked multiple recordings, word order and human decisions.
"""
from __future__ import annotations

import math
import numpy as np
from scipy import signal

MATCH_SR = 4000


def standardize_resample(value, sample_rate):
    value = np.asarray(value, dtype=np.float32)
    if value.ndim != 1 or not len(value) or sample_rate <= 0 or not np.isfinite(value).all():
        raise ValueError("Expected finite nonempty mono audio and positive sample rate")
    if sample_rate != MATCH_SR:
        divisor = math.gcd(int(sample_rate), MATCH_SR)
        value = signal.resample_poly(value, MATCH_SR // divisor, int(sample_rate) // divisor)
    output = np.asarray(value, dtype=np.float32).copy()
    output -= float(np.mean(output))
    deviation = float(np.std(output))
    return np.zeros_like(output) if deviation < 1e-8 else output / deviation


def candidates(reference, query, start_s=0.0, end_s=None, k=5):
    """Both inputs have already been resampled to MATCH_SR (4 kHz).

    start_s/end_s bound candidate STARTS in the decoded reference waveform,
    not video PTS. Scores are absolute, polarity-tolerant Pearson correlation.
    """
    reference, query = np.asarray(reference), np.asarray(query)
    if reference.ndim != 1 or query.ndim != 1 or not np.isfinite(reference).all() or not np.isfinite(query).all():
        raise ValueError("Expected finite one-dimensional waveforms")
    if k < 1 or len(query) < 2:
        return []
    start = max(0, int(round(float(start_s) * MATCH_SR)))
    last = len(reference) - len(query)
    end = last if end_s is None else min(last, int(round(float(end_s) * MATCH_SR)))
    if end < start:
        return []
    region = np.asarray(reference[start:end + len(query)], dtype=np.float64)
    q = np.asarray(query, dtype=np.float64).copy()
    q -= q.mean()
    query_energy = float(np.dot(q, q))
    if query_energy < 1e-8:
        return []
    numerator = signal.fftconvolve(region, q[::-1], mode="valid")
    cumulative = np.r_[0.0, np.cumsum(region)]
    cumulative2 = np.r_[0.0, np.cumsum(region * region)]
    length = len(q)
    sums = cumulative[length:] - cumulative[:-length]
    sums2 = cumulative2[length:] - cumulative2[:-length]
    energy = np.maximum(sums2 - sums * sums / length, 1e-8)
    correlation = np.clip(numerator / np.sqrt(energy * query_energy), -1, 1)
    objective = np.abs(correlation)
    peaks, _ = signal.find_peaks(objective, distance=round(0.5 * MATCH_SR))
    indices = {int(index) for index in peaks}
    indices.add(int(np.argmax(objective)))
    ranked = sorted(indices, key=lambda index: float(objective[index]), reverse=True)[:k]
    return [dict(rank=rank, camera_audio_start_s=(start + index) / MATCH_SR,
                 correlation=float(correlation[index]), score=float(objective[index]))
            for rank, index in enumerate(ranked, start=1)]

