import type { OperationProfileOption } from '../../api/operationCatalog';
import type { FinalActionBodyType, FinalActionMethod } from '../integration-master/types';

export function operationMethod(option: OperationProfileOption, fallback: FinalActionMethod = 'POST'): FinalActionMethod {
  const method = option.method;
  return method === 'GET' || method === 'POST' || method === 'PUT' || method === 'PATCH' || method === 'DELETE' ? method : fallback;
}

export function operationBodyType(option: OperationProfileOption, fallback: FinalActionBodyType = 'json'): FinalActionBodyType {
  const bodyType = option.body_type;
  return bodyType === 'json' || bodyType === 'xml' || bodyType === 'raw_text' || bodyType === 'form' ? bodyType : fallback;
}

export function operationUrl(option: OperationProfileOption): string {
  return option.final_url || option.full_url || option.path || '';
}

export function operationBaseUrl(option: OperationProfileOption): string {
  const url = operationUrl(option);
  const path = option.path || '';
  if (!url || !path || !url.endsWith(path)) return url;
  return url.slice(0, -path.length).replace(/\/+$/, '');
}

export function operationIdentity(option: OperationProfileOption) {
  return { operation_id: option.id, operation_code: option.code, operation_name: option.name };
}

export function operationHeaders(option: OperationProfileOption, fallback: Record<string, unknown>) {
  return option.headers_json ?? fallback;
}
