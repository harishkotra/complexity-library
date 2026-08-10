import { AnalyzerWorkbench } from "../components/analyzer-workbench";

export default function Home() {
  return (
    <main className="app-shell">
      <nav className="nav" aria-label="Primary navigation">
        <a className="brand" href="#top"><span className="brand-mark">↗</span> Complexity<br /><em>Library</em></a>
        <div className="nav-links"><a href="#analyze">Analyze</a><a href="/library">Library</a><a href="/algorithms">Algorithms</a><a href="/compare">Compare</a><a href="#learn">Learn</a></div>
        <button className="nav-action">Browse examples <span>→</span></button>
      </nav>

      <section id="top" className="hero">
        <div className="hero-copy">
          <p className="eyebrow"><span className="pulse" /> Deterministic complexity analysis</p>
          <h1>Watch the work<br />your code <i>creates.</i></h1>
          <p className="lede">Submit a function. Trace its dominant operations. See why its time and space complexity grow the way they do.</p>
          <div className="hero-note"><span>01</span><p>Built for functions—not prompts. The visual explanation is the result.</p></div>
        </div>
        <div className="hero-signal" aria-label="A visual trace that grows from linear to quadratic work">
          <div className="signal-label"><span>work trace</span><b>O(n²)</b></div>
          <div className="trace-grid">{Array.from({ length: 49 }, (_, index) => <span key={index} className={index % 7 <= Math.floor(index / 7) ? "active" : ""} />)}</div>
          <div className="signal-axis"><span>input size →</span><span>operations ↑</span></div>
        </div>
      </section>

      <AnalyzerWorkbench />

      <section id="library" className="library-tease">
        <div><p className="eyebrow">Library field notes</p><h2>Learn from work<br />that already <i>scales.</i></h2></div>
        <div className="tease-list">
          <article><span className="complexity-pill linear">O(n)</span><div><b>Linear search</b><p>One pass. One growing trace.</p></div><span>↗</span></article>
          <article><span className="complexity-pill log">O(log n)</span><div><b>Binary search</b><p>Halve the space at every step.</p></div><span>↗</span></article>
          <article><span className="complexity-pill quadratic">O(n²)</span><div><b>Pair comparison</b><p>Every item meets every other.</p></div><span>↗</span></article>
        </div>
      </section>
      <footer id="learn"><span>Complexity Library</span><span>Understand growth. Keep the evidence.</span></footer>
    </main>
  );
}
