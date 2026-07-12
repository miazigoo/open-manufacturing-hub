import { request } from '../../../api/client';
import type { RequestMultipleODataResponseCreateResponse, RequestMultipleODataResponsePatternRequest, RequestMultipleODataResponsePreviewResponse, RequestMultipleODataResponseRunTestRequest, RequestMultipleODataResponseRunTestResponse } from './types';

export const requestMultipleODataResponseApi = {
  preview: (payload: RequestMultipleODataResponsePatternRequest) =>
    request<RequestMultipleODataResponsePreviewResponse>('/api/integration-patterns/request-multiple-odata-response/preview', { method: 'POST', body: JSON.stringify(payload) }),
  create: (payload: RequestMultipleODataResponsePatternRequest) =>
    request<RequestMultipleODataResponseCreateResponse>('/api/integration-patterns/request-multiple-odata-response/create', { method: 'POST', body: JSON.stringify(payload) }),
  runTest: (payload: RequestMultipleODataResponseRunTestRequest) =>
    request<RequestMultipleODataResponseRunTestResponse>('/api/integration-patterns/request-multiple-odata-response/run-test', { method: 'POST', body: JSON.stringify(payload) }),
};
