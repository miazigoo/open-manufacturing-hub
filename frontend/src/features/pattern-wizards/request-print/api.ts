import { request } from '../../../api/client';
import type { RequestPrintCreateResponse, RequestPrintPatternRequest, RequestPrintPreviewResponse, RequestPrintRunTestRequest, RequestPrintRunTestResponse, RequestPrintTestPrintRequest, RequestPrintTestPrintResponse } from './types';

export const requestPrintApi = {
  preview: (payload: RequestPrintPatternRequest) =>
    request<RequestPrintPreviewResponse>('/api/integration-patterns/request-print/preview', { method: 'POST', body: JSON.stringify(payload) }),
  create: (payload: RequestPrintPatternRequest) =>
    request<RequestPrintCreateResponse>('/api/integration-patterns/request-print/create', { method: 'POST', body: JSON.stringify(payload) }),
  runTest: (payload: RequestPrintRunTestRequest) =>
    request<RequestPrintRunTestResponse>('/api/integration-patterns/request-print/run-test', { method: 'POST', body: JSON.stringify(payload) }),
  testPrint: (payload: RequestPrintTestPrintRequest) =>
    request<RequestPrintTestPrintResponse>('/api/integration-patterns/request-print/test-print', { method: 'POST', body: JSON.stringify(payload) }),
};
