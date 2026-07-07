import { request } from './client';

export type ODataInputMode = 'json' | 'xml' | 'raw_text';
export type ODataBodyType = 'json' | 'xml' | 'raw_text';
export type ODataResponseMode = 'sync_response' | 'accepted_event' | 'proxy_response';
export type ODataFinalActionType = 'return_response' | 'send_endpoint' | 'send_onec_http_service' | 'async_accepted';
export type ODataStepType = 'odata_query' | 'odata_object_query' | 'foreach_odata';

export interface ODataMasterOperationKey { field?: string | null; value?: string | null; custom_field?: string | null }
export interface ODataMasterSource { system: string; input_mode: ODataInputMode; sample: unknown; operation_key: ODataMasterOperationKey; endpoint_slug?: string | null; auth_mode: 'none' | 'static_token'; auth_config_json: Record<string, unknown> }
export interface ODataQueryStep { type: 'odata_query'; connection: string; resource: string; filter?: string | null; select: string[]; top?: number | null; orderby?: string | null; paginate: boolean; required: boolean; save_as: string; name?: string | null }
export interface ODataObjectStep { type: 'odata_object_query'; connection: string; base_resource: string; object_key: string; tabular_part?: string | null; filter?: string | null; select: string[]; top?: number | null; orderby?: string | null; paginate: boolean; required: boolean; save_as: string; name?: string | null }
export interface ODataForeachStep { type: 'foreach_odata'; items: string; item_as: string; connection: string; resource: string; filter?: string | null; select: string[]; top?: number | null; orderby?: string | null; paginate: boolean; required: boolean; merge: 'flatten' | 'grouped' | 'first'; save_as: string; name?: string | null }
export type ODataWizardStep = ODataQueryStep | ODataObjectStep | ODataForeachStep;
export interface ODataResponseSpec { mode: ODataResponseMode; body_type: ODataBodyType; body: unknown; return_target_response?: boolean }
export interface ODataFinalAction { type: ODataFinalActionType; method: string; url?: string | null; headers: Record<string, string>; body_type: ODataBodyType; body: unknown; response_to_caller: ODataResponseSpec }
export interface ODataWizardSpec { name: string; slug: string; description?: string | null; source: ODataMasterSource; steps: ODataWizardStep[]; final_action: ODataFinalAction }
export interface ODataMasterExample { key: string; title: string; description: string; spec: ODataWizardSpec }
export interface ODataMasterPreviewResponse { builder_json: Record<string, unknown>; flow_payload: Record<string, unknown>; validation: Record<string, unknown>; preview: Record<string, unknown> }
export interface ODataMasterSaveResponse { integration_flow: Record<string, unknown>; endpoint_url: string; next_steps: string[] }
export interface ODataMasterRunTestResponse { mode: 'preview' | 'saved_flow'; result: Record<string, unknown> }

export const odataMasterApi = {
  examples: () => request<ODataMasterExample[]>('/api/odata-master/examples'),
  preview: (payload: { spec: ODataWizardSpec; run_real_queries?: boolean }) => request<ODataMasterPreviewResponse>('/api/odata-master/preview', { method: 'POST', body: JSON.stringify(payload) }),
  save: (payload: { spec: ODataWizardSpec; enabled?: boolean }) => request<ODataMasterSaveResponse>('/api/odata-master/save', { method: 'POST', body: JSON.stringify(payload) }),
  runTest: (payload: { spec?: ODataWizardSpec; flow_id?: string; run_real_queries?: boolean; dry_run?: boolean; payload_json?: Record<string, unknown> | null; payload_text?: string | null; headers_json?: Record<string, string> }) =>
    request<ODataMasterRunTestResponse>('/api/odata-master/run-test', { method: 'POST', body: JSON.stringify(payload) }),
};
