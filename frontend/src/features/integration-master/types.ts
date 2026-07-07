export type InputMode = 'json' | 'xml' | 'raw_text';
export type OperationKeyType = 'field' | 'endpoint' | 'none';

export interface IntegrationScenario {
  key: string;
  title: string;
  description: string;
  caller: string;
  incoming: string;
  next_action: string;
  source_system: string;
  input_modes: InputMode[];
  default_input_mode: InputMode;
  default_slug: string;
  sample: unknown;
  recommended_operation_key: Record<string, unknown>;
  recommended_business_key: Record<string, unknown>;
}

export interface InputContractField {
  name: string;
  path: string;
  display_path?: string | null;
  type: string;
  required: boolean;
  example: unknown;
  description?: string | null;
}

export interface OperationKeySuggestion {
  type: OperationKeyType;
  field_path?: string | null;
  field_name?: string | null;
  value?: unknown;
  fallback_paths: string[];
  label: string;
  human_text: string;
  matcher_json: Record<string, unknown>;
}

export interface BusinessKeySuggestion {
  path: string;
  field_name: string;
  fallback_paths: string[];
  label: string;
  example?: unknown;
}

export interface InputParseRequest {
  input_mode: InputMode;
  sample: unknown;
  scenario_key?: string | null;
}

export interface InputParseResponse {
  input_mode: InputMode;
  normalized_sample: unknown;
  fields: InputContractField[];
  suggested_operation_keys: OperationKeySuggestion[];
  suggested_business_keys: BusinessKeySuggestion[];
  warnings: string[];
}

export interface InputOperationKey {
  type: OperationKeyType;
  field_path?: string | null;
  value?: unknown;
  fallback_paths: string[];
  matcher_preview: Record<string, unknown>;
}

export interface InputBusinessKey {
  path?: string | null;
  fallback_paths: string[];
}

export interface InputContract {
  name: string;
  slug: string;
  input_mode: InputMode;
  source_system: string;
  scenario_key?: string | null;
  sample: unknown;
  fields: InputContractField[];
  operation_key: InputOperationKey;
  business_key: InputBusinessKey;
  endpoint_url?: string | null;
}

export interface InputContractValidationResponse {
  valid: boolean;
  errors: string[];
  endpoint_url: string;
  matcher_preview: Record<string, unknown>;
}

export interface InputDraftRead {
  id: string;
  name: string;
  slug: string;
  scenario_key?: string | null;
  input_mode: InputMode;
  source_system: string;
  contract: InputContract;
  parse_result?: InputParseResponse | null;
  endpoint_url: string;
  created_at: string;
  updated_at: string;
}

export interface InputDraftSaveResponse {
  draft: InputDraftRead;
  next_steps: string[];
}
