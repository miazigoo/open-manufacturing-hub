import { request } from '../../../api/client';
import type { SourceWebApiWritebackOneCCreateResponse, SourceWebApiWritebackOneCPatternRequest, SourceWebApiWritebackOneCPreviewResponse, SourceWebApiWritebackOneCRunTestRequest, SourceWebApiWritebackOneCRunTestResponse } from './types';

export const sourceWebApiWritebackOnecApi = {
  preview: (payload: SourceWebApiWritebackOneCPatternRequest) =>
    request<SourceWebApiWritebackOneCPreviewResponse>('/api/integration-patterns/source-web-api-writeback-onec/preview', { method: 'POST', body: JSON.stringify(payload) }),
  create: (payload: SourceWebApiWritebackOneCPatternRequest) =>
    request<SourceWebApiWritebackOneCCreateResponse>('/api/integration-patterns/source-web-api-writeback-onec/create', { method: 'POST', body: JSON.stringify(payload) }),
  runTest: (payload: SourceWebApiWritebackOneCRunTestRequest) =>
    request<SourceWebApiWritebackOneCRunTestResponse>('/api/integration-patterns/source-web-api-writeback-onec/run-test', { method: 'POST', body: JSON.stringify(payload) }),
};
