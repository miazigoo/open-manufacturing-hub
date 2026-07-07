export type InputMode = 'json' | 'xml' | 'raw_text';
export type OperationKeyType = 'field' | 'endpoint' | 'none';
export type ODataFilterMode = 'builder' | 'raw';
export type ODataFilterOperator = 'eq' | 'ne' | 'contains' | 'gt' | 'lt' | 'ge' | 'le';
export type ODataValueType = 'string' | 'number' | 'boolean' | 'variable' | 'guid' | 'raw';
export type ODataObjectKeyType = 'guid' | 'string' | 'number' | 'raw';
export type ForeachODataMergeMode = 'flatten' | 'group_by_item' | 'first_per_item';
export type PayloadBodyType = 'json' | 'xml' | 'raw_text';
export type JsonPayloadMode = 'table' | 'raw_template';
export type JsonPayloadValueType = 'variable' | 'template_string' | 'constant_string' | 'constant_number' | 'constant_boolean' | 'constant_null' | 'object' | 'array';

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

export interface ODataFilterRule {
  field: string;
  operator: ODataFilterOperator;
  value_type: ODataValueType;
  value: unknown;
}

export interface ODataStepConfig {
  id?: string | null;
  type?: 'odata_query';
  connection_id?: string | null;
  connection_name?: string | null;
  resource: string;
  filter_mode: ODataFilterMode;
  filter_rule?: ODataFilterRule | null;
  filter?: string | null;
  select: string[];
  top?: number | null;
  orderby?: string | null;
  paginate: boolean;
  save_as: string;
  required: boolean;
  last_test_status?: string | null;
}

export interface ODataObjectStepConfig {
  id?: string | null;
  type: 'odata_object_query';
  connection_id?: string | null;
  connection_name?: string | null;
  object_variable: string;
  key_field: string;
  key_type: ODataObjectKeyType;
  base_resource: string;
  nested_resource: string;
  resource_template?: string | null;
  filter?: string | null;
  select: string[];
  top?: number | null;
  paginate: boolean;
  save_as: string;
  required: boolean;
  overwrite?: boolean;
  last_test_status?: string | null;
}

export interface ForeachODataSafetyLimits {
  max_items: number;
  max_requests: number;
  max_result_rows: number;
}

export interface ForeachODataStepConfig {
  id?: string | null;
  type: 'foreach_odata';
  items: string;
  item_as: string;
  connection_id?: string | null;
  connection_name?: string | null;
  resource: string;
  filter?: string | null;
  select: string[];
  top?: number | null;
  paginate: boolean;
  merge: ForeachODataMergeMode;
  save_as: string;
  required: boolean;
  limits: ForeachODataSafetyLimits;
  test_limit?: number | null;
  overwrite?: boolean;
  last_test_status?: string | null;
}

export interface JsonPayloadFieldConfig {
  target_path: string;
  value_source: unknown;
  value_type: JsonPayloadValueType;
}

export interface JsonPayloadDynamicEntryConfig {
  object_path: string;
  key_source: string;
  value_source: unknown;
  value_type: JsonPayloadValueType;
}

export interface PayloadStepConfig {
  id?: string | null;
  type: 'build_payload';
  body_type: PayloadBodyType;
  save_as: string;
  json_mode: JsonPayloadMode;
  template?: unknown;
  fields: JsonPayloadFieldConfig[];
  dynamic_entries: JsonPayloadDynamicEntryConfig[];
  overwrite?: boolean;
  last_preview_status?: string | null;
}

export type IntegrationMasterODataStep = ODataStepConfig | ODataObjectStepConfig | ForeachODataStepConfig | PayloadStepConfig;

export interface ODataStepRequest {
  input_contract: InputContract;
  sample_input?: unknown;
  odata_step: ODataStepConfig;
}

export interface ODataObjectStepRequest {
  input_contract: InputContract;
  previous_variables: Record<string, unknown>;
  odata_object_step: ODataObjectStepConfig;
}

export interface ForeachODataStepRequest {
  input_contract: InputContract;
  previous_variables: Record<string, unknown>;
  foreach_step: ForeachODataStepConfig;
}

export interface PayloadStepRequest {
  input_contract?: InputContract | null;
  previous_variables: Record<string, unknown>;
  payload_step: PayloadStepConfig;
}

export interface ODataStepValidationResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  template_filter?: string | null;
  rendered_filter?: string | null;
  template_url?: string | null;
  rendered_url?: string | null;
  variables_after_step: string[];
}

export interface ODataStepPreviewResponse extends ODataStepValidationResponse {
  rendered_resource: string;
  saved_as: string;
}

export interface ODataObjectStepValidationResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  template_resource?: string | null;
  rendered_resource?: string | null;
  template_filter?: string | null;
  rendered_filter?: string | null;
  template_url?: string | null;
  rendered_url?: string | null;
  variables_after_step: string[];
}

export interface ODataObjectStepPreviewResponse extends ODataObjectStepValidationResponse {
  saved_as: string;
  object_variable: string;
  key_preview?: unknown;
}

export interface ForeachODataStepValidationResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  source_count: number;
  first_item_preview?: Record<string, unknown> | null;
  template_filter?: string | null;
  rendered_filter?: string | null;
  template_url?: string | null;
  rendered_url?: string | null;
  variables_after_step: string[];
}

export interface ForeachODataStepPreviewResponse extends ForeachODataStepValidationResponse {
  saved_as: string;
  items: string;
  item_as: string;
  merge: ForeachODataMergeMode;
}

export interface PayloadStepValidationResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  body_type: PayloadBodyType;
  save_as: string;
  error_code?: string | null;
  variables_after_step: string[];
}

export interface PayloadStepPreviewResponse extends PayloadStepValidationResponse {
  rendered_preview?: unknown;
  size_bytes: number;
}

export interface ODataStepTestResponse {
  success: boolean;
  error_code?: string | null;
  message?: string | null;
  hint?: string | null;
  rendered_resource: string;
  rendered_filter?: string | null;
  items_count: number;
  result_preview?: Record<string, unknown> | null;
  saved_as: string;
  variables_after_step: string[];
  request: Record<string, unknown>;
}

export interface ODataObjectStepTestResponse {
  success: boolean;
  error_code?: string | null;
  message?: string | null;
  hint?: string | null;
  rendered_resource: string;
  rendered_filter?: string | null;
  items_count: number;
  result_preview: Array<Record<string, unknown>>;
  saved_as: string;
  variables_after_step: string[];
  request: Record<string, unknown>;
}

export interface ForeachODataStepTestResponse {
  success: boolean;
  error_code?: string | null;
  message?: string | null;
  hint?: string | null;
  source_count: number;
  items_processed: number;
  odata_requests: number;
  rows_found: number;
  merge: ForeachODataMergeMode;
  saved_as: string;
  result_preview?: unknown;
  variables_after_step: string[];
  requests: Array<Record<string, unknown>>;
}

export interface InputDraftRead {
  id: string;
  name: string;
  slug: string;
  scenario_key?: string | null;
  input_mode: InputMode;
  source_system: string;
  contract: InputContract;
  odata_steps: IntegrationMasterODataStep[];
  parse_result?: InputParseResponse | null;
  endpoint_url: string;
  created_at: string;
  updated_at: string;
}

export interface InputDraftSaveResponse {
  draft: InputDraftRead;
  next_steps: string[];
}

export interface ODataStepSaveResponse {
  draft: InputDraftRead;
  saved_step: ODataStepConfig;
  next_steps: string[];
}

export interface ODataObjectStepSaveResponse {
  draft: InputDraftRead;
  saved_step: ODataObjectStepConfig;
  next_steps: string[];
}

export interface ForeachODataStepSaveResponse {
  draft: InputDraftRead;
  saved_step: ForeachODataStepConfig;
  next_steps: string[];
}

export interface PayloadStepSaveResponse {
  draft: InputDraftRead;
  saved_step: PayloadStepConfig;
  next_steps: string[];
}
