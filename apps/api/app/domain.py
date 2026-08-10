from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class SupportedLanguage(StrEnum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"


class TimeComplexity(StrEnum):
    CONSTANT = "O(1)"
    LOGARITHMIC = "O(log n)"
    LINEAR = "O(n)"
    N_LOG_N = "O(n log n)"
    QUADRATIC = "O(n²)"
    CUBIC = "O(n³)"
    EXPONENTIAL = "O(2ⁿ)"
    FACTORIAL = "O(n!)"
    UNKNOWN = "unknown"


class SpaceComplexity(StrEnum):
    CONSTANT = "O(1)"
    LOGARITHMIC = "O(log n)"
    LINEAR = "O(n)"
    QUADRATIC = "O(n²)"
    UNKNOWN = "unknown"


class AlgorithmPattern(StrEnum):
    CONSTANT = "constant"
    LINEAR_SCAN = "linear_scan"
    LOGARITHMIC_HALVING = "logarithmic_halving"
    NESTED_LOOP = "nested_loop"
    DIVIDE_AND_CONQUER = "divide_and_conquer"
    RECURSION = "recursion"
    TWO_POINTER = "two_pointer"
    SLIDING_WINDOW = "sliding_window"
    BINARY_SEARCH = "binary_search"
    UNKNOWN = "unknown"


class VisualizationType(StrEnum):
    CONSTANT = "constant"
    LINEAR_SCAN = "linear_scan"
    LOGARITHMIC_HALVING = "logarithmic_halving"
    N_LOG_N = "n_log_n"
    QUADRATIC_GRID = "quadratic_grid"
    RECURSION_TREE = "recursion_tree"


class ComplexitySignature(BaseModel):
    recursion: bool = False
    loop_depth: int = Field(ge=0, le=10)
    input_types: list[str] = Field(default_factory=list)
    operations: list[str] = Field(default_factory=list)
    language: SupportedLanguage


class ComplexityAnalysis(BaseModel):
    schema_version: Literal[1] = 1
    time_complexity: TimeComplexity
    space_complexity: SpaceComplexity
    confidence: float = Field(ge=0, le=1)
    pattern: AlgorithmPattern
    source: Literal["deterministic"] = "deterministic"
    reasoning: str
    dominant_operations: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    signature: ComplexitySignature


class VisualizationStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: str
    label: str
    index: int | None = None
    level: int | None = None
    row: int | None = None
    column: int | None = None


class VisualizationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    type: VisualizationType
    input_size: int = Field(ge=1, le=128)
    operation_estimate: int = Field(ge=0, le=20_000)
    steps: list[VisualizationStep] = Field(default_factory=list, max_length=256)
    annotations: list[str] = Field(default_factory=list, max_length=12)
    accessible_summary: str
    controls: dict[str, int] = Field(default_factory=lambda: {"min": 2, "max": 64, "default": 16, "step": 2})


class AnalyzeRequest(BaseModel):
    language: SupportedLanguage
    code: str = Field(min_length=1, max_length=20_000)
    title: str | None = Field(default=None, max_length=120)
    prompt: str | None = Field(default=None, max_length=1_500)

    @field_validator("code")
    @classmethod
    def code_has_substance(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Paste a function before running analysis.")
        return value


class FunctionReference(BaseModel):
    id: str
    slug: str
    title: str
    language: str
    cache_hit: bool
    durable: bool


class SubmissionStatus(BaseModel):
    id: str
    slug: str
    status: Literal["processing", "published", "rejected", "removed", "failed"]
    moderation_status: Literal["pending", "allowed", "review", "blocked"]
    durable: bool


class AnalyzeResponse(BaseModel):
    analysis: ComplexityAnalysis
    visualization: VisualizationSpec
    stages: list[str]
    function: FunctionReference
    similar: list["SimilarFunction"] = Field(default_factory=list)


class AnalysisJobResponse(BaseModel):
    id: str
    status: Literal["queued"]
    events_url: str


class FunctionLibraryItem(BaseModel):
    id: str
    slug: str
    title: str
    description: str | None = None
    language: SupportedLanguage
    time_complexity: TimeComplexity
    space_complexity: SpaceComplexity
    confidence: float = Field(ge=0, le=1)
    pattern: AlgorithmPattern
    created_at: str


class FunctionDetail(FunctionLibraryItem):
    prompt: str | None = None
    code: str
    analysis: ComplexityAnalysis
    visualization: VisualizationSpec


class SimilarFunction(BaseModel):
    id: str
    slug: str
    title: str
    time_complexity: TimeComplexity
    score: float = Field(ge=0, le=1)
    reasons: list[str]


class SearchResult(BaseModel):
    query: str
    results: list[FunctionLibraryItem]


class AlgorithmItem(BaseModel):
    slug: str
    title: str
    category: str
    description: str
    function_slug: str
    time_complexity: TimeComplexity
    space_complexity: SpaceComplexity
