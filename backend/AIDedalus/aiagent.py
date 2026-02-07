from flask import Flask, request, jsonify
import os
import re
import uuid
import asyncio
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

# Optional dependency: Dedalus Labs SDK (may not exist in this repo yet).
# We keep the server running even if it's missing.
try:
    from dedalus_labs import AsyncDedalus  # type: ignore
except Exception:  # pragma: no cover
    AsyncDedalus = None  # type: ignore

app = Flask(__name__)

# Load env from backend/.env (this file lives in backend/AIDedalus)
ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(ENV_PATH)

API_KEY = os.getenv("API_KEY", "").strip()
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")

AGENT_SYSTEM_PROMPT = os.getenv(
    "AGENT_SYSTEM_PROMPT",
    (
        "You are an AI audio-processing assistant. Always respond in English. "
        "Be concise, friendly, and practical. "
        "Your job is to help the user decide which audio effects to apply and to produce "
        "a downstream code payload (pseudo-code is fine). "
        "If the user requests audio modification but no audio file is provided, ask them to upload one."
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
    filename = _secure_filename(getattr(file, "filename", "audio.wav") or "audio.wav")
    unique = f"{uuid.uuid4().hex}_{filename}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique)
    file.save(filepath)
    return filepath


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
}


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

    Assumption: downstream accepts a chain of effect calls like:
      \\distortion(); \\reverb();
    """
    # We keep it language-agnostic: a pseudo pipeline.
    audio_path_norm = audio_path.replace("\\", "/")
    lines = [
        "// generated audio processing plan",
        f"const inputAudio = loadAudio(\"{audio_path_norm}\");",
        "let out = inputAudio;",
    ]
    for e in effects:
        lines.append(f"out = {e}(out);")
    lines.append("saveAudio(out);")
    return "\n".join(lines)


def get_or_create_session(session_id: Optional[str]) -> str:
    sid = (session_id or "").strip() or uuid.uuid4().hex
    if sid not in _SESSIONS:
        _SESSIONS[sid] = []
    return sid


async def dedalus_chat(messages: List[ChatMessage]) -> str:
    """If Dedalus SDK is available, call it. Otherwise, fallback to a deterministic response."""
    if AsyncDedalus is None or not API_KEY:
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        return (
            "Hi! I'm your audio-processing assistant. Tell me what you want to change, "
            "and optionally upload an audio file. "
            "If you already know effects, you can use commands like `\\reverb();` or `\\distortion();`.\n"
            f"You said: {last_user}"
        )

    client = AsyncDedalus(api_key=API_KEY)  # type: ignore
    resp = await client.chat.completions.create(  # type: ignore[attr-defined]
        model=os.getenv("DEDALUS_MODEL", "gpt-4.1-mini"),
        messages=[asdict(m) for m in messages],  # type: ignore[arg-type]
    )
    return resp.choices[0].message.content  # type: ignore[index]


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
    - If user provided backslash commands, parse effects and return generated code.
    """
    session_id = get_or_create_session(request.form.get("session_id"))
    text_input = (request.form.get("text") or "").strip()
    audio_file = request.files.get("audio")

    if not text_input:
        return jsonify({"error": "Text input is required.", "session_id": session_id}), 400

    # Track chat
    _SESSIONS[session_id].append(ChatMessage(role="user", content=text_input))

    requested_effects = parse_effect_commands(text_input)
    known_effects, unknown_effects = normalize_effects(requested_effects)

    # If user seems to want audio modification (has effect commands) but no audio, ask for it.
    if requested_effects and not audio_file:
        extra = (
            "The user requested these effect commands but did not upload an audio file. "
            f"Requested effects: {requested_effects}. "
            "Ask a single clear question: whether they'd like to upload an audio file now."
        )
        reply = asyncio.run(generate_assistant_reply(session_id, text_input, extra_context=extra))
        _SESSIONS[session_id].append(ChatMessage(role="assistant", content=reply))
        return jsonify({
            "session_id": session_id,
            "reply": reply,
            "need_audio": True,
            "requested_effects": requested_effects,
            "supported_effects": sorted(SUPPORTED_EFFECTS),
            "unknown_effects": unknown_effects,
        })

    audio_path: Optional[str] = None
    if audio_file:
        audio_path = save_file(audio_file)

    # If we have effects + audio, generate downstream code payload.
    plan: Optional[AgentPlan] = None
    if known_effects and audio_path:
        code = generate_downstream_code(known_effects, audio_path)
        plan = AgentPlan(effects=known_effects, generated_code=code)

    # Build assistant reply (either via Dedalus or fallback)
    # Provide plan summary if we computed one.
    if plan is not None:
        extra = (
            "You have created an audio-processing plan and a downstream code payload. "
            f"Known effects: {plan.effects}. "
            f"Unknown effects: {unknown_effects}. "
            "Explain the plan briefly and mention that a code payload is included in the response JSON."
        )
        assistant_text = asyncio.run(generate_assistant_reply(session_id, text_input, extra_context=extra))
    else:
        assistant_text = asyncio.run(generate_assistant_reply(session_id, text_input))

    _SESSIONS[session_id].append(ChatMessage(role="assistant", content=assistant_text))

    return jsonify({
        "session_id": session_id,
        "reply": assistant_text,
        "audio_path": audio_path,
        "requested_effects": requested_effects,
        "known_effects": known_effects,
        "unknown_effects": unknown_effects,
        "downstream": {
            "next_backend_url": None,
            "payload": asdict(plan) if plan is not None else None,
        },
        "messages": [asdict(m) for m in _SESSIONS[session_id]],
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
