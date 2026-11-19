export interface OneCMarkingCodePoolExportRequest {
  source_system?: string;
  source_document_id?: string | null;
  source_document_name?: string | null;
  order_number: string;
  file_name?: string | null;
  codes?: string[] | null;
  full_codes_base64?: string[] | null;
  gs_marker?: string;
  allow_overwrite?: boolean;
  actions_override?: MarkingCodePoolActionOverrides;
  metadata_json?: Record<string, unknown>;
}

export interface MarkingCodePoolActionOverrides {
  local_outbox?: boolean | null;
  laser_file?: boolean | null;
  external_forward?: boolean | null;
}

export interface MarkingCodePoolOverview {
  settings: MarkingCodePoolSettings;
  latest_export: MarkingCodePoolExport | null;
  recent_errors: MarkingCodePoolExport[];
  total_exports: number;
}

export interface MarkingCodePoolExport {
  id: string;
  source_system: string;
  source_document_id: string | null;
  source_document_name: string | null;
  order_number: string;
  file_name: string;
  file_path: string;
  total_codes: number;
  content_sha256: string;
  status: string;
  error_message: string | null;
  metadata_json: Record<string, unknown>;
  forwarded_at: string | null;
  created_at: string;
}

export interface MarkingCodePoolExportResponse {
  export: MarkingCodePoolExport;
  message: string;
  success: boolean;
  status: string;
  warnings: string[];
  actions: Record<string, ActionDetails>;
  segments?: Array<Record<string, unknown>>;
  external_forward: Record<string, unknown> | null;
  dnp_forward: Record<string, unknown> | null;
}

export interface ActionDetails {
  status?: string;
  path?: string;
  target?: string;
  file_name?: string;
  url?: string;
  reason?: string;
  error?: string;
  response?: unknown;
  [key: string]: unknown;
}

export interface MarkingCodePoolSettings {
  local_outbox: {
    enabled: boolean;
    required: boolean;
    export_dir: string;
    file_name_template: string;
    allow_overwrite_default: boolean;
    note: string;
  };
  laser: {
    enabled: boolean;
    smb_unc: string;
    username: string;
    password_set: boolean;
  };
  forward: {
    enabled: boolean;
    service_name: string;
    url: string;
    method: string;
    header_name: string;
    token_set: boolean;
    timeout_seconds: number;
  };
  response: {
    success_mode: string;
  };
  source: string;
}

export interface MarkingCodePoolSettingsPatch {
  local_outbox_enabled?: boolean;
  export_dir?: string;
  file_name_template?: string;
  allow_overwrite_default?: boolean;
  laser_enabled?: boolean;
  laser_smb_unc?: string;
  laser_smb_username?: string;
  laser_smb_password?: string;
  forward_enabled?: boolean;
  forward_service_name?: string;
  forward_url?: string;
  forward_method?: string;
  forward_header_name?: string;
  forward_token?: string;
  forward_timeout_seconds?: number;
  response_success_mode?: string;
}

export interface MarkingCodePoolPreviewResponse {
  success: boolean;
  file_name: string;
  total_codes: number;
  content_sha256: string;
  would_save_to: string;
  would_laser_copy: Record<string, unknown>;
  would_forward: Record<string, unknown>;
  warnings: string[];
  segments?: Array<Record<string, unknown>>;
}

export interface MarkingCodePoolSettingsTestResponse {
  success: boolean;
  status: string;
  message: string;
  details: Record<string, unknown>;
}

export interface MarkingCodePoolActionRetryResponse {
  success: boolean;
  status: string;
  message: string;
  error_code: string | null;
  action: ActionDetails;
}

export interface ChzAggregationSettings {
  onec_url: string;
  method: string;
  header_name: string;
  token_set: boolean;
  timeout_seconds: number;
  source: string;
}

export interface ChzAggregationSettingsPatch {
  onec_url?: string;
  onec_token?: string;
  onec_header_name?: string;
  onec_timeout_seconds?: number;
}

export interface ChzAggregationPreviewResponse {
  success: boolean;
  status: string;
  order_number_1c: string;
  order_number_external: string | null;
  total_codes: number;
  total_aggregates: number;
  content_sha256: string;
  duplicate_codes: number;
  warnings: string[];
  sample: Record<string, unknown>;
}

export interface ChzAggregationRegistration {
  id: string;
  source_system: string;
  source_document_id: string | null;
  source_file_name: string | null;
  order_number_1c: string;
  order_number_external: string | null;
  total_codes: number;
  total_aggregates: number;
  content_sha256: string;
  status: string;
  error_message: string | null;
  metadata_json: Record<string, unknown>;
  forwarded_at: string | null;
  created_at: string;
}

export interface ChzAggregationRegistrationResponse {
  success: boolean;
  status: string;
  message: string;
  registration: ChzAggregationRegistration;
  onec_response: Record<string, unknown> | null;
  warnings: string[];
}

export interface ChzDnpPullRequest {
  order_number_1c: string;
  date_from?: string | null;
  date_to?: string | null;
  only_new?: boolean;
}

export interface ChzDnpPullRow {
  full_code_base64: string;
  sscc: string | null;
}

export interface ChzDnpPullResponse {
  ok: boolean;
  order_number_1c: string;
  order_name_dnp: string | null;
  codes_count: number;
  boxes_count: number;
  tsv_text_base64: string;
  rows: ChzDnpPullRow[];
  event_id: string | null;
  timeline_url: string | null;
}

export interface RoutingRuleTarget {
  type: 'laser_file' | 'local_outbox' | 'http_forward';
  file_name_template?: string | null;
  name?: string | null;
  url?: string | null;
  method?: string;
  header_name?: string | null;
  token?: string | null;
  timeout_seconds?: number | null;
}

export interface RoutingRule {
  id: string;
  name: string;
  enabled: boolean;
  priority: number;
  match_json: Record<string, unknown>;
  targets_json: RoutingRuleTarget[];
  created_at: string;
}

export interface RoutingRulePayload {
  name: string;
  enabled?: boolean;
  priority?: number;
  match_json: Record<string, unknown>;
  targets_json: RoutingRuleTarget[];
}

export interface RoutingRuleTestCodeResult {
  code_preview: string;
  gtin: string;
  serial: string;
  segment: string;
  rule_id: string | null;
  rule_name: string | null;
  targets: RoutingRuleTarget[];
}

export interface RoutingRuleTestResponse {
  total_codes: number;
  matched_codes: number;
  default_codes: number;
  results: RoutingRuleTestCodeResult[];
}

export interface RoutingRuleTestRequest {
  codes?: string[];
  full_codes_base64?: string[];
  gs_marker?: string;
  order_number?: string;
  source_document_id?: string | null;
  source_system?: string;
}
