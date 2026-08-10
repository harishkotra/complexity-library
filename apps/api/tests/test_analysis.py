import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from app.analysis import analyze_code, analyze_python, build_python_ir, fingerprint_python, normalize_python
from app.domain import AlgorithmPattern, SpaceComplexity, TimeComplexity
from app.visualization import build_visualization
from app.main import app


@pytest.mark.parametrize(
    ("code", "time", "pattern"),
    [
        ("def first(items):\n    return items[0]\n", TimeComplexity.CONSTANT, AlgorithmPattern.CONSTANT),
        ("def scan(items):\n    for item in items:\n        print(item)\n", TimeComplexity.LINEAR, AlgorithmPattern.LINEAR_SCAN),
        ("def pairs(items):\n    for left in items:\n        for right in items:\n            print(left, right)\n", TimeComplexity.QUADRATIC, AlgorithmPattern.NESTED_LOOP),
        ("def halve(n):\n    while n > 1:\n        n //= 2\n", TimeComplexity.LOGARITHMIC, AlgorithmPattern.LOGARITHMIC_HALVING),
        ("def ordered(items):\n    return sorted(items)\n", TimeComplexity.N_LOG_N, AlgorithmPattern.DIVIDE_AND_CONQUER),
        ("def cube(items):\n    for a in items:\n        for b in items:\n            for c in items:\n                print(a, b, c)\n", TimeComplexity.CUBIC, AlgorithmPattern.NESTED_LOOP),
        ("def binary(items, target):\n    low, high = 0, len(items) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if items[mid] < target:\n            low = mid + 1\n        else:\n            high = mid - 1\n    return -1\n", TimeComplexity.LOGARITHMIC, AlgorithmPattern.BINARY_SEARCH),
    ],
)
def test_supported_patterns(code, time, pattern):
    analysis = analyze_python(code)
    assert analysis.time_complexity == time
    assert analysis.pattern == pattern
    assert analysis.confidence >= 0.9


def test_recursive_allocation_reports_space():
    analysis = analyze_python("def walk(items):\n    if not items:\n        return []\n    return [items[0]] + walk(items[1:])\n")
    assert analysis.time_complexity == TimeComplexity.LINEAR
    assert analysis.space_complexity == SpaceComplexity.LINEAR
    assert analysis.signature.recursion is True


def test_invalid_code_gets_actionable_error():
    with pytest.raises(ValueError, match="could not parse"):
        analyze_python("def broken(:\n")


def test_normalization_and_fingerprint_ignore_local_identifier_names():
    first = "def scan(items):\n    for item in items:\n        print(item)\n"
    second = "def visit(values):\n    for value in values:\n        print(value)\n"
    assert normalize_python(first) == normalize_python(second)
    assert fingerprint_python(first) == fingerprint_python(second)


def test_sequential_loops_remain_linear_not_quadratic():
    analysis = analyze_python("def twice(items):\n    for item in items:\n        print(item)\n    for item in items:\n        print(item)\n")
    assert analysis.time_complexity == TimeComplexity.LINEAR


def test_linear_outer_loop_with_halving_inner_loop_is_n_log_n():
    analysis = analyze_python("def levels(items, n):\n    for item in items:\n        size = n\n        while size > 1:\n            size //= 2\n")
    assert analysis.time_complexity == TimeComplexity.N_LOG_N


def test_two_pointer_and_sliding_window_patterns_remain_linear():
    two_pointer = analyze_python("def pair(items):\n    left, right = 0, len(items) - 1\n    while left < right:\n        left += 1\n        right -= 1\n")
    sliding_window = analyze_python("def window(items):\n    left, right = 0, 0\n    while right < len(items):\n        right += 1\n        if right - left > 3:\n            left += 1\n")
    assert two_pointer.pattern == AlgorithmPattern.TWO_POINTER
    assert sliding_window.pattern == AlgorithmPattern.SLIDING_WINDOW
    assert two_pointer.time_complexity == sliding_window.time_complexity == TimeComplexity.LINEAR


def test_decrementing_recursion_uses_linear_stack_space():
    analysis = analyze_python("def count(n):\n    if n <= 0:\n        return 0\n    return count(n - 1)\n")
    assert analysis.time_complexity == TimeComplexity.LINEAR
    assert analysis.space_complexity == SpaceComplexity.LINEAR


def test_ir_records_control_flow_with_source_locations():
    ir = build_python_ir("def scan(items):\n    for item in items:\n        if item < 0:\n            continue\n        if item == 3:\n            break\n    return None\n")
    assert ir.function_name == "scan"
    assert ir.facts.branches == 2
    assert ir.facts.breaks == 1
    assert ir.facts.continues == 1
    assert [(fact.kind, fact.line) for fact in ir.facts.source_facts] == [("for_loop", 2), ("branch", 3), ("continue", 4), ("branch", 5), ("break", 6), ("return", 7)]


@pytest.mark.parametrize(
    ("language", "code", "time"),
    [
        ("javascript", "function scan(items) { for (const item of items) { console.log(item); } }", TimeComplexity.LINEAR),
        ("javascript", "function find(items, target) { let low = 0, high = items.length - 1; while (low <= high) { const mid = Math.floor((low + high) / 2); if (items[mid] < target) low = mid + 1; else high = mid - 1; } return -1; }", TimeComplexity.LOGARITHMIC),
        ("typescript", "function pairs(items: number[]): boolean { for (const left of items) { for (const right of items) { if (left === right) return true; } } return false; }", TimeComplexity.QUADRATIC),
    ],
)
def test_javascript_and_typescript_are_parsed_with_real_language_adapters(language, code, time):
    analysis = analyze_code(language, code)
    assert analysis.time_complexity == time
    assert analysis.signature.language.value == language


def test_javascript_submission_uses_the_same_typed_api_contract():
    response = TestClient(app).post("/api/functions/analyze", json={"language": "javascript", "code": "function first(items) { return items[0]; }"})
    assert response.status_code == 200
    assert response.json()["analysis"]["time_complexity"] == "O(1)"


def test_analysis_endpoint_returns_a_valid_visualization_contract():
    response = TestClient(app).post(
        "/api/functions/analyze",
        json={"language": "python", "title": "scan", "code": "def scan(items):\n    for item in items:\n        print(item)\n"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis"]["time_complexity"] == "O(n)"
    assert payload["visualization"]["type"] == "linear_scan"
    assert payload["visualization"]["accessible_summary"]
    assert payload["function"]["durable"] is False
    assert "cl_session=" in response.headers["set-cookie"]


def test_exact_normalized_submission_uses_memory_cache_in_local_development():
    client = TestClient(app)
    first = client.post("/api/functions/analyze", json={"language": "python", "code": "def scan(items):\n    for item in items:\n        print(item)\n"})
    second = client.post("/api/functions/analyze", json={"language": "python", "code": "def visit(values):\n    for value in values:\n        print(value)\n"})
    assert first.json()["function"]["slug"] == second.json()["function"]["slug"]
    assert second.json()["function"]["cache_hit"] is True


def test_health_and_analysis_responses_return_request_correlation_id():
    client = TestClient(app)
    health = client.get("/health", headers={"X-Request-ID": "test-correlation"})
    analysis = client.post("/api/functions/analyze", json={"language": "python", "code": "def item(items):\n    return items[0]\n"})
    assert health.headers["X-Request-ID"] == "test-correlation"
    assert health.json()["llm_enabled"] is False
    assert analysis.headers["X-Request-ID"]


def test_job_events_are_owner_scoped_and_include_real_stage_messages():
    client = TestClient(app)
    created = client.post("/api/functions/analyses", json={"language": "python", "code": "def scan(items):\n    for item in items:\n        print(item)\n"})
    assert created.status_code == 202
    job_id = created.json()["id"]
    events = client.get(f"/api/functions/analyses/{job_id}/events")
    assert events.status_code == 200
    assert "Parsed function" in events.text
    assert "event: completed" in events.text
    stranger = TestClient(app)
    assert stranger.get(f"/api/functions/analyses/{job_id}/events").status_code == 404


def test_local_library_contains_curated_public_entries_but_not_user_drafts():
    client = TestClient(app)
    entries = client.get("/api/functions").json()
    assert {entry["slug"] for entry in entries} >= {"python-linear-search", "python-binary-search"}
    assert client.get("/api/functions/python-linear-search").json()["time_complexity"] == "O(n)"
    assert client.get("/api/functions/not-a-public-entry").status_code == 404


def test_library_filters_and_search_are_real_query_operations():
    client = TestClient(app)
    assert [item["slug"] for item in client.get("/api/functions", params={"time_complexity": "O(log n)"}).json()] == ["python-binary-search"]
    result = client.get("/api/search", params={"q": "fibonacci"}).json()
    assert result["query"] == "fibonacci"
    assert [item["slug"] for item in result["results"]] == ["python-fibonacci-recursion"]


def test_curated_algorithms_link_to_public_function_evidence():
    algorithms = TestClient(app).get("/api/algorithms").json()
    assert {item["slug"] for item in algorithms} >= {"linear-search", "binary-search", "recursive-fibonacci"}
    assert next(item for item in algorithms if item["slug"] == "binary-search")["time_complexity"] == "O(log n)"


def test_visualization_contract_rejects_unknown_fields():
    analysis = analyze_python("def first(items):\n    return items[0]\n")
    spec = build_visualization(analysis)
    with pytest.raises(ValidationError):
        spec.__class__.model_validate({**spec.model_dump(), "agent_generated_code": "alert('unsafe')"})
