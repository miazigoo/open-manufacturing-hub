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
