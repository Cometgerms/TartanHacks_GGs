"""Isolated Pedalboard processor.

Why this exists:
- On some Windows/Conda environments, Pedalboard's native backend can hang.
- Running Pedalboard in a separate process allows us to enforce a timeout and
  report a clear error instead of freezing the whole backend.

This module is used by AudioEngine.pedalboard_chain.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
from pedalboard import (
    Pedalboard,
    Reverb,
    Distortion,
    Compressor,
    Gain,
    Limiter,
    HighpassFilter,
    LowpassFilter,
    LowShelfFilter,
    HighShelfFilter,
)
from pedalboard.io import AudioFile


def _build_board(*, args: Dict[str, Any]) -> Pedalboard:
    eq = args.get("eq")
    compressor = args.get("compressor")
    reverb = args.get("reverb")
    distortion = args.get("distortion")
    gain = args.get("gain")
    limiter = args.get("limiter")
    filters = args.get("filters")

    board = Pedalboard([])

    if isinstance(filters, dict):
        hp = filters.get("highpass_hz")
        lp = filters.get("lowpass_hz")
        if hp is not None:
            board.append(HighpassFilter(cutoff_frequency_hz=float(hp)))
        if lp is not None:
            board.append(LowpassFilter(cutoff_frequency_hz=float(lp)))

    if isinstance(eq, dict):
        if eq.get("low_shelf_db") is not None:
            board.append(
                LowShelfFilter(
                    cutoff_frequency_hz=float(eq.get("low_shelf_hz", 120.0)),
                    gain_db=float(eq["low_shelf_db"]),
                )
            )
        if eq.get("high_shelf_db") is not None:
            board.append(
                HighShelfFilter(
                    cutoff_frequency_hz=float(eq.get("high_shelf_hz", 8000.0)),
                    gain_db=float(eq["high_shelf_db"]),
                )
            )

    if isinstance(compressor, dict):
        board.append(
            Compressor(
                threshold_db=float(compressor.get("threshold_db", -18.0)),
                ratio=float(compressor.get("ratio", 2.0)),
                attack_ms=float(compressor.get("attack_ms", 10.0)),
                release_ms=float(compressor.get("release_ms", 100.0)),
            )
        )

    if isinstance(reverb, dict):
        board.append(Reverb(room_size=float(np.clip(reverb.get("room_size", 0.2), 0.0, 1.0))))

    if isinstance(distortion, dict):
        board.append(Distortion(drive_db=float(distortion.get("drive_db", 0.0))))

    if isinstance(gain, dict):
        board.append(Gain(gain_db=float(gain.get("gain_db", 0.0))))

    if isinstance(limiter, dict):
        ceiling = float(limiter.get("ceiling_db", -1.0))
        board.append(Limiter(threshold_db=ceiling))

    return board


def process_file(*, in_path: str, out_path: str, args: Dict[str, Any]) -> None:
    board = _build_board(args=args)

    in_p = Path(in_path)
    out_p = Path(out_path)
    if not in_p.exists():
        raise FileNotFoundError(str(in_p))

    with AudioFile(str(in_p)) as f:
        sr = f.samplerate
        num_channels = f.num_channels
        with AudioFile(str(out_p), "w", sr, num_channels) as out:
            while f.tell() < f.frames:
                chunk = f.read(int(sr))
                if chunk is None or chunk.size == 0:
                    break
                out.write(board(chunk, sr))


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 3:
        print("Usage: pedalboard_worker.py <in_wav> <out_wav> <args_json>", file=sys.stderr)
        return 2

    in_path, out_path, args_json = argv
    args = json.loads(args_json)
    if not isinstance(args, dict):
        raise ValueError("args_json must be an object")

    process_file(in_path=in_path, out_path=out_path, args=args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

