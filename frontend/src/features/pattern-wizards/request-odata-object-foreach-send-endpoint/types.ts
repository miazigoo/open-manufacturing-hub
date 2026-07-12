import type { CompileDraftResponse, CompiledRunTestResponse, FinalActionBodySource, FinalActionBodyType, FinalActionMethod, FinalActionReturnType, ForeachODataStepConfig, InputBusinessKey, InputContract, InputContractField, InputMode, InputOperationKey, InputParseResponse, ODataObjectStepConfig, ODataStepConfig, PayloadStepConfig } from '../../integration-master/types';

export interface DnpTargetConfig {
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

export interface DnpCallerResponseConfig {
  type: FinalActionReturnType;
  status_code: number;
  body?: unknown;
  headers?: Record<string, unknown>;
}

export interface DnpChzPatternRequest {
  name: string;
  slug: string;
  input_contract: InputContract;
  find_order: ODataStepConfig;
  read_products: ODataObjectStepConfig;
  find_codes: ForeachODataStepConfig;
  payload: PayloadStepConfig;
  target: DnpTargetConfig;
  response_to_caller: DnpCallerResponseConfig;
}

export interface DnpChzPreviewResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  endpoint: Record<string, unknown>;
  incoming_request: unknown;
  order_request: Record<string, unknown>;
  order_result: Record<string, unknown> | null;
  products_request: Record<string, unknown>;
  products_result: Record<string, unknown>[];
  codes_requests: Record<string, unknown>[];
  codes_result: unknown;
  codes_summary: Record<string, unknown>;
  target_payload: unknown;
  target_request: Record<string, unknown> | null;
  response_to_caller: unknown;
  human_steps: string[];
  advanced: Record<string, unknown>;
}

export interface DnpChzCreateResponse {
  draft_id: string;
  compile: CompileDraftResponse;
  preview: DnpChzPreviewResponse;
}

export interface DnpChzRunTestRequest {
  integration_flow_id: string;
  dry_run: boolean;
}

export type DnpChzRunTestResponse = CompiledRunTestResponse;

export interface DnpChzWizardState {
  name: string;
  slug: string;
  sourceSystem: string;
  inputMode: InputMode;
  sampleText: string;
  fields: InputContractField[];
  parseResult: InputParseResponse | null;
  operationKey: InputOperationKey;
  businessKey: InputBusinessKey;
  findOrder: ODataStepConfig;
  readProducts: ODataObjectStepConfig;
  findCodes: ForeachODataStepConfig;
  payload: PayloadStepConfig;
  target: DnpTargetConfig;
  responseToCaller: DnpCallerResponseConfig;
}
