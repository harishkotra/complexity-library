from __future__ import annotations

from typing import Literal

from fastapi import BackgroundTasks, Cookie, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.analysis import analyze_code
from app.curated import curated_algorithms
from app.domain import AlgorithmItem, AnalysisJobResponse, AnalyzeRequest, AnalyzeResponse, FunctionDetail, FunctionLibraryItem, FunctionReference, SearchResult, SupportedLanguage
from app.jobs import job_store
from app.observability import RequestObservabilityMiddleware, log_event
from app.repositories import build_anonymous_session_repository, build_function_repository
from app.sessions import create_anonymous_session, hash_anonymous_session
from app.settings import get_settings
from app.visualization import build_visualization

app = FastAPI(title="Complexity Library API", version="0.1.0")
settings = get_settings()
function_repository = build_function_repository(settings)
anonymous_session_repository = build_anonymous_session_repository(settings)
app.add_middleware(RequestObservabilityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

STAGES = [
    "Parsed function",
    "Built syntax facts",
    "Detected loops and recursion",
    "Determined complexity",
    "Built visualization",
]


def ensure_anonymous_session(response: Response, anonymous_session: str | None) -> str:
    if anonymous_session:
        return anonymous_session
    session = create_anonymous_session()
    response.set_cookie("cl_session", session.token, httponly=True, samesite="lax", secure=settings.app_env == "production", max_age=60 * 60 * 24 * 30)
    return session.token


def perform_analysis(request: AnalyzeRequest, anonymous_session_id: str | None = None) -> AnalyzeResponse:
    try:
        analysis = analyze_code(request.language, request.code)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    visualization = build_visualization(analysis)
    stored = function_repository.find_or_create(request, analysis, visualization, anonymous_session_id)
    log_event("analysis.completed", language=request.language.value, complexity=analysis.time_complexity, confidence=analysis.confidence, cache_hit=stored.cache_hit, durable=stored.durable)
    return AnalyzeResponse(analysis=analysis, visualization=visualization, stages=STAGES, function=FunctionReference(**stored.__dict__))


def run_analysis_job(job_id: str, request: AnalyzeRequest, anonymous_session_id: str) -> None:
    try:
        for stage in STAGES[:3]:
            job_store.emit(job_id, "stage", {"label": stage})
        result = perform_analysis(request, anonymous_session_id)
        for stage in STAGES[3:]:
            job_store.emit(job_id, "stage", {"label": stage})
        job_store.complete(job_id, result.model_dump(mode="json"))
    except HTTPException as exc:
        job_store.fail(job_id, str(exc.detail))
    except Exception:
        log_event("analysis.job.failed", job_id=job_id)
        job_store.fail(job_id, "Analysis could not complete.")


@app.get("/health")
def health() -> dict[str, str | bool | int | float]:
    return {"status": "ok", "mode": "deterministic", **settings.safe_runtime_summary()}


@app.post("/api/functions/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest, response: Response, anonymous_session: str | None = Cookie(default=None, alias="cl_session")) -> AnalyzeResponse:
    session_token = ensure_anonymous_session(response, anonymous_session)
    return perform_analysis(request, anonymous_session_repository.ensure(session_token).id)


@app.post("/api/functions/analyses", response_model=AnalysisJobResponse, status_code=202)
def create_analysis_job(request: AnalyzeRequest, background_tasks: BackgroundTasks, response: Response, anonymous_session: str | None = Cookie(default=None, alias="cl_session")) -> AnalysisJobResponse:
    session_token = ensure_anonymous_session(response, anonymous_session)
    session = anonymous_session_repository.ensure(session_token)
    job = job_store.create(hash_anonymous_session(session_token))
    background_tasks.add_task(run_analysis_job, job.id, request, session.id)
    return AnalysisJobResponse(id=job.id, status="queued", events_url=f"/api/functions/analyses/{job.id}/events")


@app.get("/api/functions/analyses/{job_id}/events")
def analysis_events(job_id: str, anonymous_session: str | None = Cookie(default=None, alias="cl_session")) -> StreamingResponse:
    if not anonymous_session or not job_store.get_for_session(job_id, hash_anonymous_session(anonymous_session)):
        raise HTTPException(status_code=404, detail="Analysis job not found.")
    return StreamingResponse(job_store.event_stream(job_id, hash_anonymous_session(anonymous_session)), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/functions", response_model=list[FunctionLibraryItem])
def list_functions(limit: int = 24, q: str | None = None, language: SupportedLanguage | None = None, time_complexity: str | None = None, pattern: str | None = None, sort: Literal["newest", "complexity"] = "newest") -> list[FunctionLibraryItem]:
    return function_repository.list_published(limit=max(1, min(limit, 100)), query=q.strip() if q else None, language=language.value if language else None, time_complexity=time_complexity, pattern=pattern, sort=sort)


@app.get("/api/functions/{slug}", response_model=FunctionDetail)
def function_detail(slug: str) -> FunctionDetail:
    detail = function_repository.get_published(slug)
    if not detail:
        raise HTTPException(status_code=404, detail="Published function not found.")
    return detail


@app.get("/api/search", response_model=SearchResult)
def search(q: str, limit: int = 24) -> SearchResult:
    query = q.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Enter a search term.")
    return SearchResult(query=query, results=function_repository.list_published(limit=max(1, min(limit, 100)), query=query))


@app.get("/api/algorithms", response_model=list[AlgorithmItem])
def list_algorithms() -> list[AlgorithmItem]:
    return curated_algorithms()
