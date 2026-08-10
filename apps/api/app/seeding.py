from __future__ import annotations

import hashlib
from typing import Any, Protocol

from app.analysis import normalize_code
from app.curated import curated_functions
from app.repositories import ANALYZER_VERSION


class TableClient(Protocol):
    def upsert(self, payload: list[dict[str, Any]], on_conflict: str): ...


class SupabaseClient(Protocol):
    def table(self, name: str) -> TableClient: ...


def curated_seed_rows() -> list[dict[str, Any]]:
    """Build deterministic published rows; callers decide when and where to write them."""
    rows: list[dict[str, Any]] = []
    for detail in curated_functions():
        normalized = normalize_code(detail.language, detail.code)
        code_hash = hashlib.sha256(f"{detail.language.value}:{normalized}:{ANALYZER_VERSION}".encode("utf-8")).hexdigest()
        rows.append({
            "slug": detail.slug,
            "title": detail.title,
            "description": detail.description,
            "prompt": detail.prompt,
            "code": detail.code,
            "language": detail.language.value,
            "normalized_code": normalized,
            "code_hash": code_hash,
            "time_complexity": detail.time_complexity.value,
            "space_complexity": detail.space_complexity.value,
            "confidence": detail.confidence,
            "analysis": detail.analysis.model_dump(mode="json"),
            "visualization_spec": detail.visualization.model_dump(mode="json"),
            "pattern": detail.pattern.value,
            "analyzer_version": ANALYZER_VERSION,
            "status": "published",
            "moderation_status": "allowed",
            "published_at": detail.created_at,
        })
    return rows


def seed_curated_functions(client: SupabaseClient) -> int:
    rows = curated_seed_rows()
    client.table("functions").upsert(rows, on_conflict="code_hash,analyzer_version").execute()
    return len(rows)
