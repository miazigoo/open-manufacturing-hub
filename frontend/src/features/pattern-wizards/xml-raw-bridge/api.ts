import { request } from '../../../api/client';
import type { XmlRawBridgeCreateResponse, XmlRawBridgePatternRequest, XmlRawBridgePreviewResponse, XmlRawBridgeRunTestRequest, XmlRawBridgeRunTestResponse } from './types';

export const xmlRawBridgeApi = {
  preview: (payload: XmlRawBridgePatternRequest) =>
    request<XmlRawBridgePreviewResponse>('/api/integration-patterns/xml-raw-bridge/preview', { method: 'POST', body: JSON.stringify(payload) }),
  create: (payload: XmlRawBridgePatternRequest) =>
    request<XmlRawBridgeCreateResponse>('/api/integration-patterns/xml-raw-bridge/create', { method: 'POST', body: JSON.stringify(payload) }),
  runTest: (payload: XmlRawBridgeRunTestRequest) =>
    request<XmlRawBridgeRunTestResponse>('/api/integration-patterns/xml-raw-bridge/run-test', { method: 'POST', body: JSON.stringify(payload) }),
};
