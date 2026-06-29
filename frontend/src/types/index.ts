export interface Project {
  id: string;
  name: string;
  path?: string;
  description?: string;
  experiment_count: number;
  created_at: string;
  updated_at: string;
}

export interface Experiment {
  id: string;
  project_id: string;
  name?: string;
  git_commit?: string;
  branch?: string;
  repository_name?: string;
  tool: string;
  tool_version?: string;
  device?: string;
  seed?: number;
  status: string;
  compile_options?: Record<string, unknown>;
  machine_info?: Record<string, unknown>;
  changed_files?: string[];
  created_at: string;
  completed_at?: string;
}

export interface ExperimentList {
  items: Experiment[];
  total: number;
  limit: number;
  offset: number;
}

export interface Report {
  id: string;
  experiment_id: string;
  report_type: string;
  wns?: number;
  tns?: number;
  failing_paths?: number;
  critical_path?: string;
  lut?: number;
  lut_available?: number;
  ff?: number;
  ff_available?: number;
  bram?: number;
  bram_available?: number;
  dsp?: number;
  dsp_available?: number;
  io_used?: number;
  io_available?: number;
  clock_utilization?: number;
  synthesis_duration?: number;
  implementation_duration?: number;
  bitstream_duration?: number;
  total_runtime?: number;
  raw_content?: string;
  source_file?: string;
  parsed_at: string;
}

export interface Prediction {
  expected_wns?: number;
  expected_compile_duration?: number;
  timing_success_probability?: number;
  model_versions?: Record<string, string>;
  error?: string;
}

export interface Recommendation {
  id: string;
  experiment_id: string;
  rule_name: string;
  category: string;
  priority?: string;
  message: string;
  confidence?: number;
  created_at: string;
}

export interface CompareResult {
  experiment_ids: string[];
  deltas: Record<string, MetricDelta>;
  option_diffs: Record<string, OptionDiff>;
}

export interface MetricDelta {
  a?: number;
  b?: number;
  delta?: number;
}

export interface OptionDiff {
  a?: unknown;
  b?: unknown;
}
