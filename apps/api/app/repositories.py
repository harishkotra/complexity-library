from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol

from app.analysis import fingerprint_code, normalize_code
from app.curated import curated_function, curated_summaries
from app.domain import AnalyzeRequest, ComplexityAnalysis, FunctionDetail, FunctionLibraryItem, VisualizationSpec
from app.settings import Settings

ANALYZER_VERSION = "1"


@dataclass(frozen=True)
class PersistedFunction:
    id: str
    slug: str
    title: str
    language: str
    cache_hit: bool
    durable: bool


@dataclass(frozen=True)
class PersistedAnonymousSession:
    id: str
    durable: bool


class FunctionRepository(Protocol):
    def find_or_create(
        self,
        request: AnalyzeRequest,
        analysis: ComplexityAnalysis,
        visualization: VisualizationSpec,
        anonymous_session_id: str | None = None,
    ) -> PersistedFunction: ...
    def list_published(self, limit: int = 24, query: str | None = None, language: str | None = None, time_complexity: str | None = None, pattern: str | None = None, sort: Literal["newest", "complexity"] = "newest") -> list[FunctionLibraryItem]: ...
    def get_published(self, slug: str) -> FunctionDetail | None: ...


class AnonymousSessionRepository(Protocol):
    def ensure(self, token: str) -> PersistedAnonymousSession: ...


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized[:64] or "untitled-function"


def _source_hash(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


class InMemoryFunctionRepository:
    """Development-only repository. Its response explicitly says it is not durable."""

    def __init__(self) -> None:
        self._by_key: dict[str, PersistedFunction] = {}

    def find_or_create(self, request: AnalyzeRequest, analysis: ComplexityAnalysis, visualization: VisualizationSpec, anonymous_session_id: str | None = None) -> PersistedFunction:
        normalized = normalize_code(request.language, request.code)
        key = hashlib.sha256(f"{request.language}:{normalized}:{ANALYZER_VERSION}".encode("utf-8")).hexdigest()
        existing = self._by_key.get(key)
        if existing:
            return PersistedFunction(**{**existing.__dict__, "cache_hit": True})
        title = request.title.strip() if request.title else "Untitled function"
        stored = PersistedFunction(id=str(uuid.uuid4()), slug=f"{_slugify(title)}-{key[:7]}", title=title, language=request.language.value, cache_hit=False, durable=False)
        self._by_key[key] = stored
        return stored

    def list_published(self, limit: int = 24, query: str | None = None, language: str | None = None, time_complexity: str | None = None, pattern: str | None = None, sort: Literal["newest", "complexity"] = "newest") -> list[FunctionLibraryItem]:
        # Local submissions remain processing-only. Source-curated public records keep development useful.
        records = curated_summaries()
        if query:
            needle = query.casefold()
            records = [record for record in records if needle in " ".join([record.title, record.description or "", record.language.value, record.time_complexity.value, record.pattern.value.replace("_", " ")]).casefold()]
        if language:
            records = [record for record in records if record.language.value == language]
        if time_complexity:
            records = [record for record in records if record.time_complexity.value == time_complexity]
        if pattern:
            records = [record for record in records if record.pattern.value == pattern]
        if sort == "complexity":
            order = {"O(1)": 0, "O(log n)": 1, "O(n)": 2, "O(n log n)": 3, "O(n²)": 4, "O(n³)": 5, "O(2ⁿ)": 6, "O(n!)": 7, "unknown": 8}
            records.sort(key=lambda record: order[record.time_complexity.value])
        return records[:limit]

    def get_published(self, slug: str) -> FunctionDetail | None:
        return curated_function(slug)


class InMemoryAnonymousSessionRepository:
    def __init__(self) -> None:
        self._sessions: dict[str, PersistedAnonymousSession] = {}

    def ensure(self, token: str) -> PersistedAnonymousSession:
        token_hash = _source_hash(token)
        if token_hash not in self._sessions:
            self._sessions[token_hash] = PersistedAnonymousSession(id=str(uuid.uuid4()), durable=False)
        return self._sessions[token_hash]


class SupabaseFunctionRepository:
    def __init__(self, settings: Settings) -> None:
        from supabase import create_client

        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise ValueError("Supabase URL and server-side service role key are required for durable persistence.")
        self.client = create_client(settings.supabase_url, settings.supabase_service_role_key)

    def find_or_create(self, request: AnalyzeRequest, analysis: ComplexityAnalysis, visualization: VisualizationSpec, anonymous_session_id: str | None = None) -> PersistedFunction:
        normalized = normalize_code(request.language, request.code)
        code_hash = hashlib.sha256(f"{request.language}:{normalized}:{ANALYZER_VERSION}".encode("utf-8")).hexdigest()
        existing = self.client.table("functions").select("id,slug,title,language").eq("code_hash", code_hash).eq("analyzer_version", ANALYZER_VERSION).maybe_single().execute().data
        if existing:
            return PersistedFunction(id=existing["id"], slug=existing["slug"], title=existing["title"], language=existing["language"], cache_hit=True, durable=True)
        title = request.title.strip() if request.title else "Untitled function"
        fingerprint = fingerprint_code(request.language, request.code)
        slug = f"{_slugify(title)}-{code_hash[:7]}"
        payload = {
            "slug": slug,
            "title": title,
            "prompt": request.prompt,
            "code": request.code,
            "language": request.language.value,
            "normalized_code": normalized,
            "code_hash": code_hash,
            "ast_fingerprint": fingerprint,
            "time_complexity": analysis.time_complexity.value,
            "space_complexity": analysis.space_complexity.value,
            "confidence": analysis.confidence,
            "analysis": analysis.model_dump(mode="json"),
            "visualization_spec": visualization.model_dump(mode="json"),
            "pattern": analysis.pattern.value,
            "analyzer_version": ANALYZER_VERSION,
            "anonymous_session_id": anonymous_session_id,
            "status": "processing",
            "moderation_status": "pending",
        }
        created = self.client.table("functions").insert(payload).execute().data[0]
        self.client.table("function_analyses").insert({"function_id": created["id"], "schema_version": 1, "source": "deterministic", "analyzer_version": ANALYZER_VERSION, "analysis": payload["analysis"], "visualization_spec": payload["visualization_spec"]}).execute()
        return PersistedFunction(id=created["id"], slug=created["slug"], title=created["title"], language=created["language"], cache_hit=False, durable=True)

    @staticmethod
    def _summary(record: dict[str, object]) -> FunctionLibraryItem:
        return FunctionLibraryItem.model_validate({
            "id": record["id"], "slug": record["slug"], "title": record["title"], "description": record.get("description"),
            "language": record["language"], "time_complexity": record["time_complexity"], "space_complexity": record["space_complexity"],
            "confidence": record["confidence"], "pattern": record["pattern"], "created_at": record["created_at"],
        })

    def list_published(self, limit: int = 24, query: str | None = None, language: str | None = None, time_complexity: str | None = None, pattern: str | None = None, sort: Literal["newest", "complexity"] = "newest") -> list[FunctionLibraryItem]:
        statement = self.client.table("functions").select("id,slug,title,description,language,time_complexity,space_complexity,confidence,pattern,created_at").eq("status", "published").eq("moderation_status", "allowed")
        if language:
            statement = statement.eq("language", language)
        if time_complexity:
            statement = statement.eq("time_complexity", time_complexity)
        if pattern:
            statement = statement.eq("pattern", pattern)
        if query:
            statement = statement.ilike("title", f"%{query}%")
        records = statement.order("published_at" if sort == "newest" else "time_complexity", desc=sort == "newest").limit(limit).execute().data
        return [self._summary(record) for record in records]

    def get_published(self, slug: str) -> FunctionDetail | None:
        record = self.client.table("functions").select("id,slug,title,description,prompt,code,language,time_complexity,space_complexity,confidence,pattern,created_at,analysis,visualization_spec").eq("slug", slug).eq("status", "published").eq("moderation_status", "allowed").maybe_single().execute().data
        if not record:
            return None
        return FunctionDetail.model_validate({**self._summary(record).model_dump(), "prompt": record.get("prompt"), "code": record["code"], "analysis": record["analysis"], "visualization": record["visualization_spec"]})


class SupabaseAnonymousSessionRepository:
    def __init__(self, settings: Settings) -> None:
        from supabase import create_client

        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise ValueError("Supabase URL and server-side service role key are required for durable sessions.")
        self.client = create_client(settings.supabase_url, settings.supabase_service_role_key)

    def ensure(self, token: str) -> PersistedAnonymousSession:
        token_hash = _source_hash(token)
        existing = self.client.table("anonymous_sessions").select("id").eq("token_hash", token_hash).maybe_single().execute().data
        if existing:
            return PersistedAnonymousSession(id=existing["id"], durable=True)
        created = self.client.table("anonymous_sessions").insert({"token_hash": token_hash, "expires_at": (datetime.now(UTC) + timedelta(days=30)).isoformat()}).execute().data[0]
        return PersistedAnonymousSession(id=created["id"], durable=True)


def build_function_repository(settings: Settings) -> FunctionRepository:
    return SupabaseFunctionRepository(settings) if settings.supabase_url and settings.supabase_service_role_key else InMemoryFunctionRepository()


def build_anonymous_session_repository(settings: Settings) -> AnonymousSessionRepository:
    return SupabaseAnonymousSessionRepository(settings) if settings.supabase_url and settings.supabase_service_role_key else InMemoryAnonymousSessionRepository()
