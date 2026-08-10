import type { Metadata } from "next";
import { AlgorithmCatalog } from "../../components/algorithm-catalog";

export const metadata: Metadata = { title: "Algorithms — Complexity Library", description: "Study curated algorithm patterns with deterministic complexity evidence." };

export default function AlgorithmsPage() { return <AlgorithmCatalog />; }
