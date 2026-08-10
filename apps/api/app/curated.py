from __future__ import annotations

from app.analysis import analyze_python
from app.domain import FunctionDetail, FunctionLibraryItem
from app.visualization import build_visualization


_CURATED: tuple[dict[str, str], ...] = (
    {"slug": "python-first-item", "title": "First item", "description": "Read one position from a collection.", "prompt": "Return the first item in a list.", "code": "def first_item(items):\n    return items[0]\n"},
    {"slug": "python-linear-search", "title": "Linear search", "description": "Visit each item until the target appears.", "prompt": "Find the index of a target value in a list.", "code": "def linear_search(items, target):\n    for index, item in enumerate(items):\n        if item == target:\n            return index\n    return -1\n"},
    {"slug": "python-binary-search", "title": "Binary search", "description": "Shrink a sorted search space from both bounds.", "prompt": "Find a target in a sorted list.", "code": "def binary_search(items, target):\n    low, high = 0, len(items) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if items[mid] == target:\n            return mid\n        if items[mid] < target:\n            low = mid + 1\n        else:\n            high = mid - 1\n    return -1\n"},
    {"slug": "python-pair-comparison", "title": "Pair comparison", "description": "Compare each value against every later value.", "prompt": "Determine whether a list contains duplicates.", "code": "def contains_duplicate(items):\n    for left in range(len(items)):\n        for right in range(left + 1, len(items)):\n            if items[left] == items[right]:\n                return True\n    return False\n"},
    {"slug": "python-sort-reference", "title": "Sort reference", "description": "Use Python's comparison sort to order a collection.", "prompt": "Return a sorted copy of a list.", "code": "def ordered(items):\n    return sorted(items)\n"},
    {"slug": "python-fibonacci-recursion", "title": "Fibonacci recursion", "description": "Branch into two smaller calls for each non-base input.", "prompt": "Calculate the nth Fibonacci number recursively.", "code": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n - 1) + fibonacci(n - 2)\n"},
)


def _detail(record: dict[str, str]) -> FunctionDetail:
    analysis = analyze_python(record["code"])
    return FunctionDetail(
        id=f"curated-{record['slug']}", slug=record["slug"], title=record["title"], description=record["description"], prompt=record["prompt"], code=record["code"],
        language="python", time_complexity=analysis.time_complexity, space_complexity=analysis.space_complexity, confidence=analysis.confidence, pattern=analysis.pattern,
        created_at="2026-08-10T00:00:00Z", analysis=analysis, visualization=build_visualization(analysis),
    )


def curated_functions() -> list[FunctionDetail]:
    return [_detail(record) for record in _CURATED]


def curated_summaries() -> list[FunctionLibraryItem]:
    return [FunctionLibraryItem.model_validate(item.model_dump()) for item in curated_functions()]


def curated_function(slug: str) -> FunctionDetail | None:
    return next((item for item in curated_functions() if item.slug == slug), None)
