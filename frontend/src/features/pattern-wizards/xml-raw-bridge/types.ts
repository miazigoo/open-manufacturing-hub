import type { CompileDraftResponse, CompiledRunTestResponse, FinalActionMethod, InputBusinessKey, InputContract, InputContractField, InputMode, InputOperationKey, InputParseResponse } from '../../integration-master/types';

export interface XmlRawBridgePolicyConfig {
  forward_unchanged: boolean;
  require_valid_xml: boolean;
  validate_xml: boolean;
  verify_hash: boolean;
}

export interface XmlRawBridgeTargetConfig {
  operation_id?: string | null;
  operation_code?: string | null;
  operation_name?: string | null;
  mode: 'onec_connector' | 'raw_url';
  connector_id?: string | null;
  connector_name?: string | null;
  method: FinalActionMethod;
  base_url: string;
  path: string;
  url: string;
  headers: Record<string, unknown>;
  timeout_seconds: number;
  save_response_as: string;
  training_mock_onec_xml_receiver?: boolean;
  mock_response_json?: unknown;
  mock_response_xml?: string | null;
  mock_response_text?: string | null;
  mock_status_code?: number;
}

export type XmlRawBridgeCallerResponseType = 'proxy_target_response' | 'fixed_success' | 'accepted_event' | 'custom_json' | 'custom_xml' | 'custom_raw';

export interface XmlRawBridgeCallerResponseConfig {
  type: XmlRawBridgeCallerResponseType;
  status_code: number;
  body?: unknown;
  headers: Record<string, unknown>;
}

export interface XmlRawBridgePatternRequest {
  name: string;
  slug: string;
  input_contract: InputContract;
  raw_xml_policy: XmlRawBridgePolicyConfig;
  target: XmlRawBridgeTargetConfig;
  caller_response: XmlRawBridgeCallerResponseConfig;
}

export interface XmlRawBridgePreviewResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  endpoint: Record<string, unknown>;
  incoming_xml: string;
  xml_paths: Array<Record<string, unknown>>;
  raw_xml_policy: Record<string, unknown>;
  target_request: Record<string, unknown> | null;
  target_response: unknown;
  hash_check: Record<string, unknown>;
  response_to_caller: unknown;
  human_steps: string[];
  advanced: Record<string, unknown>;
}

export interface XmlRawBridgeCreateResponse {
  draft_id?: string | null;
  compile: CompileDraftResponse;
  preview: XmlRawBridgePreviewResponse;
}

export interface XmlRawBridgeRunTestRequest {
  integration_flow_id: string;
  dry_run: boolean;
}

export type XmlRawBridgeRunTestResponse = CompiledRunTestResponse;

export interface XmlRawBridgeWizardState {
  name: string;
  slug: string;
  sourceSystem: string;
  inputMode: InputMode;
  sampleText: string;
  fields: InputContractField[];
  parseResult: InputParseResponse | null;
  operationKey: InputOperationKey;
  businessKey: InputBusinessKey;
  rawXmlPolicy: XmlRawBridgePolicyConfig;
  target: XmlRawBridgeTargetConfig;
  callerResponse: XmlRawBridgeCallerResponseConfig;
}
