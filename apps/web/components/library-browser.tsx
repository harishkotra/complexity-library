"use client";

import { useEffect, useState } from "react";

type LibraryEntry = { id: string; slug: string; title: string; description?: string | null; language: string; time_complexity: string; space_complexity: string; confidence: number; pattern: string; created_at: string };

const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function LibraryBrowser() {
  const [entries, setEntries] = useState<LibraryEntry[] | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState(""); const [language, setLanguage] = useState(""); const [complexity, setComplexity] = useState(""); const [sort, setSort] = useState("newest");
  useEffect(() => { const parameters = new URLSearchParams(); if (query.trim()) parameters.set("q", query.trim()); if (language) parameters.set("language", language); if (complexity) parameters.set("time_complexity", complexity); parameters.set("sort", sort); setEntries(null); setError(""); fetch(`${api}/api/functions?${parameters}`).then(async (response) => { if (!response.ok) throw new Error("The library could not load."); return response.json() as Promise<LibraryEntry[]>; }).then(setEntries).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "The library could not load.")); }, [query, language, complexity, sort]);
  return <main className="app-shell library-page"><nav className="nav"><a className="brand" href="/"><span className="brand-mark">↗</span> Complexity<br /><em>Library</em></a><div className="nav-links"><a href="/">Analyze</a><a href="/library">Library</a><a href="/#learn">Learn</a></div><a className="nav-action" href="/#analyze">Analyze function <span>→</span></a></nav>
    <header className="library-head"><p className="eyebrow">Public knowledge library</p><h1>Functions with<br /><i>their work showing.</i></h1><p>Published submissions appear here after analysis and moderation. Filterable discovery is the next layer; this index never exposes drafts.</p></header>
    <section className="library-controls" aria-label="Filter the function library"><label>Search functions<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="binary search, recursion…" /></label><label>Language<select value={language} onChange={(event) => setLanguage(event.target.value)}><option value="">All languages</option><option value="python">Python</option><option value="javascript">JavaScript</option><option value="typescript">TypeScript</option></select></label><label>Time<select value={complexity} onChange={(event) => setComplexity(event.target.value)}><option value="">All growth</option><option>O(1)</option><option>O(log n)</option><option>O(n)</option><option>O(n log n)</option><option>O(n²)</option><option>O(2ⁿ)</option></select></label><label>Order<select value={sort} onChange={(event) => setSort(event.target.value)}><option value="newest">Newest</option><option value="complexity">Simplest first</option></select></label></section>
    {error && <section className="library-state error-state"><span>×</span><h2>Library unavailable.</h2><p>{error}</p></section>}
    {entries && entries.length === 0 && <section className="library-state"><span className="empty-glyph">⌁</span><h2>No functions match<br />this <i>view.</i></h2><p>Try a broader search or clear one of the filters.</p><button className="analyze-button library-cta" onClick={() => { setQuery(""); setLanguage(""); setComplexity(""); setSort("newest"); }}>Clear filters <span>↗</span></button></section>}
    {entries && entries.length > 0 && <section className="library-grid">{entries.map((entry) => <a key={entry.id} href={`/functions/${entry.slug}`} className="library-card"><div><span className="complexity-pill quadratic">{entry.time_complexity}</span><span className="language-label">{entry.language}</span></div><h2>{entry.title}</h2><p>{entry.description || `${entry.pattern.replaceAll("_", " ")} · ${entry.space_complexity} space`}</p><footer><span>{Math.round(entry.confidence * 100)}% confidence</span><span>Open ↗</span></footer></a>)}</section>}
  </main>;
}
