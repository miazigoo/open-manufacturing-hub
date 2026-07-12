import type { CompileDraftResponse, CompiledRunTestResponse, FinalActionBodyType, FinalActionMethod, InputBusinessKey, InputContract, InputContractField, InputMode, InputOperationKey, InputParseResponse, ODataStepConfig, PayloadStepConfig } from '../../integration-master/types';

export type WmsCallerResponseType = 'normalized' | 'raw_onec_response' | 'accepted_event';

export interface WmsFactToOneCODataLookupConfig {
  enabled: boolean;
  config: ODataStepConfig;
  order_ref_key_path: string;
}

export interface WmsFactToOneCServiceConfig {
  operation_id?: string | null;
  operation_code?: string | null;
  operation_name?: string | null;
  connector_id?: string | null;
  connector_name?: string | null;
  operation: string;
  method: FinalActionMethod;
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

export interface WmsFactToOneCCallerResponseConfig {
  type: WmsCallerResponseType;
  status_code: number;
  body?: unknown;
  headers: Record<string, unknown>;
}

export interface WmsFactToOneCPatternRequest {
  name: string;
  slug: string;
  input_contract: InputContract;
  odata_lookup: WmsFactToOneCODataLookupConfig;
  onec_payload: PayloadStepConfig;
  onec_http_service: WmsFactToOneCServiceConfig;
  caller_response: WmsFactToOneCCallerResponseConfig;
}

export interface WmsFactToOneCPreviewResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  endpoint: Record<string, unknown>;
  incoming_request: unknown;
  odata_request: Record<string, unknown>;
  odata_result: Record<string, unknown> | null;
  onec_payload: unknown;
  onec_request: Record<string, unknown> | null;
  onec_response: unknown;
  response_to_caller: unknown;
  human_steps: string[];
  advanced: Record<string, unknown>;
}

export interface WmsFactToOneCCreateResponse {
  draft_id?: string | null;
  compile: CompileDraftResponse;
  preview: WmsFactToOneCPreviewResponse;
}

export interface WmsFactToOneCRunTestRequest {
  integration_flow_id: string;
  dry_run: boolean;
}

export type WmsFactToOneCRunTestResponse = CompiledRunTestResponse;

export interface WmsFactToOneCWizardState {
  name: string;
  slug: string;
  sourceSystem: string;
  inputMode: InputMode;
  sampleText: string;
  fields: InputContractField[];
  parseResult: InputParseResponse | null;
  operationKey: InputOperationKey;
  businessKey: InputBusinessKey;
  odataLookup: WmsFactToOneCODataLookupConfig;
  onecPayload: PayloadStepConfig;
  onecHttpService: WmsFactToOneCServiceConfig;
  callerResponse: WmsFactToOneCCallerResponseConfig;
}
