import { request } from './client';
import { ODataLookupTemplate } from './integrationBus';

export interface ODataResourceList { connector_id: string; resources: string[]; metadata_preview: string | null; fallback: boolean }
export interface ODataQueryRequest { resource: string; top?: number | null; filter?: string | null; select?: string | null; orderby?: string | null; paginate?: boolean }
export interface ODataQueryResponse { request_url: string | null; request: Record<string, unknown>; response: Record<string, unknown>; items: Array<Record<string, unknown>>; count: number; artifact_ids: Record<string, string> }

export const odataExplorerApi = {
  resources: (connectorId: string) => request<ODataResourceList>(`/api/odata-explorer/${connectorId}/resources`),
  query: (connectorId: string, payload: ODataQueryRequest) => request<ODataQueryResponse>(`/api/odata-explorer/${connectorId}/query`, { method: 'POST', body: JSON.stringify(payload) }),
  createLookup: (connectorId: string, payload: { name: string; resource: string; filter_template: string; extract_json: Record<string, string>; required?: boolean }) =>
    request<ODataLookupTemplate>(`/api/odata-explorer/${connectorId}/lookups`, { method: 'POST', body: JSON.stringify(payload) }),
};
