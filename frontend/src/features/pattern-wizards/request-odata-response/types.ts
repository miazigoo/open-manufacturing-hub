import type { CompileDraftResponse, CompiledRunTestResponse, InputBusinessKey, InputContract, InputContractField, InputMode, InputOperationKey, InputParseResponse, ODataStepConfig, PayloadBodyType } from '../../integration-master/types';

export interface RequestODataResponseWizardState {
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
  response: RequestODataResponseResponseConfig;
}

export interface RequestODataResponseResponseConfig {
  type: PayloadBodyType;
  status_code: number;
  body: unknown;
  headers?: Record<string, unknown>;
}

export interface RequestODataResponsePatternRequest {
  name: string;
  slug: string;
  input_contract: InputContract;
  odata_step: ODataStepConfig;
  response: RequestODataResponseResponseConfig;
}

export interface RequestODataResponsePreviewResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  endpoint: Record<string, unknown>;
  incoming_request: unknown;
  odata_request: Record<string, unknown>;
  odata_result: Record<string, unknown> | null;
  response_to_caller: unknown;
  human_steps: string[];
  advanced: Record<string, unknown>;
}

export interface RequestODataResponseCreateResponse {
  draft_id: string;
  compile: CompileDraftResponse;
  preview: RequestODataResponsePreviewResponse;
}

export interface RequestODataResponseRunTestRequest {
  integration_flow_id: string;
  dry_run: boolean;
}

export type RequestODataResponseRunTestResponse = CompiledRunTestResponse;
