from flask import Flask, request, jsonify, send_from_directory
import os
import re
import uuid
import asyncio
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from typing import Any

from dotenv import load_dotenv

# A marker used in error strings so the API can detect Dedalus configuration problems.
DEDAULUS_CONFIG_ERROR = "DEDALUS_NOT_CONFIGURED"

# Optional dependency: Dedalus Labs SDK (may not exist in this repo yet).
# We keep the server running even if it's missing.
try:
    from dedalus_labs import AsyncDedalus  # type: ignore
except Exception:  # pragma: no cover
    AsyncDedalus = None  # type: ignore

# Local audio engine
try:
    from audio_engine import AudioEngine, AudioEngineError, run_plan  # type: ignore
except Exception:  # pragma: no cover
    AudioEngine = None  # type: ignore
    AudioEngineError = Exception  # type: ignore
    run_plan = None  # type: ignore

# For lightweight audio validation
try:
    import soundfile as _sf  # type: ignore
except Exception:  # pragma: no cover
    _sf = None  # type: ignore

app = Flask(__name__)

# Load env from backend/.env (this file lives in backend/AIDedalus)
ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(ENV_PATH)

API_KEY = os.getenv("API_KEY", "").strip()
DEBUG_UPLOADS = os.getenv("DEBUG_UPLOADS", "").strip().lower() in {"1", "true", "yes", "on"}
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")

AGENT_SYSTEM_PROMPT = os.getenv(
    "AGENT_SYSTEM_PROMPT",
    (
        "You are an AI audio-processing assistant specialized in audio effects. "
        "Be concise, friendly, and professional. "
        "Your job is to directly analyze user requests and generate audio processing code. "
        "Do NOT ask follow-up questions or chat - immediately provide concrete code. "
        "Use clearly audible but safe settings; prefer EQ moves between -6 and +7 dB unless the user asks for extreme effects. "
        "Output JSON only. No comments."
    ),
)

# Store uploads under backend/uploads by default (relative to backend/)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UPLOAD_DIR = os.path.join(BASE_DIR, UPLOAD_FOLDER)

os.makedirs(UPLOAD_DIR, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR

# -----------------------------
# Simple in-memory chat state
# -----------------------------

@dataclass
class ChatMessage:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class AgentPlan:
    effects: List[str]
    generated_code: str


# session_id -> messages
_SESSIONS: Dict[str, List[ChatMessage]] = {}


def _secure_filename(name: str) -> str:
    # Minimal safe filename sanitization.
    name = os.path.basename(name)
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name or "upload.bin"


def save_file(file) -> str:
    """Save uploaded file and return the full path."""
    filename = _secure_filename(getattr(file, "filename", "audio.wav") or "audio.wav")
    unique = f"{uuid.uuid4().hex}_{filename}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique)

    try:
        file.save(filepath)
        file_size = os.path.getsize(filepath)
        print(f"[File Upload] Saved {filename} -> {unique} ({file_size} bytes)")
        return filepath
    except Exception as e:
        print(f"[File Upload] ERROR saving file: {e}")
        raise


def _upload_debug_snapshot() -> Dict[str, Any]:
    """Lightweight snapshot of what Flask received for this request."""
    audio = request.files.get("audio")
    meta: Dict[str, Any] = {
        "content_type": request.content_type,
        "form_keys": sorted(list(request.form.keys())),
        "files_keys": sorted(list(request.files.keys())),
        "has_audio": "audio" in request.files,
    }
    if audio is not None:
        meta["audio"] = {
            "filename": getattr(audio, "filename", None),
            "content_type": getattr(audio, "content_type", None),
            "mimetype": getattr(audio, "mimetype", None),
        }
    return meta


def _is_valid_audio_file(path: str) -> bool:
    """Return True if the file looks like valid audio readable by soundfile or ffmpeg."""
    # First check: file must exist and have reasonable size
    if not os.path.exists(path):
        print(f"[Audio Validation] File does not exist: {path}")
        return False

    file_size = os.path.getsize(path)
    if file_size < 100:  # Too small to be valid audio
        print(f"[Audio Validation] File too small ({file_size} bytes): {path}")
        return False

    # Check file extension first (broad validation)
    valid_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma', '.opus', '.webm'}
    _, ext = os.path.splitext(path.lower())
    if ext not in valid_extensions:
        print(f"[Audio Validation] Invalid extension '{ext}': {path}")
        return False

    # If soundfile is available, try to validate WAV files strictly
    if _sf is not None and ext == '.wav':
        try:
            with _sf.SoundFile(path) as f:
                is_valid = f.frames > 0 and f.samplerate > 0 and f.channels > 0
                if not is_valid:
                    print(f"[Audio Validation] Invalid WAV format (frames={f.frames}, sr={f.samplerate}, ch={f.channels}): {path}")
                return is_valid
        except Exception as e:
            print(f"[Audio Validation] WAV validation error: {e}")
            return False

    # For non-WAV files, trust the extension and let AudioEngine (ffmpeg) handle conversion
    print(f"[Audio Validation] Accepting {ext} file (will convert with ffmpeg): {path}")
    return True


SUPPORTED_EFFECTS = {
    "distortion",
    "reverb",
    "delay",
    "chorus",
    "flanger",
    "eq",
    "compressor",
    "limiter",
    "pitchShift",
    "timeStretch",
    "noisereduce",
    "lufs_normalize",
    "lufs_measure",
}

# Mapping of effect -> plausible plugin variants. The agent may request a specific variant
# (e.g. {"name":"reverb","plugin":"plate"}). If AI doesn't provide a variant we
# pick one deterministically based on the user's prompt to introduce variety without
# randomness across runs for the same input.
SUPPORTED_PLUGINS = {
    "distortion": ["softclip", "hardclip", "tube", "fuzz"],
    "reverb": ["plate", "hall", "room", "spring"],
    "delay": ["analog", "digital", "pingpong"],
    "chorus": ["classic", "ensemble"],
    "flanger": ["wide", "subtle"],
    "eq": ["surgical", "broad", "shelf"],
    "compressor": ["vca", "optical", "va"],
    "limiter": ["brickwall", "lookahead"],
    "pitchShift": ["semitone", "harmonizer"],
    "timeStretch": ["preserve_formants", "fast"],
    "noisereduce": ["spectral", "gating"],
    "lufs_normalize": ["broadcast", "music"],
    "lufs_measure": ["integrated", "short"],
}


def _choose_variant(effect: str, user_text: str) -> Optional[str]:
    """Deterministically choose a plugin variant for effect using a hash of user_text and the effect name.
    This produces more variety between different effects for the same prompt.
    Returns None when no known variants exist."""
    variants = SUPPORTED_PLUGINS.get(effect)
    if not variants:
        return None
    # deterministic index based on hash of the prompt and effect (stable per input)
    key = (user_text or "") + "::" + effect
    idx = abs(hash(key)) % len(variants)
    return variants[idx]


def _parse_effects_obj(obj: object, user_text: str) -> List[str]:
    """Given a parsed JSON object from the model, produce a list of effect strings.
    Accepts either ['reverb','distortion'] or [{'name':'reverb','plugin':'plate'}, ...].
    Returns values like 'reverb:plate' when plugin chosen, otherwise just 'reverb'."""
    out: List[str] = []
    if isinstance(obj, dict):
        eff = obj.get("effects")
        if isinstance(eff, list):
            for item in eff:
                if isinstance(item, dict):
                    name = item.get("name")
                    plugin = item.get("plugin")
                    if isinstance(name, str) and name in SUPPORTED_EFFECTS:
                        if isinstance(plugin, str) and plugin:
                            out.append(f"{name}:{plugin}")
                        else:
                            # choose deterministic variant if available
                            variant = _choose_variant(name, user_text)
                            out.append(f"{name}:{variant}" if variant else name)
                elif isinstance(item, str) and item in SUPPORTED_EFFECTS:
                    variant = _choose_variant(item, user_text)
                    out.append(f"{item}:{variant}" if variant else item)
    return out


def _keywords_fallback(user_text: str) -> List[str]:
    """Simple heuristic fallback when Dedalus is unavailable or fails: match keywords and
    attach deterministic variants.

    NOTE: This is only used when Dedalus can't be called (missing SDK/key) or errors.
    When Dedalus is available, the model is responsible for choosing the right chain.
    """
    txt = user_text.lower()
    found: List[str] = []

    # Synonym-based inference (in addition to direct effect-name matching)
    synonyms = {
        "eq": ["mid", "mids", "presence", "clarity", "tone", "radio", "telephone"],
        "compressor": ["punch", "punchy", "tight", "squash", "broadcast"],
        "limiter": ["loud", "louder", "maximize", "brickwall"],
        "noisereduce": ["noise", "hiss", "hum", "background"],
        "reverb": ["space", "room", "hall", "reverb"],
        "distortion": ["grit", "saturation", "distort", "drive"],
    }

    # Direct name hits
    for eff in SUPPORTED_EFFECTS:
        if eff.lower() in txt:
            variant = _choose_variant(eff, user_text)
            found.append(f"{eff}:{variant}" if variant else eff)

    # Synonym hits
    for eff, keys in synonyms.items():
        if any(k in txt for k in keys):
            variant = _choose_variant(eff, user_text)
            candidate = f"{eff}:{variant}" if variant else eff
            if candidate not in found:
                found.append(candidate)

    # If none found via keywords, fallback to parse backslash commands
    if not found:
        cmds = parse_effect_commands(user_text)
        for c in cmds:
            if c in SUPPORTED_EFFECTS:
                variant = _choose_variant(c, user_text)
                found.append(f"{c}:{variant}" if variant else c)

    return found


async def infer_effects_from_text(session_id: str, user_text: str) -> List[str]:
    """Use Dedalus to infer which SUPPORTED_EFFECTS to apply from natural language.

    Now requests plugin variants when possible. Returns list items of the form
    'effect:plugin' or 'effect'. If Dedalus is unavailable or fails, fall back to
    deterministic keyword heuristics or backslash command parsing.
    """
    prompt = (
        "Infer which effects to apply from this user request. "
        "Return ONLY a JSON object like {\"effects\": [ {\"name\":\"reverb\", \"plugin\":\"plate\"}, ... ] }. "
        "Each effect name must be chosen only from this list: "
        + ", ".join(sorted(SUPPORTED_EFFECTS))
        + ". "
        "Plugin variants are optional but preferred when the model can reasonably pick one. "
        "If none apply, return {\"effects\": []}."
    )

    msgs: List[ChatMessage] = [
        ChatMessage(role="system", content=prompt),
        ChatMessage(role="user", content=user_text),
    ]

    # If Dedalus client is not available or API key missing, skip the model call and use fallback
    if AsyncDedalus is None or not API_KEY:
        try:
            return _keywords_fallback(user_text)
        except Exception:
            return []

    try:
        reply = await dedalus_chat(msgs)
    except Exception as e:
        print(f"[infer_effects_from_text] Dedalus call failed: {e}")
        return _keywords_fallback(user_text)

    obj = _extract_json_object(reply) or {}
    parsed = _parse_effects_obj(obj, user_text)
    if parsed:
        return parsed

    # If model returned a flat list of strings or other format, try to be flexible
    eff = (obj or {}).get("effects") if isinstance(obj, dict) else None
    if isinstance(eff, list):
        out: List[str] = []
        for e in eff:
            if isinstance(e, str) and e in SUPPORTED_EFFECTS:
                variant = _choose_variant(e, user_text)
                out.append(f"{e}:{variant}" if variant else e)
        if out:
            return out

    # final fallback
    return _keywords_fallback(user_text)


def normalize_effects(effects: List[str]) -> Tuple[List[str], List[str]]:
    """Return (known_effects, unknown_effects)."""
    known, unknown = [], []
    for e in effects:
        if e in SUPPORTED_EFFECTS:
            known.append(e)
        else:
            unknown.append(e)
    return known, unknown


def generate_downstream_code(effects: List[str], audio_path: str) -> str:
    """Generate a simple code payload for the next backend.

    Accepts effects like 'reverb:plate' and converts them to safe function names like 'reverb_plate'.
    """
    audio_path_norm = audio_path.replace("\\", "/")
    # Use f-string to interpolate the normalized path properly
    lines = [
        "// generated audio processing plan",
        f"const inputAudio = loadAudio(\"{audio_path_norm}\");",
        "let out = inputAudio;",
    ]
    for e in effects:
        # convert 'name:plugin' -> 'name_plugin' for function naming
        func_name = e.replace(":", "_")
        # ensure safe JS identifier: replace invalid chars with underscore
        func_name = re.sub(r"[^A-Za-z0-9_]", "_", func_name)
        lines.append(f"out = {func_name}(out);")
    lines.append("saveAudio(out);")
    return "\n".join(lines)


def get_or_create_session(session_id: Optional[str]) -> str:
    sid = (session_id or "").strip() or uuid.uuid4().hex
    if sid not in _SESSIONS:
        _SESSIONS[sid] = []
    return sid


import atexit
import inspect


_DEDALUS_CLIENT = None


def _get_dedalus_client():
    global _DEDALUS_CLIENT
    if AsyncDedalus is None or not API_KEY:
        return None
    if _DEDALUS_CLIENT is None:
        _DEDALUS_CLIENT = AsyncDedalus(api_key=API_KEY)  # type: ignore
    return _DEDALUS_CLIENT


async def _close_dedalus_client() -> None:
    """Best-effort cleanup to avoid Proactor warnings on Windows."""
    global _DEDALUS_CLIENT
    client = _DEDALUS_CLIENT
    _DEDALUS_CLIENT = None
    if client is None:
        return

    aclose = getattr(client, "aclose", None)
    if callable(aclose):
        maybe = aclose()
        if inspect.isawaitable(maybe):
            await maybe

    inner = getattr(client, "client", None) or getattr(client, "_client", None)
    inner_aclose = getattr(inner, "aclose", None)
    if callable(inner_aclose):
        maybe = inner_aclose()
        if inspect.isawaitable(maybe):
            await maybe


def _close_dedalus_client_sync() -> None:
    try:
        asyncio.run(_close_dedalus_client())
    except Exception:
        # Don't crash on interpreter shutdown; this is best-effort.
        pass


atexit.register(_close_dedalus_client_sync)


async def generate_assistant_reply(session_id: str, user_text: str, extra_context: Optional[str] = None) -> str:
    """Generate an English reply via Dedalus, with an audio-agent system prompt."""
    msgs: List[ChatMessage] = [ChatMessage(role="system", content=AGENT_SYSTEM_PROMPT)]
    if _SESSIONS.get(session_id):
        msgs.extend(_SESSIONS[session_id])
    else:
        # ensure we can greet even on first turn
        msgs.append(ChatMessage(role="assistant", content="Greet the user and ask what audio change they want."))

    if extra_context:
        msgs.append(ChatMessage(role="system", content=extra_context))

    # Ensure the latest user message is included
    if not msgs or msgs[-1].role != "user" or msgs[-1].content != user_text:
        msgs.append(ChatMessage(role="user", content=user_text))

    return await dedalus_chat(msgs)


def _extract_json_object(text: str) -> Optional[Dict[str, object]]:
    """Best-effort extraction of a single JSON object from an LLM reply."""
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    blob = text[start : end + 1]
    try:
        import json
        obj = json.loads(blob)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


async def dedalus_chat(messages: List[ChatMessage]) -> str:
    """Call Dedalus for chat completions. Minimal wrapper used across the file."""
    if AsyncDedalus is None:
        raise RuntimeError(
            f"{DEDAULUS_CONFIG_ERROR}: dedalus_labs SDK is not installed."
        )
    if not API_KEY:
        raise RuntimeError(
            f"{DEDAULUS_CONFIG_ERROR}: API_KEY is missing."
        )
    client = _get_dedalus_client()
    if client is None:
        raise RuntimeError(f"{DEDAULUS_CONFIG_ERROR}: Dedalus client unavailable.")

    # Use the client's async chat completion API if available, otherwise raise
    resp = await client.chat.completions.create(  # type: ignore[attr-defined]
        model=os.getenv("DEDALUS_MODEL", "gpt-4.1-mini"),
        messages=[asdict(m) for m in messages],
        temperature=float(os.getenv("DEDALUS_TEMPERATURE", "0.4")),
        top_p=float(os.getenv("DEDALUS_TOP_P", "0.9")),
    )
    # Navigate common response shapes
    try:
        return resp.choices[0].message.content  # type: ignore[index]
    except Exception:
        # Fallback: try to stringify the response
        return str(resp)


def _effect_hints_from_effects(effects: List[str]) -> str:
    """Provide short, deterministic guidance to the planner to improve variety & correctness."""
    mapping = {
        "distortion": "distortion: add grit/saturation; use distortion.drive_db 6..30 and add limiter.\n",
        "reverb": "reverb: add space; prefer 'plate' or 'hall' depending on vocal vs. instrument; room_size 0.1..0.8.\n",
        "compressor": "compressor: control dynamics; typical threshold -30..-12, ratio 2..6.\n",
        "eq": "eq: tonal shaping; use shelves a few dB, avoid extreme boosts.\n",
        "limiter": "limiter: prevent clipping; ceiling about -1 dB.\n",
        "noisereduce": "noisereduce: reduce background noise; strength 0.3..0.8.\n",
        "lufs_normalize": "lufs_normalize: adjust loudness; target_lufs -20..-12.\n",
    }
    return "".join(mapping[e.split(':',1)[0]] for e in effects if e.split(':',1)[0] in mapping)


def _validate_audioengine_plan(plan: Dict[str, object]) -> Tuple[bool, List[str]]:
    """Basic validation of a generated plan.

    In addition to JSON shape, we reject obviously no-op plans (e.g. pedalboard_chain with empty args)
    so the backend doesn't pretend to succeed while doing nothing.
    """
    problems: List[str] = []
    if not isinstance(plan, dict):
        return False, ["Plan must be a JSON object."]
    calls = plan.get("calls")
    if not isinstance(calls, list) or not calls:
        return False, ["Plan must contain a non-empty 'calls' list."]
    allowed_ops = {
        "noisereduce",
        "lufs_measure",
        "lufs_normalize",
        "pedalboard_chain",
        "demucs_separate",
        "recombine_stems",
    }
    for i, c in enumerate(calls):
        if not isinstance(c, dict):
            problems.append(f"Call #{i} must be an object.")
            continue
        op = c.get("op")
        args = c.get("args")
        if not isinstance(op, str) or op not in allowed_ops:
            problems.append(f"Call #{i} op must be one of {sorted(allowed_ops)}.")
        if not isinstance(args, dict):
            problems.append(f"Call #{i} args must be an object.")
            continue

        # No-op rejection: pedalboard_chain must specify at least one supported sub-effect
        if op == "pedalboard_chain":
            if not args:
                problems.append("pedalboard_chain args must not be empty.")
            else:
                allowed_sub = {"eq", "compressor", "reverb", "distortion", "gain", "limiter", "filters"}
                if not any(k in args for k in allowed_sub):
                    problems.append("pedalboard_chain must include at least one of eq/compressor/reverb/distortion/gain/limiter/filters.")

    return (len(problems) == 0), problems


async def _ai_plan_audioengine(
    *,
    session_id: str,
    user_text: str,
    effects: List[str],
    attempt: int,
    prior_plan: Optional[Dict[str, object]] = None,
    validation_errors: Optional[List[str]] = None,
) -> Tuple[Optional[Dict[str, object]], str]:
    """Ask the AI to produce a fully-specified AudioEngine plan. Returns (plan_or_none, raw_reply_text)."""

    intent_training = (
        "Intent training (use as guidance):\n"
        "- 'radio/broadcast/telephone/walkie/AM/lofi voice' => a clearly audible chain: pedalboard_chain with EQ + compressor + limiter (filters optional).\n"
        "  Provide REAL numeric params (no empty objects). Example ranges (choose values):\n"
        "  • eq.high_shelf_db: +4..+7, eq.high_shelf_hz: 4000..9000\n"
        "  • eq.low_shelf_db: -4..+3, eq.low_shelf_hz: 120..220\n"
        "  • compressor.threshold_db: -26..-14, ratio: 3..6, attack_ms: 2..12, release_ms: 80..220\n"
        "  • limiter.ceiling_db: about -1.0\n"
        "- 'bring up mids/presence' => EQ shelf moves that are clearly audible (still safe).\n"
    )

    planning_rules = (
        "You are creating a JSON plan for a Python AudioEngine runner. Output ONLY one JSON object. No prose.\n"
        "Schema: {\"calls\": [ {\"op\":..., \"args\":{...}} ] }\n"
        "Allowed ops: noisereduce, lufs_measure, lufs_normalize, pedalboard_chain, demucs_separate, recombine_stems.\n"
        "Hard requirements:\n"
        "- The plan MUST make an audible change that matches the request.\n"
        "- Do NOT output empty args for any call.\n"
        "- If using pedalboard_chain, include at least one of: eq, compressor, reverb, distortion, gain, limiter, filters.\n"
        "- For tonal prompts (mids/presence/radio), include eq and give concrete shelf settings.\n"
        "- Output valid JSON only.\n"
        "\n"
        + intent_training +
        "\nEffects inferred (may be empty): "
    ) + ", ".join(effects)

    extra = f"Planning attempt {attempt}/3."
    if validation_errors:
        extra += " The previous plan failed validation: " + "; ".join(validation_errors)
    if prior_plan:
        extra += " Previous plan JSON: " + str(prior_plan)

    msgs: List[ChatMessage] = [
        ChatMessage(role="system", content=planning_rules + "\n" + extra),
        ChatMessage(role="user", content=user_text),
    ]
    reply = await dedalus_chat(msgs)
    plan = _extract_json_object(reply) or None
    return plan, reply


async def plan_with_retries(*, session_id: str, user_text: str, effects: List[str]) -> Tuple[Optional[Dict[str, object]], Optional[str], Optional[List[str]]]:
    """Try up to 3 times to get a fully valid plan from the AI. Returns (plan, raw_reply, errors)."""
    last_reply = None
    last_errors: Optional[List[str]] = None
    plan: Optional[Dict[str, object]] = None
    for attempt in range(1, 4):
        try:
            plan, last_reply = await _ai_plan_audioengine(
                session_id=session_id,
                user_text=user_text,
                effects=effects,
                attempt=attempt,
                prior_plan=plan,
                validation_errors=last_errors,
            )
        except Exception as e:
            msg = str(e)
            if DEDAULUS_CONFIG_ERROR in msg:
                return None, None, [msg]
            last_errors = [msg]
            continue
        if plan is None:
            last_errors = ["Could not parse JSON plan from the model response."]
            continue
        ok, errs = _validate_audioengine_plan(plan)
        if ok:
            return plan, last_reply, None
        last_errors = errs
    return None, last_reply, last_errors

# -----------------------------
# Routes
# -----------------------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "ok": True,
        "dedalus_available": AsyncDedalus is not None,
        "api_key_configured": bool(API_KEY),
    })


@app.route("/uploads/<path:filename>", methods=["GET"])
def serve_upload(filename):
    """Serve uploaded/processed audio files."""
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# Frontend-friendly aliases (Vite proxy uses /api/*)
@app.route("/api/health", methods=["GET"])
def api_health():
    return health()


@app.route("/api/chat", methods=["POST"])
def api_chat():
    return chat()


@app.route("/api/aiagent", methods=["POST"])
def api_aiagent():
    return ai_agent()


@app.route("/api/process", methods=["POST"])
def api_process():
    """Alias for /api/aiagent for frontend compatibility."""
    return ai_agent()


@app.route("/chat", methods=["POST"])
def chat():
    """Chat-only endpoint (no audio needed)."""
    payload = request.get_json(silent=True) or {}
    session_id = get_or_create_session(payload.get("session_id"))
    text_input = (payload.get("text") or "").strip()

    if not text_input:
        return jsonify({"error": "text is required", "session_id": session_id}), 400

    _SESSIONS[session_id].append(ChatMessage(role="user", content=text_input))

    reply = asyncio.run(generate_assistant_reply(session_id, text_input))
    _SESSIONS[session_id].append(ChatMessage(role="assistant", content=reply))

    return jsonify({
        "session_id": session_id,
        "reply": reply,
        "messages": [asdict(m) for m in _SESSIONS[session_id]],
    })


@app.route("/aiagent", methods=["POST"])
def ai_agent():
    """Agent endpoint: accepts text + optional audio.

    - If no audio is provided and user requests audio modification, ask for audio.
    - If user provided backslash commands, parse effects and run AudioEngine locally.
    """
    session_id = get_or_create_session(request.form.get("session_id"))
    text_input = (request.form.get("text") or "").strip()
    audio_file = request.files.get("audio")
    upload_debug = _upload_debug_snapshot() if DEBUG_UPLOADS else None

    if not text_input:
        resp: Dict[str, Any] = {"error": "Text input is required.", "session_id": session_id}
        if upload_debug is not None:
            resp["debug_uploads"] = upload_debug
        return jsonify(resp), 400

    # Track chat
    _SESSIONS[session_id].append(ChatMessage(role="user", content=text_input))

    # Save upload (if present)
    audio_path: Optional[str] = None
    if audio_file:
        audio_path = save_file(audio_file)

    # If user didn't upload audio, ask them to
    if not audio_path:
        assistant_text = (
            "Please upload an audio file so I can process it according to your request. "
            "Once you upload a file, I'll analyze your prompt and apply the appropriate effects."
        )
        _SESSIONS[session_id].append(ChatMessage(role="assistant", content=assistant_text))
        return jsonify({
            "session_id": session_id,
            "reply": assistant_text,
            "need_audio": True,
        }), 400

    # If the request had an audio part but saving failed for some reason (rare), return a clear error.
    if audio_file is not None and not audio_path:
        resp: Dict[str, object] = {
            "session_id": session_id,
            "error": "Audio upload was present but could not be saved.",
        }
        if upload_debug is not None:
            resp["debug_uploads"] = upload_debug
        return jsonify(resp), 500

    # Ensure these are always defined
    engine_result: Optional[Dict[str, object]] = None
    output_audio_path: Optional[str] = None
    generated_code: Optional[str] = None
    audioengine_plan: Optional[Dict[str, object]] = None

    # Validate audio file exists and has reasonable size
    if not _is_valid_audio_file(audio_path):
        assistant_text = (
            "The uploaded file doesn't appear to be a valid audio file. "
            "Please upload a valid audio file (mp3, wav, flac, etc.). "
            "Note: MP3 files require ffmpeg to be installed on the server."
        )
        _SESSIONS[session_id].append(ChatMessage(role="assistant", content=assistant_text))
        return jsonify({
            "session_id": session_id,
            "error": "Invalid audio file",
            "reply": assistant_text,
        }), 400

    # Check if AudioEngine is available
    if AudioEngine is None or run_plan is None:
        return jsonify({
            "session_id": session_id,
            "error": "AudioEngine is not available in this environment.",
        }), 500

    # Infer effect categories first (Dedalus), then generate a parameterized AudioEngine plan.
    try:
        inferred_effects = asyncio.run(infer_effects_from_text(session_id, text_input))
    except Exception as e:
        inferred_effects = []
        print(f"[AI Agent] infer_effects_from_text failed: {e}")

    hints = _effect_hints_from_effects(inferred_effects)
    if hints:
        # Add hints into the user's prompt so the plan varies appropriately.
        text_for_plan = text_input + "\n\nEffect hints:\n" + hints
    else:
        text_for_plan = text_input

    audioengine_plan, _raw, plan_errors = asyncio.run(
        plan_with_retries(session_id=session_id, user_text=text_for_plan, effects=inferred_effects)
    )

    # Normalize the plan for runtime compatibility (prevents pedalboard_chain(effects=...))
    audioengine_plan = _normalize_audioengine_plan(audioengine_plan)

    # Debug output to terminal
    print("\n" + "="*60)
    print("AI AGENT DEBUG OUTPUT")
    print("="*60)
    print(f"User Request: {text_input}")
    print(f"Audio File: {os.path.basename(audio_path)}")

    if audioengine_plan:
        print("\nGenerated AudioEngine Plan:")
        import json
        print(json.dumps(audioengine_plan, indent=2))

        # Build known_effects preferring plugin-qualified inferred effects
        known_effects = []

        # Helper: find a plugin-qualified inferred effect for a base name
        def _find_inferred_variant(base: str) -> Optional[str]:
            for ie in inferred_effects:
                if ie.split(":", 1)[0] == base:
                    return ie
            return None

        # Try to extract effects from the plan when possible, but prefer inferred variants
        calls = audioengine_plan.get("calls") if isinstance(audioengine_plan, dict) else None
        if isinstance(calls, list):
            for call in calls:
                if not isinstance(call, dict):
                    continue
                op = call.get("op", "")
                # pedalboard_chain contains sub-effect keys in args
                if op == "pedalboard_chain":
                    args = call.get("args", {})
                    if isinstance(args, dict):
                        for key in args.keys():
                            if key in SUPPORTED_EFFECTS:
                                variant = _find_inferred_variant(key)
                                if variant:
                                    known_effects.append(variant)
                                else:
                                    chosen = _choose_variant(key, text_input)
                                    known_effects.append(f"{key}:{chosen}" if chosen else key)
                elif op in SUPPORTED_EFFECTS:
                    variant = _find_inferred_variant(op)
                    if variant:
                        known_effects.append(variant)
                    else:
                        chosen = _choose_variant(op, text_input)
                        known_effects.append(f"{op}:{chosen}" if chosen else op)

        # If plan contained no recognized effects, fall back to the inferred effects (they include variants)
        if not known_effects and inferred_effects:
            known_effects = inferred_effects.copy()

        # IMPORTANT: do NOT silently substitute a keyword-based chain when Dedalus is available.
        # If the model produced a plan with no supported effects, treat it as a planning failure.
        if not known_effects and (AsyncDedalus is not None and bool(API_KEY)):
            print("[AI Agent] ERROR: Model plan included no recognized effects. Not applying heuristic fallbacks.")
            assistant_text = (
                "I generated a plan, but it didn't include any supported audio operations/effects. "
                "Please rephrase the request (e.g., 'boost presence', 'add EQ high shelf', 'compress for radio sound')."
            )
            _SESSIONS[session_id].append(ChatMessage(role="assistant", content=assistant_text))
            return jsonify({
                "session_id": session_id,
                "error": "Plan contained no supported effects.",
                "reply": assistant_text,
                "details": {
                    "inferred_effects": inferred_effects,
                    "audio_engine_plan": audioengine_plan,
                },
            }), 400

        # If Dedalus is NOT available, then heuristic fallback is acceptable.
        if not known_effects:
            known_effects = _keywords_fallback(text_input)

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for e in known_effects:
            if e not in seen:
                seen.add(e)
                deduped.append(e)
        known_effects = deduped

        # Generate downstream code
        if known_effects:
            generated_code = generate_downstream_code(known_effects, audio_path)
            print("\nGenerated Downstream Code:")
            print("-" * 40)
            print(generated_code)
            print("-" * 40)
    else:
        print(f"\nPlan Generation FAILED after 3 attempts")
        print(f"Errors: {plan_errors}")
        if _raw:
            print("\nRaw model reply (last attempt):")
            print(_raw)
        known_effects = []

    print("="*60 + "\n")

    if audioengine_plan is None:
        assistant_text = (
            f"I couldn't generate a processing plan for your request: '{text_input}'. "
            "Please try describing your desired audio changes more clearly, or use specific commands like "
            "'reduce noise', 'add reverb', 'make it louder', etc."
        )
        _SESSIONS[session_id].append(ChatMessage(role="assistant", content=assistant_text))
        return jsonify({
            "session_id": session_id,
            "error": "Unable to build a complete AudioEngine plan from the user request after 3 attempts.",
            "reply": assistant_text,
            "details": plan_errors,
        }), 400

    # Execute the plan
    try:
        print(f"[AudioEngine] Initializing engine with: {audio_path}")
        engine = AudioEngine(audio_path)
        try:
            print(f"[AudioEngine] Running plan...")
            engine_result = run_plan(engine, audioengine_plan)  # type: ignore[misc]
            print(f"[AudioEngine] Plan execution complete: {engine_result}")

            # Export to backend/uploads with a stable naming scheme
            out_name = f"processed_{uuid.uuid4().hex}.wav"
            output_audio_path = os.path.join(app.config["UPLOAD_FOLDER"], out_name)
            print(f"[AudioEngine] Exporting to: {output_audio_path}")
            engine.export(output_audio_path)
            print(f"[AudioEngine] Export complete. File size: {os.path.getsize(output_audio_path)} bytes")
        finally:
            engine.close()
    except AudioEngineError as e:
        print(f"[AudioEngine] AudioEngineError: {e}")
        assistant_text = f"Error processing audio: {str(e)}"
        _SESSIONS[session_id].append(ChatMessage(role="assistant", content=assistant_text))
        return jsonify({
            "session_id": session_id,
            "error": str(e),
            "reply": assistant_text,
        }), 400
    except Exception as e:
        print(f"[AudioEngine] Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        assistant_text = f"Unexpected error processing audio: {str(e)}"
        _SESSIONS[session_id].append(ChatMessage(role="assistant", content=assistant_text))
        return jsonify({
            "session_id": session_id,
            "error": str(e),
            "reply": assistant_text,
        }), 500

    # Downstream payload: for the next backend (not implemented yet)
    downstream_payload = {
        "effects": known_effects,
        "generated_code": generated_code,
        "input_audio_path": audio_path,
        "output_audio_path": output_audio_path,
        "audio_engine_plan": audioengine_plan,
        "audio_engine_result": engine_result,
    }

    # Build assistant reply - simple technical summary
    if output_audio_path and known_effects:
        effects_list = ", ".join(known_effects)
        assistant_text = f"✓ Audio processing complete. Applied effects: {effects_list}. Your processed audio is ready for download."
    elif output_audio_path:
        assistant_text = "✓ Audio processing complete. Your processed audio is ready for download."
    else:
        assistant_text = "Audio processing completed."

    _SESSIONS[session_id].append(ChatMessage(role="assistant", content=assistant_text))

    # Prepare output path for frontend (just filename, not full path)
    output_filename = None
    if output_audio_path:
        output_filename = os.path.basename(output_audio_path)

    resp: Dict[str, Any] = {
        "session_id": session_id,
        "reply": assistant_text,
        "audio_path": audio_path,
        "output_audio_path": output_filename,
        "known_effects": known_effects,
        "audio_engine": {
            "ran": bool(engine_result),
            "result": engine_result,
        },
        "downstream": {
            "next_backend_url": None,
            "payload": downstream_payload,
            "generated_code": generated_code,
        },
        "messages": [asdict(m) for m in _SESSIONS[session_id]],
    }
    if upload_debug is not None:
        resp["debug_uploads"] = upload_debug
    return jsonify(resp)


def parse_effect_commands(text_input: str) -> List[str]:
    """Extract effect function names from text like: \distortion(); \reverb();"""
    effects: List[str] = []
    for match in re.finditer(r"\\\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*\)\s*;?", text_input):
        effects.append(match.group(1))
    # fallback: if user starts with backslash but didn't include ()
    if not effects and text_input.strip().startswith("\\"):
        maybe = text_input.strip()[1:].strip().rstrip(";")
        maybe = re.sub(r"\(.*\)$", "", maybe).strip()
        if maybe:
            effects = [maybe]
    return effects


def _normalize_audioengine_plan(plan: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Normalize AI-produced plans to match our AudioEngine.run_plan expectations.

    Today the main mismatch we see is when the model emits:
      {"op":"pedalboard_chain","args":{"effects":[{"name":"reverb","args":{...}}, ...]}}
    but AudioEngine.pedalboard_chain() expects keyword args like:
      {"op":"pedalboard_chain","args":{"reverb":{...}, "distortion":{...}}}

    This function converts the former into the latter and drops unknown effects.
    """
    if plan is None or not isinstance(plan, dict):
        return plan

    calls = plan.get("calls")
    if not isinstance(calls, list):
        return plan

    normalized_calls: List[Dict[str, Any]] = []
    for call in calls:
        if not isinstance(call, dict):
            continue

        op = call.get("op")
        args = call.get("args")
        if op != "pedalboard_chain" or not isinstance(args, dict):
            normalized_calls.append(call)  # type: ignore[arg-type]
            continue

        effects = args.get("effects")
        if not isinstance(effects, list):
            normalized_calls.append(call)  # type: ignore[arg-type]
            continue

        coerced: Dict[str, Any] = {}
        for item in effects:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            eargs = item.get("args", {})
            if isinstance(name, str) and name in SUPPORTED_EFFECTS and isinstance(eargs, dict):
                coerced[name] = eargs

        # Preserve any already-correct keys (eq/reverb/etc.) while ensuring we don't pass `effects=`
        for k, v in args.items():
            if k == "effects":
                continue
            coerced.setdefault(k, v)

        normalized_calls.append({"op": op, "args": coerced})

    plan["calls"] = normalized_calls
    return plan
