import type { VisualizationSpec } from "./index";

export const linearScanFixture: VisualizationSpec = {
  schema_version: 1,
  type: "linear_scan",
  input_size: 8,
  operation_estimate: 8,
  steps: [{ operation: "visit", label: "item 1", index: 0 }],
  annotations: ["One visit per input item."],
  accessible_summary: "The algorithm visits each item once.",
  controls: { min: 2, max: 64, default: 8, step: 2 },
};
