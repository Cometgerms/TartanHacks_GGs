import { useState } from "react";
import "./App.css";

export default function App() {
  const [page, setPage] = useState("landing"); // landing | editor

  const [prompt, setPrompt] = useState("");
  const [file, setFile] = useState(null);

  const [status, setStatus] = useState("idle"); // idle | uploading | done | error
  const [message, setMessage] = useState("");
  const [outputUrl, setOutputUrl] = useState(null);
  const [error, setError] = useState("");

  const canSubmit = file && prompt.trim() && status !== "uploading";

  const examples = [
    "clearer voice",
    "delete background noise",
    "professional mix",
    "reduce sibilance",
    "bring up the bass",
    "make it louder (normalize)",
  ];

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus("uploading");
    setError("");
    setMessage("");
    setOutputUrl(null);

    try {
      const form = new FormData();
      form.append("audio", file);
      form.append("prompt", prompt);

      const res = await fetch("/api/process", { method: "POST", body: form });

      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Backend error (${res.status}): ${txt || res.statusText}`);
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);

      setOutputUrl(url);
      setMessage("Done! Edited audio received.");
      setStatus("done");
    } catch (err) {
      setStatus("error");
      setError(err.message || "Something went wrong");
    }
  }

  return (
    <div className="page">
      {page === "landing" ? (
  <div
    style={{
      width: "1440px",          // hardcoded to laptop-ish width
      height: "900px",          // hardcoded height
      margin: "0 auto",         // centers the whole “canvas”
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "0 24px",
    }}
  >
    <div style={{ maxWidth: "720px", textAlign: "center" }}>
      <h2 className="heroTitle" style={{ margin: "0 0 10px" }}>
        Edit audio using plain English.
      </h2>

      <p className="heroSub" style={{ margin: "0 auto 18px", maxWidth: "62ch" }}>
        #1 tool for creators: clean speech for reels/podcasts, quick master for music demos, and other simple edits
        with no need for sound editing knowledge.
      </p>

      <button className="button landingBtn" onClick={() => setPage("editor")}>
        Get started
      </button>
    </div>
  </div>
) : (

        <div className="editorWrap">
          <div className="hero">
            <h2 className="heroTitle">Make audio edits using plain English.</h2>
            <p className="heroSub">
              Great for creators: clean speech for reels/podcasts, quick “mix polish” for demos, and other simple edits
              without a DAW workflow.
            </p>
          </div>

          <div className="grid">
            <div className="card">
              <div className="cardTitle">Input</div>

              <form className="form" onSubmit={handleSubmit}>
                <div className="drop">
                  <div className="dropRow">
                    <div className="fileName">
                      {file ? `Selected: ${file.name}` : "Choose an audio file (mp3/wav/m4a…)"}
                    </div>
                    <button type="button" className="chip" onClick={() => setPage("landing")}>
                      ← Back
                    </button>
                  </div>

                  <input
                    className="inputFile"
                    type="file"
                    accept="audio/*"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                  />
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
                      className="chip"
                      onClick={() => setPrompt(ex)}
                      title="Use this prompt"
                    >
                      {ex}
                    </button>
                  ))}
                </div>

                <div className="actions">
                  <button className="button" disabled={!canSubmit}>
                    {status === "uploading" ? "Processing…" : "Process audio"}
                  </button>
                </div>

                <p className="hint">
                  Tip: keep prompts simple. Your backend can map keywords to EQ, noise reduction, compression, normalize,
                  etc.
                </p>
              </form>
            </div>

            <div className="card">
              <div className="cardTitle">Output</div>

              {status === "idle" && <p className="statusLine">Waiting for input.</p>}
              {status === "uploading" && <p className="statusLine">Sending to backend…</p>}

              {status === "done" && (
                <>
                  <p className="statusLine done">{message || "Done!"}</p>
                  {outputUrl && <audio controls src={outputUrl} className="player" />}
                </>
              )}

              {status === "error" && (
                <>
                  <p className="statusLine error">Error</p>
                  <p className="statusLine">{error}</p>
                  <p className="hint">If your backend isn’t running yet, this is expected.</p>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
