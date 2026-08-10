"use client";

import { useEffect, useMemo, useState } from "react";

type Lesson = {
  key: string;
  label: string;
  title: string;
  body: string;
  prompt: string;
  formula: (n: number) => number;
};

const lessons: Lesson[] = [
  { key: "foundations", label: "01 · Big-O", title: "Measure the shape, not the stopwatch.", body: "Big-O compares how work changes as input grows. Constants matter in production, but the growth shape tells you which approach will age well.", prompt: "Move the reference input, then name the relationship: fixed, proportional, or faster than proportional?", formula: () => 1 },
  { key: "constant", label: "02 · O(1)", title: "Fixed work stays fixed.", body: "Reading one known position does the same amount of work whether the collection has 8 or 8,000 items.", prompt: "Find the operation that happens once, regardless of collection size.", formula: () => 3 },
  { key: "logarithmic", label: "03 · O(log n)", title: "Halving changes the scale.", body: "Binary search discards about half the remaining candidates with each comparison.", prompt: "Count how many times you can halve the input before one item remains.", formula: (n) => Math.ceil(Math.log2(n)) },
  { key: "linear", label: "04 · O(n)", title: "One pass grows with input.", body: "A linear scan may touch each item once, so twice the input means roughly twice the work.", prompt: "Identify which single operation repeats once for every item.", formula: (n) => n },
  { key: "nlogn", label: "05 · O(n log n)", title: "Split, then cover every item.", body: "Efficient comparison sorts repeatedly split the problem while doing linear work at each level.", prompt: "Notice that doubling n adds both more items and another division level.", formula: (n) => n * Math.ceil(Math.log2(n)) },
  { key: "quadratic", label: "06 · O(n²)", title: "Nested work multiplies.", body: "Comparing every item with every other item produces a grid of operations.", prompt: "Find the nested loop: one loop supplies rows and the other supplies columns.", formula: (n) => n * n },
  { key: "exponential", label: "07 · O(2ⁿ)", title: "Branches double the paths.", body: "A recursive choice that branches twice can create roughly twice as many paths for each extra input unit.", prompt: "Increase n by one. Does the estimate add a little, or multiply?", formula: (n) => 2 ** n },
  { key: "factorial", label: "08 · O(n!)", title: "Every ordering opens another path.", body: "Permutation-style recursion chooses one remaining item, then repeats for every remaining choice.", prompt: "Compare adjacent inputs: each new item can be placed in every existing ordering.", formula: (n) => Array.from({ length: n }, (_, index) => index + 1).reduce((total, value) => total * value, 1) },
  { key: "space", label: "09 · Space", title: "Memory has a growth shape too.", body: "An output array or recursion stack can grow with n even when the time complexity is already understood.", prompt: "Ask what the algorithm keeps alive at the same time—not only what it visits.", formula: (n) => n },
  { key: "calculation", label: "10 · Calculate", title: "Turn code into a growth claim.", body: "Name the input, count the repeating work, compose nested or sequential blocks, then state time and auxiliary space separately.", prompt: "Use the three reference sizes to explain why a linear pass plus a nested pass is dominated by O(n²).", formula: (n) => n + n * n },
];

export function LearnWorkbench() {
  const [lessonKey, setLessonKey] = useState("foundations");
  const [size, setSize] = useState(8);
  const [completed, setCompleted] = useState<string[]>([]);
  const lesson = lessons.find((item) => item.key === lessonKey) ?? lessons[0];

  useEffect(() => {
    const saved = window.localStorage.getItem("complexity-library:learn-progress");
    if (saved) setCompleted(JSON.parse(saved) as string[]);
  }, []);

  const values = useMemo(() => [Math.max(2, Math.floor(size / 2)), size, Math.min(24, size * 2)].map((n) => ({ n, operations: lesson.formula(n) })), [lesson, size]);
  const completeLesson = () => {
    const next = completed.includes(lesson.key) ? completed.filter((key) => key !== lesson.key) : [...completed, lesson.key];
    setCompleted(next);
    window.localStorage.setItem("complexity-library:learn-progress", JSON.stringify(next));
  };

  return <main className="app-shell learn-page"><nav className="nav"><a className="brand" href="/"><span className="brand-mark">↗</span> Complexity<br /><em>Library</em></a><div className="nav-links"><a href="/">Analyze</a><a href="/library">Library</a><a href="/algorithms">Algorithms</a><a href="/compare">Compare</a></div><a className="nav-action" href="/#analyze">Analyze function <span>→</span></a></nav><header className="library-head"><p className="eyebrow">Ten interactive Big-O lessons · {completed.length}/10 reviewed</p><h1>Make growth<br /><i>visible.</i></h1><p>Change the input. Read the operations. Use the same mental model when you inspect your own function.</p></header><section className="learn-layout"><aside aria-label="Lessons">{lessons.map((item) => <button key={item.key} className={item.key === lesson.key ? "selected" : ""} onClick={() => setLessonKey(item.key)}><span>{completed.includes(item.key) ? "✓ " : ""}{item.label}</span>{item.title}</button>)}</aside><article className="lesson-panel"><p className="eyebrow">{lesson.label} growth</p><h2>{lesson.title}</h2><p>{lesson.body}</p><div className="lesson-visual" aria-label={`${lesson.label} operation estimate`}><div className={`lesson-bars ${lesson.key}`}>{values.map((value) => <div key={value.n}><span style={{ height: `${Math.max(9, Math.min(100, value.operations / Math.max(...values.map((item) => item.operations)) * 100))}%` }} /><b>{value.operations.toLocaleString()}</b><small>n = {value.n}</small></div>)}</div><p className="sr-only">At input sizes {values.map((value) => `${value.n}, the estimate is ${value.operations} operations`).join("; ")}.</p></div><label className="size-control">Reference input <input type="range" min="4" max="24" value={size} onChange={(event) => setSize(Number(event.target.value))} /><b>n = {size}</b></label><div className="lesson-check"><b>Try it yourself</b><p>{lesson.prompt}</p><button type="button" onClick={completeLesson}>{completed.includes(lesson.key) ? "Mark for review" : "Mark lesson reviewed"}</button></div></article></section></main>;
}
