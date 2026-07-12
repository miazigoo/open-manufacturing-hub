import type { CompileDraftResponse, CompiledRunTestResponse, InputBusinessKey, InputContract, InputContractField, InputMode, InputOperationKey, InputParseResponse, ODataStepConfig, PayloadBodyType } from '../../integration-master/types';

export interface XmlODataXmlExtractField {
  name: string;
  path: string;
  required: boolean;
  mode: 'first' | 'all';
  example?: unknown;
}

export interface XmlODataXmlExtractConfig {
  fields: XmlODataXmlExtractField[];
}

export interface XmlODataXmlResponseConfig {
  body_type: PayloadBodyType;
  status_code: number;
  template: unknown;
  headers?: Record<string, unknown>;
}

export interface XmlODataXmlResponsePatternRequest {
  name: string;
  slug: string;
  input_contract: InputContract;
  xml_extract: XmlODataXmlExtractConfig;
  odata_step: ODataStepConfig;
  response: XmlODataXmlResponseConfig;
}

export interface XmlODataXmlResponsePreviewResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  endpoint: Record<string, unknown>;
  incoming_xml: string;
  xml_paths: Array<Record<string, unknown>>;
  extracted_variables: Record<string, unknown>;
  odata_request: Record<string, unknown>;
  odata_result: Record<string, unknown> | Record<string, unknown>[] | null;
  response_to_caller: unknown;
  human_steps: string[];
  advanced: Record<string, unknown>;
}

export interface XmlODataXmlResponseCreateResponse {
  draft_id?: string | null;
  compile: CompileDraftResponse;
  preview: XmlODataXmlResponsePreviewResponse;
}

export interface XmlODataXmlResponseRunTestRequest {
  integration_flow_id: string;
  dry_run: boolean;
}

export type XmlODataXmlResponseRunTestResponse = CompiledRunTestResponse;

export interface XmlODataXmlResponseWizardState {
  name: string;
  slug: string;
  sourceSystem: string;
  inputMode: InputMode;
  sampleText: string;
  fields: InputContractField[];
  parseResult: InputParseResponse | null;
  operationKey: InputOperationKey;
  businessKey: InputBusinessKey;
  xmlExtract: XmlODataXmlExtractConfig;
  odataStep: ODataStepConfig;
  response: XmlODataXmlResponseConfig;
}
