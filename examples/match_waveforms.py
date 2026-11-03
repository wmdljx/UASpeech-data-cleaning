"""Illustrative search, not an automatic replacement for approved frame indices.

Usage: python examples/match_waveforms.py word.wav camera_speech.wav \
    --start 100 --end 150 --clock-slope 1.000 --clock-intercept -0.04

Inputs must be mono PCM16 16-kHz WAV. camera_speech.wav is the complete decoded
speech channel, not the DTMF channel. Obtain the clock coefficients from the
source table, rather than assuming the decoded audio and video clocks coincide.
"""
import argparse
import json
import numpy as np

from uaspeech_cut.common import pcm_bytes
from uaspeech_cut.matching import candidates, standardize_resample


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("camera_speech")
    parser.add_argument("--start", type=float, default=0)
    parser.add_argument("--end", type=float)
    parser.add_argument("--clock-slope", type=float, required=True)
    parser.add_argument("--clock-intercept", type=float, required=True)
    parser.add_argument("--fps-num", type=int, default=30000)
    parser.add_argument("--fps-den", type=int, default=1001)
    args = parser.parse_args()
    query = standardize_resample(np.frombuffer(pcm_bytes(args.query), dtype="<i2"), 16000)
    reference = standardize_resample(np.frombuffer(pcm_bytes(args.camera_speech), dtype="<i2"), 16000)
    matches = candidates(reference, query, args.start, args.end)
    for item in matches:
        video_start = args.clock_slope * item["camera_audio_start_s"] + args.clock_intercept
        item["candidate_video_start_s"] = video_start
        item["candidate_begin_frame"] = round(video_start * args.fps_num / args.fps_den)
        item["requires_review"] = True
    print(json.dumps(matches, indent=2))


if __name__ == "__main__":
    main()

