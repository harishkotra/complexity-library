import type { Metadata } from "next";
import { LibraryBrowser } from "../../components/library-browser";

export const metadata: Metadata = { title: "Function library — Complexity Library", description: "Browse published functions and their complexity visualizations." };

export default function LibraryPage() { return <LibraryBrowser />; }
