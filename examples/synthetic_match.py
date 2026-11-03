"""Tiny, reproducible NCC example. Synthetic signals only; no UASpeech content."""
import numpy as np
from uaspeech_cut.matching import candidates

rate = 4000
rng = np.random.default_rng(3407)
query = rng.normal(size=rate) * np.hanning(rate)
reference = rng.normal(scale=0.04, size=5 * rate)
true_start_s = 2.18
start = round(true_start_s * rate)
reference[start:start + len(query)] += 0.65 * query

matches = candidates(reference, query, 1.5, 3.0)
best = matches[0]
print(f"Known start: {true_start_s:.3f} s")
print(f"Retrieved start: {best['camera_audio_start_s']:.3f} s")
print(best)
assert abs(best['camera_audio_start_s'] - true_start_s) <= 1 / rate
