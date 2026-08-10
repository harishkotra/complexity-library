"use client";

import { FormEvent, useMemo, useState } from "react";

type Complexity = "O(1)" | "O(log n)" | "O(n)" | "O(n log n)" | "O(n²)" | "O(2ⁿ)" | "unknown";
type VizType = "constant" | "linear_scan" | "logarithmic_halving" | "n_log_n" | "quadratic_grid" | "recursion_tree";

type Result = {
  analysis: { time_complexity: Complexity; space_complexity: string; confidence: number; reasoning: string; assumptions: string[]; limitations: string[]; pattern: string };
  visualization: { type: VizType; input_size: number; operation_estimate: number; accessible_summary: string };
  stages: string[];
  function: { title: string; language: string };
};

function operationEstimate(complexity: Complexity, inputSize: number) {
  switch (complexity) {
    case "O(1)": return 3;
    case "O(log n)": return Math.max(1, Math.ceil(Math.log2(inputSize)));
    case "O(n)": return inputSize;
    case "O(n log n)": return inputSize * Math.max(1, Math.ceil(Math.log2(inputSize)));
    case "O(n²)": return inputSize * inputSize;
    case "O(2ⁿ)": return 2 ** Math.min(inputSize, 20);
    default: return inputSize;
  }
}

const sample = `def contains_duplicate(items):
    for left in range(len(items)):
        for right in range(left + 1, len(items)):
            if items[left] == items[right]:
                return True
    return False`;

const stages = ["Parsing function", "Building syntax facts", "Detecting loops and recursion", "Determining complexity", "Building visualization"];
const serverStageIndex: Record<string, number> = { "Parsed function": 0, "Built syntax facts": 1, "Detected loops and recursion": 2, "Determined complexity": 3, "Built visualization": 4 };

function Visualization({ type, size }: { type: VizType; size: number }) {
  if (type === "quadratic_grid") return <div className="viz-grid" aria-hidden="true">{Array.from({ length: Math.min(64, size * size) }, (_, index) => <span className={index % (Math.min(size, 8) + 1) === 0 ? "hot" : ""} key={index} />)}</div>;
  if (type === "logarithmic_halving") return <div className="viz-halving" aria-hidden="true">{[size, Math.max(1, Math.floor(size / 2)), Math.max(1, Math.floor(size / 4)), 1].map((value, index) => <div key={`${value}-${index}`}><b>{value}</b>{index < 3 && <span>↓</span>}</div>)}</div>;
  if (type === "n_log_n") return <div className="viz-levels" aria-hidden="true">{[1, 2, 4, 8].map((count, row) => <div key={count}>{Array.from({ length: count }, (_, index) => <span key={index} style={{ opacity: 1 - row * 0.14 }} />)}</div>)}</div>;
  if (type === "recursion_tree") return <div className="viz-tree" aria-hidden="true">{[1, 2, 4, 8].map((count, row) => <div key={count}>{Array.from({ length: count }, (_, index) => <span key={index} className={row === 3 ? "leaf" : ""} />)}</div>)}</div>;
  if (type === "constant") return <div className="viz-line constant" aria-hidden="true">{[0, 1, 2].map((item) => <span key={item} />)}</div>;
  return <div className="viz-line" aria-hidden="true">{Array.from({ length: Math.min(size, 18) }, (_, index) => <span key={index} className={index === 7 ? "hot" : ""} />)}</div>;
}

export function AnalyzerWorkbench() {
  const [code, setCode] = useState(sample);
  const [language, setLanguage] = useState("python");
  const [title, setTitle] = useState("Duplicate value check");
  const [stage, setStage] = useState(-1);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [size, setSize] = useState(8);
  const estimated = useMemo(() => result ? operationEstimate(result.analysis.time_complexity, size) : 0, [result, size]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(""); setResult(null); setStage(0);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const response = await fetch(`${apiUrl}/api/functions/analyses`, {
        method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify({ language, code, title }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Analysis could not start.");
      await new Promise<void>((resolve, reject) => {
        const events = new EventSource(`${apiUrl}${payload.events_url}`, { withCredentials: true });
        events.addEventListener("stage", (message) => {
          const stageEvent = JSON.parse(message.data) as { label: string };
          setStage(serverStageIndex[stageEvent.label] ?? 0);
        });
        events.addEventListener("completed", (message) => {
          setResult(JSON.parse(message.data) as Result); setStage(stages.length); events.close(); resolve();
        });
        events.addEventListener("failed", (message) => {
          const failure = JSON.parse(message.data) as { message: string };
          events.close(); reject(new Error(failure.message));
        });
        events.onerror = () => { events.close(); reject(new Error("Analysis connection closed before a result arrived.")); };
      });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Analysis could not complete."); setStage(-1);
    }
  }

  return <section id="analyze" className="workbench-section">
    <div className="section-heading"><div><p className="eyebrow">Your function, in motion</p><h2>Trace the dominant<br /><i>work.</i></h2></div><p>Static reasoning first. No code execution. No chat layer.</p></div>
    <div className="workbench">
      <form className="submission" onSubmit={submit}>
        <div className="form-head"><span>function input</span><span className="dot-label"><i /> safe static analysis</span></div>
        <label>Language<select value={language} onChange={(event) => setLanguage(event.target.value)}><option value="python">Python</option><option value="javascript">JavaScript (planned)</option><option value="typescript">TypeScript (planned)</option></select></label>
        <label>Function title<input value={title} maxLength={120} onChange={(event) => setTitle(event.target.value)} placeholder="Name this function" /></label>
        <label>Code<textarea value={code} onChange={(event) => setCode(event.target.value)} spellCheck="false" aria-describedby="code-help" /></label>
        <p id="code-help" className="form-help">Paste a top-level function. It is parsed, never executed.</p>
        <button className="analyze-button" type="submit">Analyze function <span>↗</span></button>
      </form>
      <section className="result" aria-live="polite">
        {!result && !error && <div className="result-empty"><span className="empty-glyph">⌁</span><h3>Give the trace<br />something to follow.</h3><p>Analysis will show the evidence behind the complexity—not a guess.</p></div>}
        {!result && stage >= 0 && <div className="progress"><p className="eyebrow">Analysis in progress</p>{stages.map((item, index) => <div key={item} className={index < stage ? "done" : index === stage ? "current" : ""}><span>{index < stage ? "✓" : index === stage ? "→" : "·"}</span>{item}</div>)}</div>}
        {error && <div className="result-error"><span>×</span><h3>Analysis stopped here.</h3><p>{error}</p><small>Choose Python and add a complete top-level function to continue.</small></div>}
        {result && <div className="result-data">
          <div className="result-kicker"><span>analysis complete</span><span>{result.function.language}</span></div>
          <div className="complexity-readout"><div><small>time</small><strong>{result.analysis.time_complexity}</strong></div><div><small>space</small><strong>{result.analysis.space_complexity}</strong></div><p>{Math.round(result.analysis.confidence * 100)}%<span> confidence</span></p></div>
          <p className="reasoning">{result.analysis.reasoning}</p>
          <div className="visual-panel"><div className="visual-top"><span>operation trace</span><span>{estimated.toLocaleString()} operations</span></div><Visualization type={result.visualization.type} size={size} /><p className="sr-only">{result.visualization.accessible_summary}</p><label className="size-control">Input size <input type="range" min="2" max="32" value={size} onChange={(event) => setSize(Number(event.target.value))} /><b>{size}</b></label></div>
          {result.analysis.assumptions.length > 0 && <div className="assumptions"><b>Assumptions</b>{result.analysis.assumptions.map((assumption) => <p key={assumption}>• {assumption}</p>)}</div>}
          {result.analysis.limitations.length > 0 && <div className="limitations"><b>What remains uncertain</b>{result.analysis.limitations.map((limitation) => <p key={limitation}>{limitation}</p>)}</div>}
        </div>}
      </section>
    </div>
  </section>;
}
