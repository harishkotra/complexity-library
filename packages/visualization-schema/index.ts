export type VisualizationType =
  | "constant"
  | "linear_scan"
  | "logarithmic_halving"
  | "n_log_n"
  | "quadratic_grid"
  | "recursion_tree";

export type VisualizationStep = {
  operation: string;
  label: string;
  index?: number;
  level?: number;
  row?: number;
  column?: number;
};

export type VisualizationSpec = {
  schema_version: 1;
  type: VisualizationType;
  input_size: number;
  operation_estimate: number;
  steps: VisualizationStep[];
  annotations: string[];
  accessible_summary: string;
  controls: { min: number; max: number; default: number; step: number };
};
