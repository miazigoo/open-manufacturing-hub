import { request } from '../../../api/client';
import type { XmlODataXmlResponseCreateResponse, XmlODataXmlResponsePatternRequest, XmlODataXmlResponsePreviewResponse, XmlODataXmlResponseRunTestRequest, XmlODataXmlResponseRunTestResponse } from './types';

export const xmlODataXmlResponseApi = {
  preview: (payload: XmlODataXmlResponsePatternRequest) =>
    request<XmlODataXmlResponsePreviewResponse>('/api/integration-patterns/xml-odata-xml-response/preview', { method: 'POST', body: JSON.stringify(payload) }),
  create: (payload: XmlODataXmlResponsePatternRequest) =>
    request<XmlODataXmlResponseCreateResponse>('/api/integration-patterns/xml-odata-xml-response/create', { method: 'POST', body: JSON.stringify(payload) }),
  runTest: (payload: XmlODataXmlResponseRunTestRequest) =>
    request<XmlODataXmlResponseRunTestResponse>('/api/integration-patterns/xml-odata-xml-response/run-test', { method: 'POST', body: JSON.stringify(payload) }),
};
