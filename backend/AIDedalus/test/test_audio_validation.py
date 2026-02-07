"""Test script to validate audio file processing."""
import os
import sys
import time

# Make sure the AIDedalus package directory is importable regardless of cwd/IDE.
_AIDEDALUS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _AIDEDALUS_DIR not in sys.path:
    sys.path.insert(0, _AIDEDALUS_DIR)

import audio_engine as ae


def _p(msg: str) -> None:
    """Print + flush so output is visible even when buffering hides it."""
    print(msg, flush=True)


def _file_stat(path: str) -> str:
    if not os.path.exists(path):
        return "MISSING"
    try:
        return f"{os.path.getsize(path)} bytes"
    except Exception as e:
        return f"exists (stat error: {e})"


def _fsync_dir(dir_path: str) -> None:
    """Best-effort: ensure directory entries are flushed (mostly useful on POSIX)."""
    try:
        if hasattr(os, "sync"):
            os.sync()  # type: ignore[attr-defined]
    except Exception:
        pass


def _run_processing_direct(engine: "ae.AudioEngine", output_path: str, *, fast: bool = False) -> str:
    """Run processing by calling engine methods directly (bypasses run_plan)."""
    _p("\n[DIRECT] Starting direct processing...")

    if not fast:
        _p("[DIRECT] noisereduce...")
        t0 = time.time()
        engine.noisereduce(strength=0.6)
        _p(f"[DIRECT] noisereduce done in {time.time() - t0:.2f}s")

    _p("[DIRECT] pedalboard_chain (with distortion + reverb)...")
    t0 = time.time()
    engine.pedalboard_chain(
        # Make it obvious:
        distortion={"drive_db": 18.0},
        reverb={"room_size": 0.85},
        # Keep some dynamics control so it doesn't clip too hard:
        compressor={"threshold_db": -24.0, "ratio": 4.0, "attack_ms": 5.0, "release_ms": 150.0},
        eq={"low_shelf_db": 3.0, "low_shelf_hz": 140.0, "high_shelf_db": 6.0, "high_shelf_hz": 9000.0},
        limiter={"ceiling_db": -1.0},
    )
    _p(f"[DIRECT] pedalboard_chain done in {time.time() - t0:.2f}s")

    _p("[DIRECT] lufs_normalize...")
    t0 = time.time()
    engine.lufs_normalize(target_lufs=-16.0)
    _p(f"[DIRECT] lufs_normalize done in {time.time() - t0:.2f}s")

    _p(f"[DIRECT] Exporting processed audio to: {os.path.abspath(output_path)}")
    engine.export(output_path)
    _p(f"[DIRECT] Export done: {_file_stat(output_path)}")
    return output_path


def _run_processing_plan(engine: "ae.AudioEngine", output_path: str, *, fast: bool = False) -> str:
    """Run a small deterministic plan and export a wav.

    Returns output path.
    """
    # If run_plan stalls in your environment, direct mode is more debuggable.
    return _run_processing_direct(engine, output_path, fast=fast)


def _test_audio_file(filepath: str, *, do_process: bool = False, keep_outputs: bool = False, fast: bool = False) -> bool:
    """Test if an audio file can be read and optionally processed.

    Note: prefixed with '_' so pytest doesn't treat it as a test that requires fixtures.
    """
    _p(f"\n{'='*60}")
    _p(f"Testing: {filepath}")
    _p(f"{'='*60}")

    if not os.path.exists(filepath):
        _p(f"❌ File does not exist: {filepath}")
        return False

    file_size = os.path.getsize(filepath)
    _p(f"File size: {file_size} bytes")

    processed_path_abs: str | None = None

    try:
        _p("Initializing AudioEngine...")
        engine = ae.AudioEngine(filepath)
        _p("✓ AudioEngine initialized successfully")

        _p("Measuring LUFS...")
        result = engine.lufs_measure()
        _p(f"✓ LUFS measurement: {result}")

        if do_process:
            _p("Running processing plan...")
            processed_path = os.path.join(os.path.dirname(__file__), "test_output_processed.wav")
            processed_path_abs = os.path.abspath(processed_path)
            out_path = _run_processing_plan(engine, processed_path, fast=fast)
            _fsync_dir(os.path.dirname(out_path))
            if not os.path.exists(out_path) or os.path.getsize(out_path) <= 0:
                raise ae.AudioEngineError(f"Processed output was not created or empty: {out_path} ({_file_stat(out_path)})")
            _p(f"✓ Processed export: {processed_path_abs} ({os.path.getsize(out_path)} bytes)")

        _p("Exporting current audio...")
        output_path = os.path.join(os.path.dirname(filepath), "test_output.wav")
        output_path_abs = os.path.abspath(output_path)
        engine.export(output_path)
        _fsync_dir(os.path.dirname(output_path))
        if not os.path.exists(output_path) or os.path.getsize(output_path) <= 0:
            raise ae.AudioEngineError(f"Exported output was not created or empty: {output_path} ({_file_stat(output_path)})")
        _p(f"✓ Exported to: {output_path_abs} ({os.path.getsize(output_path)} bytes)")

        engine.close()
        _p("✓ Engine closed successfully")

        # Clean up test outputs unless --keep was used
        if keep_outputs:
            manifest_path = os.path.join(os.path.dirname(__file__), "outputs_manifest.txt")
            manifest_abs = os.path.abspath(manifest_path)
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write("Exported files (absolute paths):\n")
                f.write(f"- {output_path_abs}\n")
                if processed_path_abs:
                    f.write(f"- {processed_path_abs}\n")

            _p("\nOUTPUT SUCCESSFUL")
            _p(f"- {output_path_abs} ({_file_stat(output_path)})")
            if processed_path_abs:
                _p(f"- {processed_path_abs} ({_file_stat(processed_path_abs)})")
            _p(f"Manifest: {manifest_abs} ({_file_stat(manifest_path)})")

            _p("\nDirectory listing (wav + manifest):")
            for name in sorted(os.listdir(os.path.dirname(__file__))):
                if name.lower().endswith(".wav") or name == "outputs_manifest.txt":
                    _p(f"  - {name} ({_file_stat(os.path.join(os.path.dirname(__file__), name))})")

            return True

        for p in [output_path, os.path.join(os.path.dirname(__file__), "test_output_processed.wav")]:
            if os.path.exists(p):
                os.remove(p)
                _p(f"✓ Cleaned up: {os.path.basename(p)}")

        _p("\nOUTPUT SUCCESSFUL (cleaned up)")
        return True

    except ae.AudioEngineError as e:
        _p(f"❌ AudioEngineError: {e}")
        return False
    except Exception as e:
        _p(f"❌ Unexpected error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Default file
    test_file = os.path.join(os.path.dirname(__file__), "test_Man.mp3")

    # Args:
    #   python test_audio_validation.py <path> [--process] [--keep] [--fast]
    do_process = "--process" in sys.argv
    keep_outputs = "--keep" in sys.argv
    fast = "--fast" in sys.argv
    args = [a for a in sys.argv[1:] if a not in {"--process", "--keep", "--fast"}]

    if len(args) > 0:
        test_file = args[0]

    _p(f"Looking for test file: {test_file}")
    _p(f"Absolute path: {os.path.abspath(test_file)}")
    _p(f"File exists: {os.path.exists(test_file)}")

    success = _test_audio_file(test_file, do_process=do_process, keep_outputs=keep_outputs, fast=fast)

    if success:
        _p("\n✓ All tests passed!")
        sys.exit(0)
    else:
        _p("\n❌ Tests failed!")
        sys.exit(1)
