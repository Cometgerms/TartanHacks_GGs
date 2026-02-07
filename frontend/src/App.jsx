import { useEffect, useRef, useState } from "react";
import "./App.css";

export default function App() {
  const [screen, setScreen] = useState("landing"); // landing | input | progress | result

  const [prompt, setPrompt] = useState("");
  const [file, setFile] = useState(null);

  const [status, setStatus] = useState("idle"); // idle | uploading | done | error
  const [message, setMessage] = useState("");
  const [outputUrl, setOutputUrl] = useState(null);
  const [error, setError] = useState("");

  // progress UI
  const [progress, setProgress] = useState(0);
  const [stepText, setStepText] = useState("");

  const progressTimerRef = useRef(null);
  const abortRef = useRef(null);

  const MIN_PROGRESS_MS = 3500;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  const canSubmit = file && prompt.trim() && status !== "uploading";

  const examples = [
    "clearer voice",
    "delete background noise",
    "professional mix",
    "reduce sibilance",
    "bring up the bass",
    "make it louder (normalize)",
  ];

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

  useEffect(() => {
    return () => {
      stopProgressTimer();
      abortRef.current?.abort();
    };
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!canSubmit) return;

    setScreen("progress");
    setStatus("uploading");
    setError("");
    setMessage("");
    setOutputUrl(null);

    startFakeProgress();
    const startedAt = Date.now();

    try {
      abortRef.current = new AbortController();

      const form = new FormData();
      form.append("audio", file);
      form.append("prompt", prompt);

      const res = await fetch("/api/process", {
        method: "POST",
        body: form,
        signal: abortRef.current.signal,
      });

      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Backend error (${res.status}): ${txt || res.statusText}`);
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);

      const elapsed = Date.now() - startedAt;
      if (elapsed < MIN_PROGRESS_MS) await sleep(MIN_PROGRESS_MS - elapsed);

      stopProgressTimer();
      setProgress(100);
      setStepText("Done!");

      setOutputUrl(url);
      setMessage("Done! Your edited audio is ready.");
      setStatus("done");
      setScreen("result");
    } catch (err) {
      if (err?.name === "AbortError") {
        // user cancelled
        return;
      }

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
      <div className="page">
        <div className="landingWrap">
          <div className="landingInner">
            <h2 className="heroTitle">Edit audio using plain English.</h2>

            <p className="heroSub">
              #1 tool for creators: clean speech for reels/podcasts, quick master for music demos, and other simple edits
              with no need for music editing knowledge.
            </p>

            <button
              className="button landingBtn"
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
    );
  }

  if (screen === "input") {
    return (
      <div className="page">
        <div className="editorPage">
          <div className="editorWrap">
            <div className="hero heroCompact">
              <h2 className="heroTitle">Upload audio & describe the edit.</h2>
            </div>

            <div className="grid oneCol">
              <div className="card">
                <div className="dropRow" style={{ marginBottom: 10 }}>
                  <div className="cardTitle" style={{ margin: 0 }}>
                    Upload audio file
                  </div>
                  <button
                    type="button"
                    className="chip"
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
                      {file ? `Selected: ${file.name}` : "Choose an audio file (mp3/wav/m4a…)"}
                    </div>

                    <div className="filePicker">
                      <input
                        id="audioFile"
                        className="fileHidden"
                        type="file"
                        accept="audio/*"
                        onChange={(e) => setFile(e.target.files?.[0] || null)}
                      />

  <label htmlFor="audioFile" className="fileBtn">
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
                      <button type="button" key={ex} className="chip" onClick={() => setPrompt(ex)}>
                        {ex}
                      </button>
                    ))}
                  </div>

                  <div className="actions">
                    <button
                      className={`button ${canSubmit ? "buttonReady" : ""}`}
                      disabled={!canSubmit}
                    >
                      Process audio
                    </button>

                  </div>

                  <p className="hint">
                    Tip: keep prompts simple. Later the backend can map keywords to EQ, noise reduction, compression,
                    normalize, etc.
                  </p>
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (screen === "progress") {
    return (
      <div className="page">
        <div className="landingWrap">
          <div className="landingInner landingInnerNarrow">
            <h2 className="heroTitle" style={{ marginBottom: 8 }}>
              Processing your audio…
            </h2>
            <p className="heroSub" style={{ marginBottom: 18 }}>
              {stepText || "Working…"}
            </p>

            <div className="card">
              <div className="progressTrack">
                <div className="progressFill" style={{ width: `${progress}%` }} />
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
                  className="chip"
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

              <div className="card" style={{ marginTop: 18 }}>
                {outputUrl && (
                  <>
                    <audio controls src={outputUrl} className="player" />
                    <div className="centerRow" style={{ marginTop: 12 }}>
                      <a className="chip" href={outputUrl} download="edited-audio.wav">
                        Download edited audio
                      </a>
                    </div>
                  </>
                )}
              </div>
            </>
          ) : (
            <>
              <h2 className="heroTitle">Something went wrong.</h2>
              <p className="heroSub">{error || "Unknown error"}</p>

              <div className="card" style={{ marginTop: 18 }}>
                <p className="hint" style={{ margin: 0 }}>
                  If your backend isn’t running yet, this is expected.
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
