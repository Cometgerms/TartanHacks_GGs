import { useEffect, useMemo, useRef, useState } from "react";
import anime from "animejs";
import "./App.css";
import logoUrl from "./assets/Scotty.jpg";


function AudioFileIcon() {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current) return;
    const paths = ref.current.querySelectorAll("path");

    // "Drawable" effect: strokeDashoffset animation
    anime.set(paths, { strokeDashoffset: anime.setDashoffset, opacity: 1 });

    anime({
      targets: paths,
      strokeDashoffset: [anime.setDashoffset, 0],
      easing: "easeInOutSine",
      duration: 1500,
      delay: anime.stagger(150),
      loop: false
    });
  }, []);

  return (
    <svg
      ref={ref}
      className="audioIcon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" stroke="rgba(255,255,255,0.3)" />
      <path d="M14 2v4a2 2 0 0 0 2 2h4" stroke="rgba(255,255,255,0.3)" />
      {/* Colored paths for more fun */}
      <path d="M10 13v4" stroke="var(--accent2)" strokeWidth="2" />
      <path d="M14 12v6" stroke="var(--accent1)" strokeWidth="2" />
      <path d="M6 14v2" stroke="var(--accent3)" strokeWidth="2" />
      <path d="M18 15v-1" stroke="var(--accent3)" strokeWidth="2" />
    </svg>
  );
}

// Split text into spans for staggered animation
function SplitText({ text, className = "", style = {} }) {
  return (
    <div className={`split-text ${className}`} style={{ ...style, display: 'inline-block' }} aria-label={text}>
      {text.split("").map((char, i) => (
        <span
          key={i}
          className="letter"
          style={{
            display: "inline-block",
            whiteSpace: "pre",
            willChange: "transform, opacity",
            // Fix for visibility issues
            color: 'inherit',
            position: 'relative',
            zIndex: 1
          }}
        >
          {char}
        </span>
      ))}
    </div>
  );
}

export default function App() {
  const [screen, setScreen] = useState("landing"); // landing | input | progress | result
  const [prompt, setPrompt] = useState("");
  const [file, setFile] = useState(null);
  const [imageFile, setImageFile] = useState(null); // New state for image
  const [sessionId, setSessionId] = useState(null);

  const [status, setStatus] = useState("idle"); // idle | uploading | done | error
  const [message, setMessage] = useState("");
  const [outputUrl, setOutputUrl] = useState(null);
  const [error, setError] = useState("");
  const [agentReply, setAgentReply] = useState("");

  const progressTimerRef = useRef(null);
  const abortRef = useRef(null);

  // animation refs
  const rootRef = useRef(null);
  const bgStartedRef = useRef(false);

  const fileCardRef = useRef(null);
  const primaryBtnRef = useRef(null);
  const progressFillRef = useRef(null);

  const MIN_PROGRESS_MS = 4000;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  const canSubmit = !!file && (!!prompt.trim() || !!imageFile) && status !== "uploading";

  const examples = useMemo(
    () => [
      "clearer voice",
      "remove background noise",
      "professional mix",
      "reduce sibilance",
      "bring up the bass",
      "make it louder",
    ],
    []
  );

  const [progressMessage, setProgressMessage] = useState("Analyzing audio...");

    const loadingPhrases = [
      "Analyzing audio frequencies...",
      "Applying digital signal processing...",
      "Fine-tuning output levels...",
      "Finalizing your edit..."
    ];

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
    // removed setStepText

    if (clearInputs) {
      setPrompt("");
      setFile(null);
      setImageFile(null);
    }
  }

  //showing progress messages//
  useEffect(() => {
  if (screen !== "progress") return;

  let index = 0;
  const interval = setInterval(() => {
    index = (index + 1) % loadingPhrases.length;
    setProgressMessage(loadingPhrases[index]);
  }, 1000); // Change message every 1.5 seconds

  return () => clearInterval(interval);
}, [screen]);

  // ---------- Mouse-interactive background parallax (stable, no loop conflicts) ----------
  useEffect(() => {
    if (prefersReduced) return;

    const fx = document.querySelector(".bgFX");
    if (!fx) return;

    let raf = 0;

    const onMove = (ev) => {
      const w = window.innerWidth || 1;
      const h = window.innerHeight || 1;
      const x = (ev.clientX / w - 0.5) * 2; // -1..1
      const y = (ev.clientY / h - 0.5) * 2;

      if (raf) return;
      raf = window.requestAnimationFrame(() => {
        raf = 0;

        // Track cursor for follower effect
        document.body.style.setProperty("--cursor-x", `${ev.clientX}px`);
        document.body.style.setProperty("--cursor-y", `${ev.clientY}px`);

        // IMPORTANT: set unitless CSS vars; CSS will multiply by px.
        anime.remove(fx);
        anime({
          targets: fx,
          "--mx": x,
          "--my": y,
          duration: 420,
          easing: "easeOutQuad",
        });
      });
    };

    window.addEventListener("mousemove", onMove, { passive: true });
    return () => {
      window.removeEventListener("mousemove", onMove);
      if (raf) window.cancelAnimationFrame(raf);
    };
  }, [prefersReduced]);

  // ---------- Real progress indeterminate while uploading ----------
  useEffect(() => {
    // No need for percentage fake progress.
    // Keep a minimal timer as a safety to avoid stuck UI if needed later.
    if (status !== "uploading") {
      stopProgressTimer();
      return;
    }

    return () => {
      stopProgressTimer();
    };
  }, [status]);

  // ---------- Background FX (runs once) ----------
  useEffect(() => {
  if (prefersReduced) return;

  // 1. Static Background Elements (Orbs/Grid) - Only start these once
  if (!bgStartedRef.current) {
    bgStartedRef.current = true;

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
  }

  // 2. Mosaic Tiles - Restart/Ensure movement whenever the screen changes
  const mosaicTargets = rootRef.current?.querySelectorAll(".mosaicTile");

  if (mosaicTargets && mosaicTargets.length > 0) {
    // Stop any existing animation on these specific tiles before starting a new one
    anime.remove(mosaicTargets);

    anime({
      targets: mosaicTargets,
      translateX: [0, window.innerWidth + 500],
      duration: () => anime.random(5000, 20000),
      delay: anime.stagger(2500),
      easing: 'linear',
      loop: true
    });
  }
  // Adding 'screen' here ensures the tiles start moving again when you go back to landing
}, [prefersReduced, screen]);

// ---------- Screen entrance animation ----------
useEffect(() => {
  const root = rootRef.current;
  if (!root || prefersReduced) return;

  const screenEl = root.querySelector(".anim-screen");
  const cards = Array.from(root.querySelectorAll(".anim-card"));
  const letters = Array.from(root.querySelectorAll(".letter"));
  const heroSub = Array.from(root.querySelectorAll(".anim-heroSub"));
  const cta = Array.from(root.querySelectorAll(".anim-cta"));

  const targets = [screenEl, ...cards, ...letters, ...heroSub, ...cta].filter(Boolean);

  // Stop any running animations on these elements
  anime.remove(targets);

  // Set initial states explicitly to ensure they are hidden before animation starts
  if (screenEl) anime.set(screenEl, { opacity: 0, translateY: 20 });
  if (letters.length) anime.set(letters, { opacity: 0 }); // Start neutral pos, hidden
  if (heroSub.length) anime.set(heroSub, { opacity: 0, translateY: 15 });
  if (cta.length) anime.set(cta, { opacity: 0, translateY: 20, scale: 0.9 });
  if (cards.length) anime.set(cards, { opacity: 0, translateY: 30 });

  const tl = anime.timeline({
    easing: "easeOutExpo",
    duration: 850,
  });

  // 1. Screen fade in
  if (screenEl) {
    tl.add({
      targets: screenEl,
      opacity: [0, 1],
      translateY: [20, 0],
      duration: 600,
      easing: "easeOutQuad",
    });
  }

  // 2. Letters (Jump & Bounce style)
  if (letters.length) {
    tl.add({
      targets: letters,
      opacity: { value: [0, 1], duration: 100 },
      translateY: [
        { value: -20, duration: 400, easing: 'easeOutCubic' }, // Jump up
        { value: 0, duration: 800, easing: 'easeOutBounce' }   // Bounce down
      ],
      rotate: {
        value: [-15, 0], // Subtle rotation
        duration: 500,
        easing: 'easeOutElastic(1, .8)'
      },
      delay: anime.stagger(40),
    }, "-=400");
  }

  // 3. Subtitle
  if (heroSub.length) {
    tl.add({
      targets: heroSub,
      opacity: [0, 1],
      translateY: [15, 0],
      duration: 600,
    }, "-=600");
  }

  // 4. CTA
  if (cta.length) {
    tl.add({
      targets: cta,
      opacity: [0, 1],
      translateY: [20, 0],
      scale: [0.9, 1],
      duration: 600,
    }, "-=500");
  }


  // 5. Cards
  if (cards.length) {
    tl.add({
      targets: cards,
      opacity: [0, 1],
      translateY: [30, 0],
      delay: anime.stagger(100),
      duration: 700,
    }, "-=600");
  }

  return () => {
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

  // Removed complex logo timeline for cleaner entry
  // Landing CTA visibility safeguard
useEffect(() => {
  if (screen !== "landing") return;
  const root = rootRef.current;
  if (!root) return;

  const btn = root.querySelector(".landingBtn");
  if (!btn) return;

  const ensureVisible = () => {
    const cs = window.getComputedStyle(btn);
    if (cs.opacity === "0") {
      btn.style.opacity = "1";
      btn.style.transform = "none";
    }
  };

  requestAnimationFrame(ensureVisible);
  const id = window.setTimeout(ensureVisible, 900);
  return () => window.clearTimeout(id);
}, [screen]);


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

  // Important: don't let hover cancel the "enter" animation while the button is still at opacity 0.
  // If the cursor is already over the CTA when it mounts, React can fire onMouseEnter immediately.
  anime.remove(t);
  anime.set(t, { opacity: 1, translateY: 0, scale: 1 });

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

  // Same safety as hoverGlow: make sure CTA is visible even if we interrupt the entrance timeline.
  anime.remove(t);
  anime.set(t, { opacity: 1, translateY: 0, scale: 1 });

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
    <div className="cursorFollower" />

    {/* New Mosaic Layer */}
    <div className="mosaicContainer">
      <div className="mosaicTile tile1" />
      <div className="mosaicTile tile2" />
      <div className="mosaicTile tile3" />
      <div className="mosaicTile tile4" />
        <div className="mosaicTile tile5" />
        <div className="mosaicTile tile6" />
        <div className="mosaicTile tile7" />
        <div className="mosaicTile tile8" />
        <div className="mosaicTile tile9" />
        <div className="mosaicTile tile10" />
    </div>

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

    const startedAt = Date.now();

    try {
      abortRef.current = new AbortController();

      const form = new FormData();
      form.append("audio", file);
      if (imageFile) form.append("image", imageFile);
      form.append("text", prompt);
      form.append("session_id", sessionId || `session_${Date.now()}`);

      const res = await fetch("/api/aiagent", {
        method: "POST",
        body: form,
        signal: abortRef.current.signal,
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        const elapsed = Date.now() - startedAt;
        if (elapsed < MIN_PROGRESS_MS) await sleep(MIN_PROGRESS_MS - elapsed);

        // If backend returned an agent reply, show it.
        if (data && (data.reply || data.error)) {
          setAgentReply(data.reply || "");
          setError(data.error || "Could not process your request");
        } else {
          setError(`Backend error (${res.status})`);
        }

        setStatus("error");
        setScreen("result");
        return;
      }

      // success
      setSessionId(data?.session_id || sessionId);
      setAgentReply(data?.reply || "");

      let outputFileUrl = null;
      if (data?.output_audio_path) {
        const filename = String(data.output_audio_path).split(/[/\\]/).pop();
        outputFileUrl = `/uploads/${filename}`;
      }

      const elapsed = Date.now() - startedAt;
      if (elapsed < MIN_PROGRESS_MS) await sleep(MIN_PROGRESS_MS - elapsed);

      setOutputUrl(outputFileUrl);
      setMessage(outputFileUrl ? "Done! Your edited audio is ready." : "Processing complete. See AI assistant reply for details.");
      setStatus("done");
      setScreen("result");
    } catch (err) {
      if (err?.name === "AbortError") return;

      const elapsed = Date.now() - startedAt;
      if (elapsed < MIN_PROGRESS_MS) await sleep(MIN_PROGRESS_MS - elapsed);

      setStatus("error");
      setError(err?.message || "Something went wrong");
      setScreen("result");
    } finally {
      abortRef.current = null;
    }
  }

  // ---------- UI ----------
  if (screen === "landing") {
    return (
      <div className="page" ref={rootRef} key="landing">
        {BackgroundFX}
        <div className="screen anim-screen landingContent">
          <div className="landingWrap">
              <img className="logoImg" src={logoUrl} alt="Scotty Logo" />
            <div className="landingInner">


              {/* Enhanced animated title */}
              <SplitText
                text="Edit audio using plain English."
                className="heroTitle"
              />

              <p className="heroSub anim-heroSub">
                The #1 tool for creators: clean speech for reels/podcasts, quick master for music demos, and other simple edits
                without needing complex software.
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
      <div className="page" ref={rootRef} key="input">
        {BackgroundFX}

        <div className="screen anim-screen">
          <div className="editorPage">
            <div className="editorWrap">
              <div className="hero heroCompact" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <SplitText
                  text="Describe your edit."
                  className="heroTitle"
                  style={{ fontSize: '3rem', margin: 0 }}
                />

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
                  style={{ margin: 0 }}
                >
                  ← Back
                </button>
              </div>

              <form className="editorGrid" onSubmit={handleSubmit}>
                {/* LEFT COL: Files */}
                <div className="card anim-card" style={{ height: '100%' }}>
                  <div className="cardTitle">Source Files</div>

                  <div className="form">
                    <div className="drop">
                      <div className="dropRow">
                         <div className="fileName">Audio File (Required)</div>
                      </div>

                      {/* BIG “physical file” card drops in here */}
                      <div className="fileDropCard fxRing" ref={fileCardRef} style={{ display: "none" }}>
                        <AudioFileIcon key={file?.name || "audio-icon"} />
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

                    {/* Image Upload for Multimodal */}
                    <div className="drop" style={{ borderStyle: 'dotted', borderColor: 'rgba(255,255,255,0.15)' }}>
                      <div className="dropRow">
                        <div className="fileName" style={{ fontSize: 13 }}>
                          Reference Image (Optional)
                        </div>
                        {imageFile && (
                          <button
                            type="button"
                            className="buttonTiny"
                            onClick={() => setImageFile(null)}
                            style={{ padding: '4px 8px', fontSize: 10 }}
                          >
                            Remove
                          </button>
                        )}
                      </div>

                      <div className="filePicker" style={{ marginTop: 12 }}>
                         <input
                          id="imageFile"
                          className="fileHidden"
                          type="file"
                          accept="image/*"
                          onChange={(e) => setImageFile(e.target.files?.[0] || null)}
                        />
                         <label
                          htmlFor="imageFile"
                          className="fileBtn fxRing"
                          style={{ fontSize: 13, padding: '6px 14px' }}
                          onMouseDown={pressPop}
                        >
                          {imageFile ? "Change Image" : "Add Photo"}
                        </label>

                        {imageFile ? (
                           <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                             <img
                               src={URL.createObjectURL(imageFile)}
                               alt="preview"
                               style={{ width: 44, height: 44, borderRadius: 8, objectFit: 'cover', border: '1px solid rgba(255,255,255,0.2)' }}
                             />
                             <span className="fileMeta" style={{ fontSize: 12 }}>{imageFile.name}</span>
                           </div>
                        ) : (
                           <span className="fileMeta" style={{ fontSize: 13, fontStyle: 'italic', opacity: 0.7 }}>
                             e.g. "Photo of a concert hall"
                           </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* RIGHT COL: Prompt & Actions */}
                <div className="card anim-card" style={{ display: 'flex', flexDirection: 'column', height: '100%', animationDelay: '0.15s' }}>
                  <div className="cardTitle">Text Input</div>

                  <div className="form" style={{ height: '100%' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>

                      <textarea
                        className="textarea"
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        placeholder='Examples: "remove background noise", "make it sound like this photo", "add reverb"'
                        style={{ flex: 1, minHeight: 180, marginTop: 8 }}
                      />
                    </div>

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

                    <div className="actions" style={{ marginTop: 'auto', paddingTop: 16 }}>
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
                  </div>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (screen === "progress") {
    return (
      <div className="page" ref={rootRef} key="progress">
        {BackgroundFX}

        <div className="screen anim-screen">
          <div className="landingWrap">
            <div className="landingInner landingInnerNarrow">
              <h2 className="heroTitle anim-heroTitle" style={{ marginBottom: 8 }}>
                Processing your audio…
              </h2>
              <p className="heroSub anim-heroSub" style={{ marginBottom: 18, fontWeight: '500', color: 'var(--accent2)' }}>
                  {progressMessage}
              </p>

              <div className={`card anim-card progressCard fxScan ${status === "uploading" ? "loadingGlow" : ""}`}>
                <div className="progressTrack indeterminate">
                  <div className="progressIndeterminate" />
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

                <p className="hint">(Thank you for your patience)</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // result
  return (
    <div className="page" ref={rootRef} key="result">
      {BackgroundFX}

      <div className="screen anim-screen">
        <div className="landingWrap">
          <div className="landingInner landingInnerNarrow">
            <div className="resultShell resultBlock">
              <div className="resultHeader">
                <div className={`badge ${status === "done" ? "ok" : status === "error" ? "err" : ""}`}>
                  {status === "done" ? "SUCCESS" : status === "error" ? "ERROR" : "STATUS"}
                </div>

                <h2 className="heroTitle" style={{ marginTop: 10 }}>
                  {status === "done" ? "Your edited audio is ready." : "Something went wrong."}
                </h2>

                <p className="heroSub" style={{ marginTop: 8 }}>
                  {status === "done" ? (message || "Done!") : (error || "Unknown error")}
                </p>
              </div>

              <div className="resultBody">
                {status === "done" ? (
                  <div className="resultGrid">
                    <div className="card resultBlock">
                      <div className="cardTitle">Output</div>
                      {outputUrl ? (
                        <>
                          <audio controls src={outputUrl} className="player" />
                          <div className="centerRow" style={{ marginTop: 14 }}>
                            <a
                              className="buttonTiny fxRing"
                              href={outputUrl}
                              download="edited-audio.wav"
                              style={{ display: 'inline-flex', alignItems: 'center', gap: '10px' }}
                            >
                              Download
                              {/* The SVG is now after the text */}
                              <svg
                                width="18"
                                height="18"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2.5"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                style={{ flexShrink: 0 }} // This prevents the "distorted/squished" look
                              >
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                                <polyline points="7 10 12 15 17 10" />
                                <line x1="12" y1="15" x2="12" y2="3" />
                              </svg>
                            </a>
                          </div>
                        </>
                      ) : (
                        <p className="hint" style={{ margin: 0 }}>
                          No output audio generated.
                        </p>
                      )}
                    </div>

                    <div className="card resultBlock">
                      <div className="cardTitle">Details</div>
                      {agentReply ? (
                        <p className="detailsText">{agentReply}</p>
                      ) : (
                        <p className="hint" style={{ margin: 0 }}>
                          (No assistant message.)
                        </p>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="card resultBlock">
                    <div className="cardTitle">What happened</div>
                    <p className="detailsText">
                      {agentReply || "If your backend isn’t running, this is expected."}
                    </p>
                  </div>
                )}

                <div className="resultActions resultBlock">
                  <button
                    className="buttonTiny fxRing"
                    onMouseDown={pressPop}
                    onMouseEnter={hoverGlow}
                    onMouseLeave={hoverGlowOut}
                    onClick={() => {
                      resetJob({ clearInputs: true });
                      setScreen("input");
                    }}
                  >
                    Process another file
                  </button>

                  <button
                    className="buttonTiny fxRing"
                    onMouseDown={pressPop}
                    onMouseEnter={hoverGlow}
                    onMouseLeave={hoverGlowOut}
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
        </div>
      </div>
    </div>
  );
}
