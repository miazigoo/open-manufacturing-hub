import { request } from '../../../api/client';
import type { DnpChzCreateResponse, DnpChzPatternRequest, DnpChzPreviewResponse, DnpChzRunTestRequest, DnpChzRunTestResponse } from './types';

export const dnpChzCodePoolApi = {
  preview: (payload: DnpChzPatternRequest) =>
    request<DnpChzPreviewResponse>('/api/integration-patterns/request-odata-object-foreach-send-endpoint/preview', { method: 'POST', body: JSON.stringify(payload) }),
  create: (payload: DnpChzPatternRequest) =>
    request<DnpChzCreateResponse>('/api/integration-patterns/request-odata-object-foreach-send-endpoint/create', { method: 'POST', body: JSON.stringify(payload) }),
  runTest: (payload: DnpChzRunTestRequest) =>
    request<DnpChzRunTestResponse>('/api/integration-patterns/request-odata-object-foreach-send-endpoint/run-test', { method: 'POST', body: JSON.stringify(payload) }),
};
