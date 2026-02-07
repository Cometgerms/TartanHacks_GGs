import { useEffect, useMemo, useRef, useState } from "react";
import anime from "animejs";
import "./App.css";
import logoUrl from "./assets/Scotty.jpg";


function AudioFileIcon() {
  // Simple inline SVG "audio file" icon
  return (
    <svg
      className="audioIcon"
      viewBox="0 0 64 64"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M18 8h18l10 10v38a4 4 0 0 1-4 4H18a4 4 0 0 1-4-4V12a4 4 0 0 1 4-4Z"
        stroke="rgba(255,255,255,0.55)"
        strokeWidth="2"
      />
      <path
        d="M36 8v10h10"
        stroke="rgba(255,255,255,0.55)"
        strokeWidth="2"
      />
      <path
        d="M26 43c0 2.2-2 4-4.5 4S17 45.2 17 43s2-4 4.5-4S26 40.8 26 43Z"
        stroke="rgba(255,255,255,0.65)"
        strokeWidth="2"
      />
      <path
        d="M26 43V26l20-4v16"
        stroke="rgba(255,255,255,0.65)"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <path
        d="M46 38c0 2.2-2 4-4.5 4S37 40.2 37 38s2-4 4.5-4S46 35.8 46 38Z"
        stroke="rgba(255,255,255,0.65)"
        strokeWidth="2"
      />
    </svg>
  );
}

export default function App() {
  const [screen, setScreen] = useState("landing"); // landing | input | progress | result
  const [prompt, setPrompt] = useState("");
  const [file, setFile] = useState(null);
  const [sessionId, setSessionId] = useState(null);

  const [status, setStatus] = useState("idle"); // idle | uploading | done | error
  const [message, setMessage] = useState("");
  const [outputUrl, setOutputUrl] = useState(null);
  const [error, setError] = useState("");
  const [agentReply, setAgentReply] = useState("");

  const fileInputRef = useRef(null);

  // progress UI
  const [progress, setProgress] = useState(0);
  const [stepText, setStepText] = useState("");

  const progressTimerRef = useRef(null);
  const abortRef = useRef(null);

  // animation refs
  const rootRef = useRef(null);
  const bgStartedRef = useRef(false);

  const fileCardRef = useRef(null);
  const primaryBtnRef = useRef(null);
  const progressFillRef = useRef(null);

  const MIN_PROGRESS_MS = 3500;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  const canSubmit = !!file && !!prompt.trim() && status !== "uploading";

  const examples = useMemo(
    () => [
      "clearer voice",
      "delete background noise",
      "professional mix",
      "reduce sibilance",
      "bring up the bass",
      "make it louder (normalize)",
    ],
    []
  );

  const prefersReduced =
    window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ?? false;

  function stopProgressTimer() {
    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
  }

  function resetJob({ clearInputs = false } = {}) {
    stopProgressTimer();
    abortRef.current?.abort();
    abortRef.current = null;

    setStatus("idle");
    setMessage("");
    setOutputUrl(null);
    setError("");
    setProgress(0);
    setStepText("");

    if (clearInputs) {
      setPrompt("");
      setFile(null);
    }
  }

  function startFakeProgress() {
    stopProgressTimer();

    const steps = [
      { at: 8, text: "Uploading audio…" },
      { at: 18, text: "Analyzing signal…" },
      { at: 35, text: "Deleting background noise…" },
      { at: 55, text: "Adding compression…" },
      { at: 70, text: "Adding reverb…" },
      { at: 85, text: "Normalizing loudness…" },
      { at: 95, text: "Exporting edited audio…" },
    ];

    let p = 2;
    setProgress(2);
    setStepText("Starting…");

    progressTimerRef.current = setInterval(() => {
      p = Math.min(98, p + 2);
      setProgress(p);

      const current = [...steps].reverse().find((s) => p >= s.at);
      if (current) setStepText(current.text);
    }, 180);
  }

  // ---------- Background FX (runs once) ----------
  useEffect(() => {
    if (bgStartedRef.current) return;
    bgStartedRef.current = true;
    if (prefersReduced) return;

    const orb1 = document.querySelector(".bgOrb.orb1");
    const orb2 = document.querySelector(".bgOrb.orb2");
    const grid = document.querySelector(".bgGrid");

    if (orb1) {
      anime({
        targets: orb1,
        translateX: [-80, 120],
        translateY: [-60, 90],
        rotate: [-10, 18],
        duration: 18000,
        easing: "easeInOutSine",
        direction: "alternate",
        loop: true,
      });
    }

    if (orb2) {
      anime({
        targets: orb2,
        translateX: [120, -140],
        translateY: [90, -110],
        rotate: [12, -16],
        duration: 21000,
        easing: "easeInOutSine",
        direction: "alternate",
        loop: true,
      });
    }

    if (grid) {
      anime({
        targets: grid,
        opacity: [0.06, 0.18],
        duration: 5200,
        easing: "easeInOutSine",
        direction: "alternate",
        loop: true,
      });
    }
  }, [prefersReduced]);

// ---------- Screen entrance animation ----------
useEffect(() => {
  const root = rootRef.current;
  if (!root || prefersReduced) return;

  // only stop animations inside this screen
  const screenEl = root.querySelector(".anim-screen");
  const cards = Array.from(root.querySelectorAll(".anim-card"));

  const heroTitle = Array.from(root.querySelectorAll(".anim-heroTitle"));
  const heroSub = Array.from(root.querySelectorAll(".anim-heroSub"));
  const cta = Array.from(root.querySelectorAll(".anim-cta")); // <-- CTA separate

  const targets = [screenEl, ...cards, ...heroTitle, ...heroSub, ...cta].filter(Boolean);

  anime.remove(targets);

  // Clear leftover inline styles that can get stuck
  targets.forEach((el) => {
    el.style.removeProperty("transform");
    el.style.removeProperty("filter");
    // DO NOT clear opacity for CTA because CSS locks it to 1 anyway
    if (!el.classList.contains("anim-cta")) el.style.removeProperty("opacity");
  });

  const tl = anime.timeline({ autoplay: true });

  if (screenEl) {
    tl.add({
      targets: screenEl,
      opacity: [0, 1],
      translateY: [14, 0],
      duration: 380,
      easing: "easeOutCubic",
    });
  }

  // Title/Sub fade in (fine)
  tl.add(
    {
      targets: [...heroTitle, ...heroSub],
      opacity: [0, 1],
      translateY: [18, 0],
      delay: anime.stagger(110),
      duration: 650,
      easing: "easeOutExpo",
    },
    40
  );

  // CTA: move/scale only (NO opacity)
  tl.add(
    {
      targets: cta,
      translateY: [18, 0],
      scale: [0.98, 1],
      duration: 520,
      easing: "easeOutExpo",
    },
    120
  );

  if (cards.length) {
    tl.add(
      {
        targets: cards,
        opacity: [0, 1],
        translateY: [16, 0],
        delay: anime.stagger(100),
        duration: 560,
        easing: "easeOutQuad",
      },
      70
    );
  }

  return () => {
    tl.pause();
    anime.remove(targets);
  };
}, [screen, prefersReduced]);


  // ---------- File card “drops in” when you choose a file ----------
  useEffect(() => {
    if (prefersReduced) return;
    if (screen !== "input") return;

    const card = fileCardRef.current;
    if (!card) return;

    anime.remove(card);

    if (file) {
      // Make sure it's visible before animating
      card.style.display = "flex";

      anime({
        targets: card,
        opacity: [0, 1],
        translateY: [-18, 0],
        rotate: [-2, 0],
        scale: [0.98, 1],
        duration: 720,
        easing: "easeOutElastic(1, .6)",
      });

      // “spark” along the border
      anime({
        targets: card,
        boxShadow: [
          "0 12px 40px rgba(0,0,0,0.35)",
          "0 18px 70px rgba(130,120,255,0.18)",
          "0 12px 40px rgba(0,0,0,0.35)",
        ],
        duration: 900,
        easing: "easeOutQuad",
      });
    } else {
      // Hide gracefully
      anime({
        targets: card,
        opacity: [1, 0],
        translateY: [0, -10],
        duration: 220,
        easing: "easeOutQuad",
        complete: () => {
          card.style.display = "none";
        },
      });
    }
  }, [file, screen, prefersReduced]);

  // ---------- Ready button “charge up” when valid ----------
  useEffect(() => {
    const btn = primaryBtnRef.current;
    if (!btn || prefersReduced) return;

    anime.remove(btn);

    if (screen === "input" && canSubmit) {
      anime({
        targets: btn,
        scale: [1, 1.02, 1],
        duration: 900,
        easing: "easeInOutSine",
        loop: true,
      });

      // Quick “ready flash”
      anime({
        targets: btn,
        filter: ["brightness(1)", "brightness(1.18)", "brightness(1)"],
        duration: 420,
        easing: "easeOutQuad",
      });
    }
  }, [screen, canSubmit, prefersReduced]);

  // ---------- Progress shimmer ----------
  useEffect(() => {
    const el = progressFillRef.current;
    if (!el || prefersReduced) return;

    anime.remove(el);

    if (screen === "progress" && status === "uploading") {
      anime({
        targets: el,
        backgroundPositionX: ["0%", "180%"],
        duration: 1400,
        easing: "linear",
        loop: true,
      });
    }
  }, [screen, status, prefersReduced]);

  // ---------- Cleanup ----------
  useEffect(() => {
    return () => {
      stopProgressTimer();
      abortRef.current?.abort();
    };
  }, []);

  useEffect(() => {
  if (screen !== "landing") return;
  if (prefersReduced) return;

  const root = rootRef.current;
  if (!root) return;

  const logo = root.querySelector(".logoImg");
  const stage = root.querySelector(".logoStage");
  const content = root.querySelector(".landingContent");

  if (!logo || !stage || !content) return;

  // reset (prevents “stuck” states on fast navigation)
  anime.remove([logo, content, stage]);
  logo.style.opacity = "0";
  content.style.opacity = "0";

  const tl = anime.timeline({ autoplay: true });

  // drop-in
  tl.add({
    targets: logo,
    opacity: [0, 1],
    translateY: [-40, 0],
    scale: [0.9, 1],
    rotate: [-6, 0],
    duration: 900,
    easing: "easeOutElastic(1, .6)",
  });

  // move to top-left corner
  tl.add({
    targets: logo,
    translateX: [0, -((window.innerWidth / 2) - 70)],  // tweak "70" for padding
    translateY: [0, -((window.innerHeight / 2) - 70)],
    scale: [1, 0.78],
    duration: 750,
    easing: "easeInOutCubic",
  }, "+=120");

  // reveal landing content
  tl.add({
    targets: content,
    opacity: [0, 1],
    duration: 450,
    easing: "easeOutQuad",
  }, "-=250");

  // optionally fade the stage away so it stops covering layout
  tl.add({
    targets: stage,
    opacity: [1, 0],
    duration: 300,
    easing: "easeOutQuad",
    complete: () => {
      stage.style.display = "none";
    },
  }, "-=200");

  return () => {
    anime.remove([logo, content, stage]);
    stage.style.display = ""; // restore if you come back later
    stage.style.opacity = "";
  };
}, [screen, prefersReduced]);

  // ---------- Interaction helpers ----------
  function pressPop(e) {
    const t = e?.currentTarget;
    if (!t || prefersReduced) return;
    anime.remove(t);
    anime({
      targets: t,
      scale: [1, 0.97, 1],
      duration: 220,
      easing: "easeOutQuad",
    });
  }

  function hoverGlow(e) {
    const t = e?.currentTarget;
    if (!t || prefersReduced) return;
    anime.remove(t);
    anime({
      targets: t,
      boxShadow: [
        "0 0 0 rgba(0,0,0,0)",
        "0 18px 60px rgba(130,120,255,0.16)",
      ],
      duration: 260,
      easing: "easeOutQuad",
    });
  }

  function hoverGlowOut(e) {
    const t = e?.currentTarget;
    if (!t || prefersReduced) return;
    anime.remove(t);
    anime({
      targets: t,
      boxShadow: [
        "0 18px 60px rgba(130,120,255,0.16)",
        "0 0 0 rgba(0,0,0,0)",
      ],
      duration: 260,
      easing: "easeOutQuad",
    });
  }

  // ---------- Background FX markup ----------
  const BackgroundFX = (
    <div className="bgFX" aria-hidden="true">
      <div className="bgOrb orb1" />
      <div className="bgOrb orb2" />
      <div className="bgGrid" />
      <div className="bgNoise" />
    </div>
  );

  async function handleSubmit(e) {
    e.preventDefault();
    if (!canSubmit) return;

    setScreen("progress");
    setStatus("uploading");
    setError("");
    setMessage("");
    setOutputUrl(null);
    setAgentReply("");

    startFakeProgress();
    const startedAt = Date.now();

    try {
      abortRef.current = new AbortController();

      const form = new FormData();
      form.append("audio", file);
      form.append("text", prompt);
      form.append("session_id", sessionId || `session_${Date.now()}`);

      const res = await fetch("/api/aiagent", {
        method: "POST",
        body: form,
        signal: abortRef.current.signal,
      });

      if (!res.ok) {
        // Try to parse JSON error response first
        let errorData = null;
        try {
          errorData = await res.json();
        } catch {
          const txt = await res.text().catch(() => "");
          throw new Error(`Backend error (${res.status}): ${txt || res.statusText}`);
        }

        // If we got a JSON error response with AI reply, handle it specially
        if (errorData && errorData.reply) {
          const elapsed = Date.now() - startedAt;
          if (elapsed < MIN_PROGRESS_MS) await sleep(MIN_PROGRESS_MS - elapsed);

          stopProgressTimer();
          setProgress(100);
          setStepText("Error");

          setAgentReply(errorData.reply);
          setError(errorData.error || "Could not process your request");
          setStatus("error");
          setScreen("result");
          return;
        }

        // Otherwise throw normal error
        throw new Error(`Backend error (${res.status}): ${errorData?.error || res.statusText}`);
      }

      const data = await res.json();
      setSessionId(data.session_id || sessionId);
      setAgentReply(data.reply || "");

      // Get output audio URL from backend response
      let outputFileUrl = null;
      if (data.output_audio_path) {
        // If it's just a filename, construct full URL
        const filename = data.output_audio_path.split(/[/\\]/).pop();
        outputFileUrl = `/uploads/${filename}`;
      }

      // Log debug info to console
      console.log("Backend response:", {
        session_id: data.session_id,
        output_audio_path: data.output_audio_path,
        outputFileUrl,
        known_effects: data.known_effects,
        audio_engine_ran: data.audio_engine?.ran,
        generated_code: data.downstream?.generated_code
      });

      const elapsed = Date.now() - startedAt;
      if (elapsed < MIN_PROGRESS_MS) await sleep(MIN_PROGRESS_MS - elapsed);

      stopProgressTimer();
      setProgress(100);
      setStepText("Done!");

      setOutputUrl(outputFileUrl);
      setMessage(outputFileUrl ? "Done! Your edited audio is ready." : "Processing complete. See agent reply for details.");
      setStatus("done");
      setScreen("result");
    } catch (err) {
      if (err?.name === "AbortError") return;

      const elapsed = Date.now() - startedAt;
      if (elapsed < MIN_PROGRESS_MS) await sleep(MIN_PROGRESS_MS - elapsed);

      stopProgressTimer();
      setStatus("error");
      setError(err?.message || "Something went wrong");
      setStepText("Error");
      setScreen("result");
    } finally {
      abortRef.current = null;
    }
  }

  // ---------- UI ----------
  if (screen === "landing") {
    return (
      <div className="page" ref={rootRef}>
        {BackgroundFX}
          <div className="logoStage" aria-hidden="true">
            <img className="logoImg" src={logoUrl} alt="" />
        </div>
        <div className="screen anim-screen landingContent">
          <div className="landingWrap">
            <div className="landingInner">
              <h2 className="heroTitle anim-heroTitle">Edit audio using plain English.</h2>

              <p className="heroSub anim-heroSub">
                #1 tool for creators: clean speech for reels/podcasts, quick master for music demos, and other simple edits
                with no need for music editing knowledge.
              </p>

              <button
                className="button landingBtn fxRing anim-cta"
                onMouseDown={pressPop}
                onMouseEnter={hoverGlow}
                onMouseLeave={hoverGlowOut}
                onClick={() => {
                  resetJob({ clearInputs: false });
                  setScreen("input");
                }}
              >
                Get started
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (screen === "input") {
    return (
      <div className="page" ref={rootRef}>
        {BackgroundFX}

        <div className="screen anim-screen">
          <div className="editorPage">
            <div className="editorWrap">
              <div className="hero heroCompact">
                <h2 className="heroTitle anim-heroTitle">Upload audio and describe the edit.</h2>
              </div>

              <div className="grid oneCol">
                <div className="card anim-card">
                  <div className="dropRow" style={{ marginBottom: 10 }}>
                    <div className="cardTitle" style={{ margin: 0 }}>
                      Upload audio file
                    </div>

                    <button
                      type="button"
                      className="chip fxRing"
                      onMouseDown={pressPop}
                      onMouseEnter={hoverGlow}
                      onMouseLeave={hoverGlowOut}
                      onClick={() => {
                        resetJob({ clearInputs: false });
                        setScreen("landing");
                      }}
                    >
                      ← Back
                    </button>
                  </div>

                  <form className="form" onSubmit={handleSubmit}>
                    <div className="drop">
                      <div className="fileName">
                        {file ? `Selected: ${file.name}` : "Upload an audio file (mp3/wav/m4a…)"}
                      </div>

                      {/* BIG “physical file” card drops in here */}
                      <div className="fileDropCard fxRing" ref={fileCardRef} style={{ display: "none" }}>
                        <AudioFileIcon />
                        <div className="fileDropText">
                          <div className="fileDropTop">Audio file loaded</div>
                          <div className="fileDropName">{file?.name || ""}</div>
                        </div>
                        <span className="fileDropPill">READY</span>
                      </div>

                      <div className="filePicker">
                        <input
                          id="audioFile"
                          className="fileHidden"
                          type="file"
                          accept="audio/*"
                          onChange={(e) => setFile(e.target.files?.[0] || null)}
                        />

                        <label
                          htmlFor="audioFile"
                          className="fileBtn fxRing"
                          onMouseDown={pressPop}
                          onMouseEnter={hoverGlow}
                          onMouseLeave={hoverGlowOut}
                        >
                          {file ? "Change file" : "Choose file"}
                        </label>

                        <span className="fileMeta" title={file?.name || ""}>
                          {file ? file.name : "No file selected"}
                        </span>
                      </div>
                    </div>

                    <label className="label">
                      Edit prompt
                      <textarea
                        className="textarea"
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        placeholder='Examples: "clearer voice", "delete background noise", "professional mix"'
                      />
                    </label>

                    <div className="chips">
                      {examples.map((ex) => (
                        <button
                          type="button"
                          key={ex}
                          className="chip fxRing"
                          onMouseDown={pressPop}
                          onMouseEnter={hoverGlow}
                          onMouseLeave={hoverGlowOut}
                          onClick={() => setPrompt(ex)}
                        >
                          {ex}
                        </button>
                      ))}
                    </div>

                    <div className="actions">
                      <button
                        ref={primaryBtnRef}
                        className={`button fxRing ${canSubmit ? "buttonReady" : ""}`}
                        disabled={!canSubmit}
                        onMouseDown={pressPop}
                        onMouseEnter={hoverGlow}
                        onMouseLeave={hoverGlowOut}
                      >
                        Process audio
                      </button>
                    </div>

                    <p className="hint">Tip: loosely describe what you want — we’ll handle the details.</p>
                  </form>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (screen === "progress") {
    return (
      <div className="page" ref={rootRef}>
        {BackgroundFX}

        <div className="screen anim-screen">
          <div className="landingWrap">
            <div className="landingInner landingInnerNarrow">
              <h2 className="heroTitle anim-heroTitle" style={{ marginBottom: 8 }}>
                Processing your audio…
              </h2>

              <p className="heroSub anim-heroSub" style={{ marginBottom: 18 }}>
                {stepText || "Working…"}
              </p>

              <div className="card anim-card progressCard fxScan">
                <div className="progressTrack">
                  <div ref={progressFillRef} className="progressFill" style={{ width: `${progress}%` }} />
                </div>

                <div className="kv">
                  <div className="kvRow">
                    <span>Progress</span>
                    <span className="code">{progress}%</span>
                  </div>
                  <div className="kvRow">
                    <span>Status</span>
                    <span className="code">{status}</span>
                  </div>
                </div>

                <div className="centerRow">
                  <button
                    type="button"
                    className="chip fxRing"
                    onMouseDown={pressPop}
                    onMouseEnter={hoverGlow}
                    onMouseLeave={hoverGlowOut}
                    onClick={() => {
                      resetJob({ clearInputs: false });
                      setScreen("input");
                    }}
                  >
                    Cancel
                  </button>
                </div>

                <p className="hint">(Progress messages are simulated for demo right now.)</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // result
  return (
    <div className="page">
      <div className="landingWrap">
        <div className="landingInner landingInnerNarrow">
          {status === "done" ? (
            <>
              <h2 className="heroTitle">Your edited audio is ready.</h2>
              <p className="heroSub">{message || "Done!"}</p>

              {agentReply && (
                <div className="card" style={{ marginTop: 18, marginBottom: 12 }}>
                  <div className="cardTitle">AI Assistant</div>
                  <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{agentReply}</p>
                </div>
              )}

              <div className="card" style={{ marginTop: 18 }}>
                {outputUrl ? (
                  <>
                    <audio controls src={outputUrl} className="player" />
                    <div className="centerRow" style={{ marginTop: 12 }}>
                      <a className="chip" href={outputUrl} download="edited-audio.wav">
                        Download edited audio
                      </a>
                    </div>
                  </>
                ) : (
                  <p className="hint" style={{ margin: 0 }}>
                    No output audio generated. See AI assistant reply above.
                  </p>
                )}
              </div>
            </>
          ) : (
            <>
              <h2 className="heroTitle">Something went wrong.</h2>
              <p className="heroSub">{error || "Unknown error"}</p>

              {agentReply && (
                <div className="card" style={{ marginTop: 18 }}>
                  <div className="cardTitle">AI Assistant</div>
                  <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{agentReply}</p>
                </div>
              )}

              <div className="card" style={{ marginTop: 18 }}>
                <p className="hint" style={{ margin: 0 }}>
                  If your backend isn't running yet, this is expected.
                </p>
              </div>
            </>
          )}

          <div className="centerRow" style={{ marginTop: 18 }}>
            <button
              className="chip"
              onClick={() => {
                resetJob({ clearInputs: true });
                setScreen("input");
              }}
            >
              Process another file
            </button>

            <button
              className="chip"
              onClick={() => {
                resetJob({ clearInputs: true });
                setScreen("landing");
              }}
            >
              Back to landing
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
