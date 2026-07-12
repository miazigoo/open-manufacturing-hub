import { request } from '../../../api/client';
import type { WmsFactToOneCCreateResponse, WmsFactToOneCPatternRequest, WmsFactToOneCPreviewResponse, WmsFactToOneCRunTestRequest, WmsFactToOneCRunTestResponse } from './types';

export const wmsFactToOnecApi = {
  preview: (payload: WmsFactToOneCPatternRequest) =>
    request<WmsFactToOneCPreviewResponse>('/api/integration-patterns/wms-fact-to-onec/preview', { method: 'POST', body: JSON.stringify(payload) }),
  create: (payload: WmsFactToOneCPatternRequest) =>
    request<WmsFactToOneCCreateResponse>('/api/integration-patterns/wms-fact-to-onec/create', { method: 'POST', body: JSON.stringify(payload) }),
  runTest: (payload: WmsFactToOneCRunTestRequest) =>
    request<WmsFactToOneCRunTestResponse>('/api/integration-patterns/wms-fact-to-onec/run-test', { method: 'POST', body: JSON.stringify(payload) }),
};
