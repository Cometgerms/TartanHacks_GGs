# audio_engine.py
from __future__ import annotations

import io
import os
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import soundfile as sf

# pedalboard
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

# noisereduce
import noisereduce as nr

# pyloudnorm
import pyloudnorm as pyln


# ----------------------------
# Utilities
# ----------------------------

class AudioEngineError(Exception):
    pass


def _ensure_wav(in_path: str, out_path: str) -> None:
    """
    Ensures audio is WAV. If input is non-wav, converts using ffmpeg if available.
    """
    in_path_p = Path(in_path)
    out_path_p = Path(out_path)

    if in_path_p.suffix.lower() == ".wav":
        shutil.copyfile(in_path, out_path)
        return

    # Convert via ffmpeg
    cmd = ["ffmpeg", "-y", "-i", str(in_path_p), str(out_path_p)]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        raise AudioEngineError("ffmpeg not found. Install ffmpeg or provide WAV input.")
    except subprocess.CalledProcessError:
        raise AudioEngineError("ffmpeg conversion failed. Input audio may be corrupted.")


def load_audio(path: str, always_mono: bool = False) -> Tuple[np.ndarray, int]:
    """
    Returns audio as float32 ndarray shape (n_samples, n_channels) and sample rate.
    """
    audio, sr = sf.read(path, always_2d=True)
    audio = audio.astype(np.float32)

    if always_mono and audio.shape[1] > 1:
        audio = np.mean(audio, axis=1, keepdims=True)

    return audio, sr


def save_wav(path: str, audio: np.ndarray, sr: int) -> None:
    """
    Saves float audio to WAV (16-bit PCM).
    """
    # Clip to [-1,1] to be safe
    audio = np.clip(audio, -1.0, 1.0)
    sf.write(path, audio, sr, subtype="PCM_16")


def peak_normalize(audio: np.ndarray, target_peak: float = 0.98) -> np.ndarray:
    peak = float(np.max(np.abs(audio)))
    if peak <= 1e-9:
        return audio
    gain = target_peak / peak
    return audio * gain


# ----------------------------
# Core engine
# ----------------------------

@dataclass
class EnginePaths:
    work_dir: Path
    input_wav: Path
    current_wav: Path


class AudioEngine:
    """
    AudioEngine manages a "working copy" of the audio in a temp directory.
    Each operation reads current_wav and writes a new current_wav.
    """

    def __init__(self, input_audio_path: str):
        self._tmp = tempfile.TemporaryDirectory(prefix="audio_engine_")
        work_dir = Path(self._tmp.name)

        input_wav = work_dir / "input.wav"
        _ensure_wav(input_audio_path, str(input_wav))

        self.paths = EnginePaths(
            work_dir=work_dir,
            input_wav=input_wav,
            current_wav=work_dir / "current.wav",
        )
        shutil.copyfile(input_wav, self.paths.current_wav)

    def close(self) -> None:
        self._tmp.cleanup()

    # -------------
    # Operations
    # -------------

    def noisereduce(self, strength: float = 0.8, prop_decrease: Optional[float] = None) -> str:
        """
        Noise reduction using noisereduce spectral gating.
        strength: 0..1 (mapped to prop_decrease if not given)
        """
        strength = float(np.clip(strength, 0.0, 1.0))
        if prop_decrease is None:
            # prop_decrease range commonly 0.0..1.0
            prop_decrease = strength

        audio, sr = load_audio(str(self.paths.current_wav), always_mono=False)

        # noisereduce expects shape (n_samples,) or (n_samples, n_channels) is okay but we handle channels explicitly
        out = np.zeros_like(audio)
        for ch in range(audio.shape[1]):
            out[:, ch] = nr.reduce_noise(y=audio[:, ch], sr=sr, prop_decrease=float(prop_decrease))

        out = peak_normalize(out)
        save_wav(str(self.paths.current_wav), out, sr)
        return str(self.paths.current_wav)

    def lufs_measure(self) -> Dict[str, float]:
        """
        Measures integrated loudness (LUFS) and true peak-ish (peak sample).
        """
        audio, sr = load_audio(str(self.paths.current_wav), always_mono=False)
        meter = pyln.Meter(sr)

        # pyloudnorm expects mono for loudness; common approach is to average channels for measurement
        mono = np.mean(audio, axis=1)
        lufs = float(meter.integrated_loudness(mono))
        peak = float(np.max(np.abs(audio)))
        return {"integrated_lufs": lufs, "peak": peak}

    def lufs_normalize(self, target_lufs: float = -14.0) -> str:
        """
        Normalizes perceived loudness to target LUFS.
        Note: apply limiter after if you drive it louder.
        """
        audio, sr = load_audio(str(self.paths.current_wav), always_mono=False)
        meter = pyln.Meter(sr)
        mono = np.mean(audio, axis=1)
        current_lufs = float(meter.integrated_loudness(mono))

        out = np.zeros_like(audio)
        for ch in range(audio.shape[1]):
            out[:, ch] = pyln.normalize.loudness(audio[:, ch], current_lufs, float(target_lufs))

        # Not clipping-protected by default; keep headroom
        out = np.clip(out, -1.0, 1.0)
        save_wav(str(self.paths.current_wav), out, sr)
        return str(self.paths.current_wav)

    def pedalboard_chain(
        self,
        *,
        eq: Optional[Dict[str, Any]] = None,
        compressor: Optional[Dict[str, Any]] = None,
        reverb: Optional[Dict[str, Any]] = None,
        distortion: Optional[Dict[str, Any]] = None,
        gain: Optional[Dict[str, Any]] = None,
        limiter: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Applies a deterministic Pedalboard FX chain.
        All args are optional dictionaries so your GPT plan can specify only what it needs.

        Supported keys:
        - eq: {low_shelf_db, low_shelf_hz, high_shelf_db, high_shelf_hz}
        - filters: {highpass_hz, lowpass_hz}
        - compressor: {threshold_db, ratio, attack_ms, release_ms}
        - reverb: {room_size}   (0..1)
        - distortion: {drive_db}
        - gain: {gain_db}
        - limiter: {ceiling_db}  (threshold_db in pedalboard limiter)
        """
        audio, sr = load_audio(str(self.paths.current_wav), always_mono=False)

        board = Pedalboard([])

        # Filters
        if filters:
            hp = filters.get("highpass_hz")
            lp = filters.get("lowpass_hz")
            if hp is not None:
                board.append(HighpassFilter(cutoff_hz=float(hp)))
            if lp is not None:
                board.append(LowpassFilter(cutoff_hz=float(lp)))

        # EQ shelves (simple and safe)
        if eq:
            if eq.get("low_shelf_db") is not None:
                board.append(
                    LowShelfFilter(
                        cutoff_hz=float(eq.get("low_shelf_hz", 120.0)),
                        gain_db=float(eq["low_shelf_db"]),
                    )
                )
            if eq.get("high_shelf_db") is not None:
                board.append(
                    HighShelfFilter(
                        cutoff_hz=float(eq.get("high_shelf_hz", 8000.0)),
                        gain_db=float(eq["high_shelf_db"]),
                    )
                )

        # Compressor
        if compressor:
            board.append(
                Compressor(
                    threshold_db=float(compressor.get("threshold_db", -18.0)),
                    ratio=float(compressor.get("ratio", 2.0)),
                    attack_ms=float(compressor.get("attack_ms", 10.0)),
                    release_ms=float(compressor.get("release_ms", 100.0)),
                )
            )

        # Reverb
        if reverb:
            board.append(Reverb(room_size=float(np.clip(reverb.get("room_size", 0.2), 0.0, 1.0))))

        # Distortion
        if distortion:
            board.append(Distortion(drive_db=float(distortion.get("drive_db", 0.0))))

        # Gain
        if gain:
            board.append(Gain(gain_db=float(gain.get("gain_db", 0.0))))

        # Limiter at end
        if limiter:
            ceiling = float(limiter.get("ceiling_db", -1.0))
            board.append(Limiter(threshold_db=ceiling))

        # Apply
        out = board(audio, sr)
        out = np.clip(out, -1.0, 1.0)
        save_wav(str(self.paths.current_wav), out, sr)
        return str(self.paths.current_wav)

    def demucs_separate(self, model: str = "htdemucs") -> Dict[str, str]:
        """
        Runs Demucs stem separation (CLI) and returns paths:
        { "vocals": "...wav", "drums": "...wav", "bass": "...wav", "other": "...wav" }

        Requires demucs installed and available in environment.
        """
        out_dir = self.paths.work_dir / "stems"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Demucs CLI:
        # demucs -n htdemucs -o stems current.wav
        cmd = [
            "demucs",
            "-n",
            model,
            "-o",
            str(out_dir),
            str(self.paths.current_wav),
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            raise AudioEngineError("demucs CLI not found. Install with: pip install demucs")
        except subprocess.CalledProcessError:
            raise AudioEngineError("demucs separation failed.")

        # Demucs output path pattern:
        # stems/<model>/<trackname>/(vocals|drums|bass|other).wav
        # Our input name is "current.wav" => trackname "current"
        track_dir = out_dir / model / "current"
        if not track_dir.exists():
            # Sometimes demucs uses filename without extension; usually "current"
            raise AudioEngineError("demucs output not found; unexpected output structure.")

        stems = {}
        for stem in ["vocals", "drums", "bass", "other"]:
            p = track_dir / f"{stem}.wav"
            if p.exists():
                stems[stem] = str(p)

        if len(stems) < 2:
            raise AudioEngineError("demucs produced too few stems; check input audio.")

        return stems

    def recombine_stems(
        self,
        stems: Dict[str, str],
        gains_db: Optional[Dict[str, float]] = None,
    ) -> str:
        """
        Recombines stems (time-aligned) into current.wav.
        gains_db: optional per-stem gain changes, e.g. {"bass": 4.0, "other": 2.0}
        """
        if gains_db is None:
            gains_db = {}

        stem_audios = []
        sr0 = None
        max_len = 0

        # Load each stem
        for stem_name, stem_path in stems.items():
            audio, sr = load_audio(stem_path, always_mono=False)
            if sr0 is None:
                sr0 = sr
            elif sr != sr0:
                raise AudioEngineError("Stem sample rates differ; cannot recombine.")

            # Apply gain
            g_db = float(gains_db.get(stem_name, 0.0))
            lin = 10 ** (g_db / 20.0)
            audio = audio * lin

            stem_audios.append(audio)
            max_len = max(max_len, audio.shape[0])

        assert sr0 is not None

        # Pad to same length and sum
        mix = None
        for a in stem_audios:
            if a.shape[0] < max_len:
                pad = np.zeros((max_len - a.shape[0], a.shape[1]), dtype=np.float32)
                a = np.vstack([a, pad])
            mix = a if mix is None else (mix + a)

        # Prevent clipping
        mix = peak_normalize(mix, target_peak=0.98)
        save_wav(str(self.paths.current_wav), mix, sr0)
        return str(self.paths.current_wav)

    def export(self, output_path: str) -> str:
        """
        Copies current.wav to output_path.
        """
        shutil.copyfile(self.paths.current_wav, output_path)
        return output_path


# ----------------------------
# Dispatcher (exec LLM plan safely)
# ----------------------------

ALLOWED_OPS = {
    "noisereduce",
    "lufs_measure",
    "lufs_normalize",
    "pedalboard_chain",
    "demucs_separate",
    "recombine_stems",
}

def run_plan(engine: AudioEngine, plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    plan format:
    {
      "calls": [
        {"op": "noisereduce", "args": {"strength": 0.8}},
        {"op": "pedalboard_chain", "args": {"eq": {...}, "compressor": {...}, ...}},
        {"op": "lufs_normalize", "args": {"target_lufs": -14.0}}
      ]
    }

    Returns execution log with results.
    """
    calls = plan.get("calls")
    if not isinstance(calls, list):
        raise AudioEngineError("Plan missing 'calls' list.")

    log: List[Dict[str, Any]] = []
    context: Dict[str, Any] = {}  # for passing stems, measurements, etc.

    for idx, call in enumerate(calls):
        if not isinstance(call, dict):
            raise AudioEngineError(f"Call #{idx} must be an object.")

        op = call.get("op")
        args = call.get("args", {})
        if op not in ALLOWED_OPS:
            raise AudioEngineError(f"Operation not allowed: {op}")

        if not isinstance(args, dict):
            raise AudioEngineError(f"Args for op {op} must be an object.")

        # Execute with safe routing
        if op == "noisereduce":
            out = engine.noisereduce(**args)
            log.append({"op": op, "out": out})

        elif op == "lufs_measure":
            out = engine.lufs_measure()
            context["lufs_measure"] = out
            log.append({"op": op, "out": out})

        elif op == "lufs_normalize":
            out = engine.lufs_normalize(**args)
            log.append({"op": op, "out": out})

        elif op == "pedalboard_chain":
            out = engine.pedalboard_chain(**args)
            log.append({"op": op, "out": out})

        elif op == "demucs_separate":
            stems = engine.demucs_separate(**args)
            context["stems"] = stems
            log.append({"op": op, "out": stems})

        elif op == "recombine_stems":
            # args can refer to previously separated stems
            stems = args.get("stems") or context.get("stems")
            if not stems:
                raise AudioEngineError("recombine_stems requires stems (or run demucs_separate first).")
            gains_db = args.get("gains_db", {})
            out = engine.recombine_stems(stems=stems, gains_db=gains_db)
            log.append({"op": op, "out": out})

    return {"ok": True, "log": log, "context": context}
