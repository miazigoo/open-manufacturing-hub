import type { CompileDraftResponse, CompiledRunTestResponse, FinalActionBodySource, FinalActionBodyType, FinalActionMethod, FinalActionReturnType, InputBusinessKey, InputContract, InputContractField, InputMode, InputOperationKey, InputParseResponse, ODataStepConfig, PayloadStepConfig } from '../../integration-master/types';

export interface RequestODataSendEndpointWizardState {
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
  payload: PayloadStepConfig;
  target: RequestODataSendEndpointTargetConfig;
  responseToCaller: RequestODataSendEndpointResponseConfig;
}

export interface RequestODataSendEndpointTargetConfig {
  operation_id?: string | null;
  operation_code?: string | null;
  operation_name?: string | null;
  method: FinalActionMethod;
  url: string;
  headers: Record<string, unknown>;
  body_source: FinalActionBodySource;
  body_type: FinalActionBodyType;
  custom_body?: unknown;
  timeout_seconds: number;
}

export interface RequestODataSendEndpointResponseConfig {
  type: FinalActionReturnType;
  status_code: number;
  body?: unknown;
  headers?: Record<string, unknown>;
}

export interface RequestODataSendEndpointPatternRequest {
  name: string;
  slug: string;
  input_contract: InputContract;
  odata_step: ODataStepConfig;
  payload: PayloadStepConfig;
  target: RequestODataSendEndpointTargetConfig;
  response_to_caller: RequestODataSendEndpointResponseConfig;
}

export interface RequestODataSendEndpointPreviewResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  endpoint: Record<string, unknown>;
  incoming_request: unknown;
  odata_request: Record<string, unknown>;
  odata_result: Record<string, unknown> | null;
  target_payload: unknown;
  target_request: Record<string, unknown> | null;
  response_to_caller: unknown;
  human_steps: string[];
  advanced: Record<string, unknown>;
}

export interface RequestODataSendEndpointCreateResponse {
  draft_id: string;
  compile: CompileDraftResponse;
  preview: RequestODataSendEndpointPreviewResponse;
}

export interface RequestODataSendEndpointRunTestRequest {
  integration_flow_id: string;
  dry_run: boolean;
}

export type RequestODataSendEndpointRunTestResponse = CompiledRunTestResponse;
