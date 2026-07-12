import { request } from '../../../api/client';
import type { PollODataSendTargetCreateResponse, PollODataSendTargetPatternRequest, PollODataSendTargetPreviewResponse, PollODataSendTargetRunTestRequest, PollODataSendTargetRunTestResponse } from './types';

export const pollODataSendTargetApi = {
  preview: (payload: PollODataSendTargetPatternRequest) =>
    request<PollODataSendTargetPreviewResponse>('/api/integration-patterns/poll-odata-send-target/preview', { method: 'POST', body: JSON.stringify(payload) }),
  create: (payload: PollODataSendTargetPatternRequest) =>
    request<PollODataSendTargetCreateResponse>('/api/integration-patterns/poll-odata-send-target/create', { method: 'POST', body: JSON.stringify(payload) }),
  runTest: (payload: PollODataSendTargetRunTestRequest) =>
    request<PollODataSendTargetRunTestResponse>('/api/integration-patterns/poll-odata-send-target/run-test', { method: 'POST', body: JSON.stringify(payload) }),
};
