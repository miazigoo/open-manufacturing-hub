import { request } from '../../../api/client';
import type { RequestODataSendEndpointCreateResponse, RequestODataSendEndpointPatternRequest, RequestODataSendEndpointPreviewResponse, RequestODataSendEndpointRunTestRequest, RequestODataSendEndpointRunTestResponse } from './types';

export const requestODataSendEndpointApi = {
  preview: (payload: RequestODataSendEndpointPatternRequest) =>
    request<RequestODataSendEndpointPreviewResponse>('/api/integration-patterns/request-odata-send-endpoint/preview', { method: 'POST', body: JSON.stringify(payload) }),
  create: (payload: RequestODataSendEndpointPatternRequest) =>
    request<RequestODataSendEndpointCreateResponse>('/api/integration-patterns/request-odata-send-endpoint/create', { method: 'POST', body: JSON.stringify(payload) }),
  runTest: (payload: RequestODataSendEndpointRunTestRequest) =>
    request<RequestODataSendEndpointRunTestResponse>('/api/integration-patterns/request-odata-send-endpoint/run-test', { method: 'POST', body: JSON.stringify(payload) }),
};
