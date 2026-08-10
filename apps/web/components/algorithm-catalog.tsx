"use client";

import { useEffect, useState } from "react";

type Algorithm = { slug: string; title: string; category: string; description: string; function_slug: string; time_complexity: string; space_complexity: string };
const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function AlgorithmCatalog() {
  const [algorithms, setAlgorithms] = useState<Algorithm[] | null>(null); const [error, setError] = useState("");
  useEffect(() => { fetch(`${api}/api/algorithms`).then(async (response) => { if (!response.ok) throw new Error("Curated algorithms could not load."); return response.json() as Promise<Algorithm[]>; }).then(setAlgorithms).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Curated algorithms could not load.")); }, []);
  return <main className="app-shell library-page"><nav className="nav"><a className="brand" href="/"><span className="brand-mark">↗</span> Complexity<br /><em>Library</em></a><div className="nav-links"><a href="/">Analyze</a><a href="/library">Library</a><a href="/algorithms">Algorithms</a></div><a className="nav-action" href="/#analyze">Analyze function <span>→</span></a></nav><header className="library-head"><p className="eyebrow">Curated algorithm library</p><h1>Patterns worth<br /><i>seeing run.</i></h1><p>Each entry points to a tested function record and its deterministic visualization. This catalog grows without turning the product into a blog.</p></header>{error && <section className="library-state error-state"><span>×</span><h2>Catalog unavailable.</h2><p>{error}</p></section>}{algorithms && <section className="algorithm-grid">{algorithms.map((algorithm) => <a href={`/functions/${algorithm.function_slug}`} key={algorithm.slug} className="algorithm-card"><p className="eyebrow">{algorithm.category}</p><h2>{algorithm.title}</h2><p>{algorithm.description}</p><div><span className="complexity-pill linear">{algorithm.time_complexity}</span><span>{algorithm.space_complexity} space</span></div><b>Study the trace ↗</b></a>)}</section>}</main>;
}
