import type { Metadata } from "next";
import { LearnWorkbench } from "../../components/learn-workbench";

export const metadata: Metadata = { title: "Learn Big-O visually — Complexity Library", description: "Interactive, deterministic lessons on how algorithmic work grows." };

export default function LearnPage() { return <LearnWorkbench />; }
