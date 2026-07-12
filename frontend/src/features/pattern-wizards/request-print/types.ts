import type { CompileDraftResponse, CompiledRunTestResponse, InputBusinessKey, InputContract, InputContractField, InputMode, InputOperationKey, InputParseResponse } from '../../integration-master/types';

export interface RequestPrintPrinterSelectionConfig {
  mode: 'from_request' | 'fixed' | 'rule_based';
  path: string;
  fixed_printer_name: string;
}

export interface RequestPrintLabelsConfig {
  path: string;
  item_as: string;
  required_fields: string[];
  optional_fields: string[];
}

export interface RequestPrintZplConfig {
  template: string;
}

export interface RequestPrintPrintModeConfig {
  mode: 'dry_run' | 'test_one_label' | 'print_all';
}

export interface RequestPrintCallerResponseConfig {
  type: 'normalized_print_status' | 'raw_printer_response' | 'accepted_event';
  status_code: number;
  body?: unknown;
  headers: Record<string, unknown>;
}

export interface RequestPrintPatternRequest {
  name: string;
  slug: string;
  input_contract: InputContract;
  printer_selection: RequestPrintPrinterSelectionConfig;
  labels: RequestPrintLabelsConfig;
  zpl: RequestPrintZplConfig;
  print_mode: RequestPrintPrintModeConfig;
  response: RequestPrintCallerResponseConfig;
}

export interface RequestPrintPreviewResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  endpoint: Record<string, unknown>;
  incoming_request: unknown;
  selected_printer: Record<string, unknown> | null;
  labels_count: number;
  rendered_zpl_first_label: string;
  rendered_zpl_all_labels: string;
  print_action: string;
  response_to_caller: unknown;
  human_steps: string[];
  advanced: Record<string, unknown>;
}

export interface RequestPrintCreateResponse {
  draft_id?: string | null;
  compile: CompileDraftResponse;
  preview: RequestPrintPreviewResponse;
}

export interface RequestPrintRunTestRequest {
  integration_flow_id: string;
  dry_run: boolean;
}

export type RequestPrintRunTestResponse = CompiledRunTestResponse;

export interface RequestPrintTestPrintRequest extends RequestPrintPatternRequest {
  dry_run: boolean;
  limit: number;
}

export interface RequestPrintTestPrintResponse {
  preview: RequestPrintPreviewResponse;
  print_result: Record<string, unknown>;
}

export interface RequestPrintWizardState {
  name: string;
  slug: string;
  sourceSystem: string;
  inputMode: InputMode;
  sampleText: string;
  fields: InputContractField[];
  parseResult: InputParseResponse | null;
  operationKey: InputOperationKey;
  businessKey: InputBusinessKey;
  printerSelection: RequestPrintPrinterSelectionConfig;
  labels: RequestPrintLabelsConfig;
  zpl: RequestPrintZplConfig;
  printMode: RequestPrintPrintModeConfig;
  response: RequestPrintCallerResponseConfig;
}
