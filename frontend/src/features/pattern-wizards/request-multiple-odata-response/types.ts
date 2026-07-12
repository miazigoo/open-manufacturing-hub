import type { CompileDraftResponse, CompiledRunTestResponse, InputBusinessKey, InputContract, InputContractField, InputMode, InputOperationKey, InputParseResponse, ODataObjectStepConfig, ODataStepConfig, PayloadBodyType } from '../../integration-master/types';

export interface RequestMultipleODataResponseResponseConfig {
  type: PayloadBodyType;
  status_code: number;
  template: unknown;
  headers?: Record<string, unknown>;
}

export interface RequestMultipleODataResponsePatternRequest {
  name: string;
  slug: string;
  input_contract: InputContract;
  find_order: ODataStepConfig;
  read_items: ODataObjectStepConfig;
  response: RequestMultipleODataResponseResponseConfig;
}

export interface RequestMultipleODataResponsePreviewResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  endpoint: Record<string, unknown>;
  incoming_request: unknown;
  order_request: Record<string, unknown>;
  order_result: Record<string, unknown> | null;
  items_request: Record<string, unknown>;
  items_result: Record<string, unknown>[];
  response_to_caller: unknown;
  human_steps: string[];
  advanced: Record<string, unknown>;
}

export interface RequestMultipleODataResponseCreateResponse {
  draft_id: string;
  compile: CompileDraftResponse;
  preview: RequestMultipleODataResponsePreviewResponse;
}

export interface RequestMultipleODataResponseRunTestRequest {
  integration_flow_id: string;
  dry_run: boolean;
}

export type RequestMultipleODataResponseRunTestResponse = CompiledRunTestResponse;

export interface RequestMultipleODataResponseWizardState {
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
  readItems: ODataObjectStepConfig;
  response: RequestMultipleODataResponseResponseConfig;
}
