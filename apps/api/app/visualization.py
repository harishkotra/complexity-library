from __future__ import annotations

import math

from app.domain import ComplexityAnalysis, TimeComplexity, VisualizationSpec, VisualizationStep, VisualizationType


def build_visualization(analysis: ComplexityAnalysis, input_size: int = 16) -> VisualizationSpec:
    mapping = {
        TimeComplexity.CONSTANT: VisualizationType.CONSTANT,
        TimeComplexity.LOGARITHMIC: VisualizationType.LOGARITHMIC_HALVING,
        TimeComplexity.LINEAR: VisualizationType.LINEAR_SCAN,
        TimeComplexity.N_LOG_N: VisualizationType.N_LOG_N,
        TimeComplexity.QUADRATIC: VisualizationType.QUADRATIC_GRID,
        TimeComplexity.EXPONENTIAL: VisualizationType.RECURSION_TREE,
    }
    kind = mapping.get(analysis.time_complexity, VisualizationType.LINEAR_SCAN)
    if kind == VisualizationType.CONSTANT:
        steps = [VisualizationStep(operation="work", label="fixed operation", index=index) for index in range(3)]
        estimate, summary = 3, "The function performs three fixed operations regardless of input size."
    elif kind == VisualizationType.LOGARITHMIC_HALVING:
        values = []
        current = input_size
        while current > 1:
            values.append(current)
            current = max(1, current // 2)
        values.append(1)
        steps = [VisualizationStep(operation="halve", label=str(value), level=index) for index, value in enumerate(values)]
        estimate, summary = len(values) - 1, f"The search space halves from {input_size} until one item remains."
    elif kind == VisualizationType.N_LOG_N:
        levels = max(1, math.ceil(math.log2(input_size)))
        steps = [VisualizationStep(operation="level", label=f"level {level + 1}", level=level) for level in range(levels)]
        estimate, summary = input_size * levels, f"There are {levels} levels, each doing roughly {input_size} units of work."
    elif kind == VisualizationType.QUADRATIC_GRID:
        display_size = min(input_size, 12)
        steps = [VisualizationStep(operation="compare", label=f"{row},{column}", row=row, column=column) for row in range(display_size) for column in range(display_size)]
        estimate, summary = input_size * input_size, f"Each of {input_size} positions is compared against {input_size} positions."
    elif kind == VisualizationType.RECURSION_TREE:
        depth = min(5, max(2, math.ceil(math.log2(input_size))))
        steps = [VisualizationStep(operation="call", label=f"depth {level}", level=level) for level in range(depth)]
        estimate, summary = 2**depth - 1, "Each call branches into more calls, forming a growing recursion tree."
    else:
        steps = [VisualizationStep(operation="visit", label=f"item {index + 1}", index=index) for index in range(input_size)]
        estimate, summary = input_size, f"The function visits each of {input_size} input positions once."
    return VisualizationSpec(
        type=kind,
        input_size=input_size,
        operation_estimate=estimate,
        steps=steps,
        annotations=[analysis.reasoning],
        accessible_summary=summary,
    )
