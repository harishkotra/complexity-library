import type { Metadata } from "next";
import { ComparisonWorkbench } from "../../components/comparison-workbench";

export const metadata: Metadata = { title: "Compare functions — Complexity Library", description: "Compare the growth of two published functions at the same input sizes." };

export default function ComparePage() { return <ComparisonWorkbench />; }
