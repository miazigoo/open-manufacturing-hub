import type { CompileDraftResponse, CompiledRunTestResponse, FinalActionBodyType, FinalActionMethod, InputBusinessKey, InputContract, InputContractField, InputMode, InputOperationKey, InputParseResponse, ODataStepConfig, PayloadStepConfig } from '../../integration-master/types';

export type SourceWebApiWritebackCallerResponseType = 'custom_json' | 'site_response' | 'onec_writeback_response' | 'accepted_event';
export type SourceWebApiWritebackConditionOperator = 'eq' | 'ne';

export interface SourceWebApiWritebackEndpointConfig {
  operation_id?: string | null;
  operation_code?: string | null;
  operation_name?: string | null;
  method: FinalActionMethod;
  url: string;
  headers: Record<string, unknown>;
  body_source: string;
  body_type: FinalActionBodyType;
  custom_body?: unknown;
  timeout_seconds: number;
  save_response_as: string;
  mock_response_json?: unknown;
}

export interface SourceWebApiWritebackSuccessCondition {
  path: string;
  operator: SourceWebApiWritebackConditionOperator;
  value: unknown;
}

export interface SourceWebApiWritebackExtractionConfig {
  external_id_path: string;
  status_path: string;
  success_condition: SourceWebApiWritebackSuccessCondition;
  sample_response: Record<string, unknown>;
}

export interface SourceWebApiWritebackOneCServiceConfig {
  operation_id?: string | null;
  operation_code?: string | null;
  operation_name?: string | null;
  method: FinalActionMethod;
  connector_id?: string | null;
  connector_name?: string | null;
  base_url: string;
  path: string;
  url: string;
  headers: Record<string, unknown>;
  body_source: string;
  body_type: FinalActionBodyType;
  timeout_seconds: number;
  save_response_as: string;
  mock_response_json?: unknown;
}

export interface SourceWebApiWritebackCallerResponseConfig {
  type: SourceWebApiWritebackCallerResponseType;
  status_code: number;
  body?: unknown;
  headers: Record<string, unknown>;
}

export interface SourceWebApiWritebackOneCPatternRequest {
  name: string;
  slug: string;
  input_contract: InputContract;
  odata_step: ODataStepConfig;
  site_payload: PayloadStepConfig;
  site_endpoint: SourceWebApiWritebackEndpointConfig;
  site_response_extraction: SourceWebApiWritebackExtractionConfig;
  onec_writeback_payload: PayloadStepConfig;
  onec_http_service: SourceWebApiWritebackOneCServiceConfig;
  caller_response: SourceWebApiWritebackCallerResponseConfig;
}

export interface SourceWebApiWritebackOneCPreviewResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  endpoint: Record<string, unknown>;
  incoming_request: unknown;
  odata_request: Record<string, unknown>;
  odata_result: Record<string, unknown> | null;
  site_payload: unknown;
  site_request: Record<string, unknown> | null;
  site_response: unknown;
  extraction: Record<string, unknown>;
  onec_writeback_payload: unknown;
  onec_writeback_request: Record<string, unknown> | null;
  onec_writeback_response: unknown;
  response_to_caller: unknown;
  human_steps: string[];
  advanced: Record<string, unknown>;
}

export interface SourceWebApiWritebackOneCCreateResponse {
  draft_id?: string | null;
  compile: CompileDraftResponse;
  preview: SourceWebApiWritebackOneCPreviewResponse;
}

export interface SourceWebApiWritebackOneCRunTestRequest {
  integration_flow_id: string;
  dry_run: boolean;
}

export type SourceWebApiWritebackOneCRunTestResponse = CompiledRunTestResponse;

export interface SourceWebApiWritebackOneCWizardState {
  name: string;
  slug: string;
  sourceSystem: string;
  inputMode: InputMode;
  sampleText: string;
  fields: InputContractField[];
  parseResult: InputParseResponse | null;
  operationKey: InputOperationKey;
  businessKey: InputBusinessKey;
  odataStep: ODataStepConfig;
  sitePayload: PayloadStepConfig;
  siteEndpoint: SourceWebApiWritebackEndpointConfig;
  siteResponseExtraction: SourceWebApiWritebackExtractionConfig;
  onecWritebackPayload: PayloadStepConfig;
  onecHttpService: SourceWebApiWritebackOneCServiceConfig;
  callerResponse: SourceWebApiWritebackCallerResponseConfig;
}
