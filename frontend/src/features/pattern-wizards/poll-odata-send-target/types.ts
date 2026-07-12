import type { FinalActionBodySource, FinalActionBodyType, FinalActionMethod, ODataStepConfig, PayloadStepConfig } from '../../integration-master/types';

export type PollODataScheduleType = 'manual_only' | 'interval_minutes';
export type PollODataFirstRunStrategy = 'fixed_start_date' | 'last_n_hours' | 'no_cursor_filter';
export type PollODataCursorType = 'last_success_at' | 'field_max_value' | 'manual';
export type PollODataCursorUpdateWhen = 'target_success' | 'odata_success' | 'manual';
export type PollODataEmptyResultBehavior = 'do_nothing_success' | 'send_empty_payload' | 'mark_warning';

export interface PollODataJobBasicsConfig {
  name: string;
  slug: string;
  enabled_after_create: boolean;
  schedule_type: PollODataScheduleType;
  interval_minutes: number;
}

export interface PollODataFirstRunStrategyConfig {
  strategy: PollODataFirstRunStrategy;
  fixed_start_at: string;
  hours: number;
}

export interface PollODataCursorConfig {
  cursor_type: PollODataCursorType;
  source_field: string;
  update_when: PollODataCursorUpdateWhen;
}

export interface PollODataTargetConfig {
  operation_id?: string | null;
  operation_code?: string | null;
  operation_name?: string | null;
  method: FinalActionMethod;
  url: string;
  headers: Record<string, unknown>;
  body_source: FinalActionBodySource | string;
  body_type: FinalActionBodyType;
  timeout_seconds: number;
  empty_result_behavior: PollODataEmptyResultBehavior;
}

export interface PollODataSendTargetPatternRequest {
  job: PollODataJobBasicsConfig;
  odata_step: ODataStepConfig;
  first_run: PollODataFirstRunStrategyConfig;
  cursor: PollODataCursorConfig;
  payload: PayloadStepConfig;
  target: PollODataTargetConfig;
}

export interface PollODataSendTargetPreviewResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  schedule: Record<string, unknown>;
  odata_request: Record<string, unknown>;
  first_run_filter: string;
  odata_result: Array<Record<string, unknown>>;
  target_payload: unknown;
  target_request: Record<string, unknown> | null;
  cursor: Record<string, unknown>;
  run_history_hint: Record<string, unknown>;
  human_steps: string[];
  advanced: Record<string, unknown>;
}

export interface PollODataSendTargetCreateResponse {
  polling_job_id: string;
  integration_flow_id: string | null;
  preview: PollODataSendTargetPreviewResponse;
  run_now_url: string;
  runs_url: string;
  enabled: boolean;
  next_steps: string[];
}

export interface PollODataSendTargetRunTestRequest {
  pattern?: PollODataSendTargetPatternRequest | null;
  polling_job_id?: string | null;
  dry_run: boolean;
  update_cursor: boolean;
}

export interface PollODataSendTargetRunTestResponse {
  success: boolean;
  run: Record<string, unknown>;
  preview: PollODataSendTargetPreviewResponse | null;
}
