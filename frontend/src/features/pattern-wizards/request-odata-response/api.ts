import { request } from '../../../api/client';
import type { RequestODataResponseCreateResponse, RequestODataResponsePatternRequest, RequestODataResponsePreviewResponse, RequestODataResponseRunTestRequest, RequestODataResponseRunTestResponse } from './types';

export const requestODataResponseApi = {
  preview: (payload: RequestODataResponsePatternRequest) =>
    request<RequestODataResponsePreviewResponse>('/api/integration-patterns/request-odata-response/preview', { method: 'POST', body: JSON.stringify(payload) }),
  create: (payload: RequestODataResponsePatternRequest) =>
    request<RequestODataResponseCreateResponse>('/api/integration-patterns/request-odata-response/create', { method: 'POST', body: JSON.stringify(payload) }),
  runTest: (payload: RequestODataResponseRunTestRequest) =>
    request<RequestODataResponseRunTestResponse>('/api/integration-patterns/request-odata-response/run-test', { method: 'POST', body: JSON.stringify(payload) }),
};
