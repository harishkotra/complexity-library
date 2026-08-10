from __future__ import annotations

from difflib import SequenceMatcher

from app.analysis import fingerprint_code, normalize_code
from app.curated import curated_functions
from app.domain import AnalyzeRequest, ComplexityAnalysis, SimilarFunction


def find_similar_functions(request: AnalyzeRequest, analysis: ComplexityAnalysis, limit: int = 3) -> list[SimilarFunction]:
    """Rank deterministic evidence; no vector or LLM score is permitted to stand alone."""
    normalized = normalize_code(request.language, request.code)
    fingerprint = fingerprint_code(request.language, request.code)
    candidates: list[SimilarFunction] = []
    for entry in curated_functions():
        entry_normalized = normalize_code(entry.language, entry.code)
        ast_similarity = SequenceMatcher(None, normalized, entry_normalized).ratio()
        fingerprint_match = fingerprint == fingerprint_code(entry.language, entry.code)
        signature_match = analysis.time_complexity == entry.time_complexity and analysis.space_complexity == entry.space_complexity
        pattern_match = analysis.pattern == entry.pattern
        language_match = request.language == entry.language
        score = 0.30 * max(ast_similarity, float(fingerprint_match)) + 0.25 * float(signature_match) + 0.15 * float(pattern_match) + 0.10 * float(language_match)
        reasons: list[str] = []
        if fingerprint_match:
            reasons.append("Same normalized syntax structure")
        elif ast_similarity >= 0.55:
            reasons.append("Similar syntax structure")
        if signature_match:
            reasons.append(f"Same time and space complexity ({analysis.time_complexity.value}, {analysis.space_complexity.value})")
        if pattern_match:
            reasons.append(f"Same {analysis.pattern.value.replace('_', ' ')} pattern")
        if language_match:
            reasons.append(f"Both are {request.language.value.title()}")
        if score >= 0.30:
            candidates.append(SimilarFunction(id=entry.id, slug=entry.slug, title=entry.title, time_complexity=entry.time_complexity, score=round(score, 3), reasons=reasons))
    return sorted(candidates, key=lambda candidate: candidate.score, reverse=True)[:limit]
