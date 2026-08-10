import type { Metadata } from "next";
import { FunctionDetailView } from "../../../components/function-detail";

export const metadata: Metadata = { title: "Function analysis — Complexity Library", description: "A public complexity analysis with its evidence and visualization." };

export default function FunctionPage({ params }: { params: Promise<{ slug: string }> }) { return <FunctionDetailView params={params} />; }
