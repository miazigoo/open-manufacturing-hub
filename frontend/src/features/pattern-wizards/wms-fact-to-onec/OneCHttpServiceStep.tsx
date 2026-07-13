import { useQuery } from '@tanstack/react-query';
import { connectionCenterApi } from '../../../api/connectionCenter';
import { operationCatalogApi } from '../../../api/operationCatalog';
import { EndpointHeadersEditor } from '../../integration-master/final-action/EndpointHeadersEditor';
import type { FinalActionBodyType, FinalActionMethod } from '../../integration-master/types';
import { operationBaseUrl, operationBodyType, operationHeaders, operationIdentity, operationMethod } from '../operationCatalogHelpers';
import type { WmsFactToOneCServiceConfig } from './types';

interface OneCHttpServiceStepProps {
  service: WmsFactToOneCServiceConfig;
  payloadSaveAs: string;
  onChange: (value: WmsFactToOneCServiceConfig) => void;
}

export function OneCHttpServiceStep({ service, payloadSaveAs, onChange }: OneCHttpServiceStepProps) {
  const profiles = useQuery({ queryKey: ['connection-center-onec-http-options'], queryFn: connectionCenterApi.onecHttpOptions });
  const operations = useQuery({ queryKey: ['operation-catalog-onec-http-options'], queryFn: operationCatalogApi.onecHttpOptions });
  const patch = (patchValue: Partial<WmsFactToOneCServiceConfig>) => onChange({ ...service, ...patchValue });
  const connectorName = service.connector_name?.trim();
  const fullUrl = service.url?.trim() || `${(service.base_url || '').replace(/\/+$/, '')}/${(service.path || '').replace(/^\/+/, '')}`;
  const route = connectorName && !service.url?.trim() ? `${connectorName}:${service.path || '/shipment-facts'}` : fullUrl;

  return (
    <section className="wizard-step integration-master-step wms-onec-service-step">
      <span className="step-index">04</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">1C HTTP service</span>
          <h2>Куда отправить складской факт</h2>
          <p>Рекомендуется выбрать connector 1С HTTP Service. Если connector ещё не создан, используйте полный URL.</p>
        </div>
        <span className="status-card neutral"><small>Target</small><strong>{route}</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label full-span">Операция 1С
          <select value={service.operation_id ?? ''} onChange={(event) => {
            const option = operations.data?.find((item) => item.id === event.target.value);
            if (!option) {
              patch({ operation_id: null, operation_code: null, operation_name: null });
              return;
            }
            patch({ ...operationIdentity(option), connector_id: option.connection_profile_id ?? service.connector_id, connector_name: option.connection_name ?? service.connector_name, operation: option.code, method: operationMethod(option, service.method), base_url: operationBaseUrl(option) || service.base_url, path: option.path ?? service.path, url: option.full_url ?? '', headers: operationHeaders(option, service.headers), body_type: operationBodyType(option, service.body_type), timeout_seconds: option.timeout_seconds ?? service.timeout_seconds });
          }}>
            <option value="">Manual 1C HTTP service</option>
            {(operations.data ?? []).map((option) => <option key={option.id} value={option.id}>{option.label} · {option.path ?? option.final_url ?? 'configured'}</option>)}
          </select>
          <small>{operations.isLoading ? 'Загружаю операции...' : 'Например update_shipment_status, update_stock_balance, send_inventory_result или send_movement_fact.'}</small>
        </label>
        <label className="field-label full-span">Профиль подключения
          <select value={service.connector_id ?? ''} onChange={(event) => {
            const option = profiles.data?.find((item) => item.connector_id === event.target.value);
            patch({ connector_id: option?.connector_id ?? null, connector_name: option?.label ?? '', base_url: option?.base_url ?? service.base_url });
          }}>
            <option value="">Ручные параметры / legacy</option>
            {(profiles.data ?? []).map((option) => <option key={option.profile_id} value={option.connector_id}>{option.label} · {option.base_url ?? 'configured'}</option>)}
          </select>
          <small>{profiles.isLoading ? 'Загружаю профили...' : 'Берутся только enabled 1C HTTP Service профили из Connection Center.'}</small>
        </label>
        <label className="field-label">Connector name<input value={service.connector_name ?? ''} onChange={(event) => patch({ connector_name: event.target.value })} placeholder="1C ERP HTTP Service" /><small>Для Training Sandbox: <code>Training 1C HTTP Service</code>.</small></label>
        <label className="field-label">Operation<input value={service.operation} onChange={(event) => patch({ operation: event.target.value })} placeholder="update_shipment_status" /></label>
        <label className="field-label">Method<select value={service.method} onChange={(event) => patch({ method: event.target.value as FinalActionMethod })}>{['POST', 'PUT', 'PATCH', 'DELETE', 'GET'].map((method) => <option key={method} value={method}>{method}</option>)}</select></label>
        <label className="field-label">Base URL<input value={service.base_url} onChange={(event) => patch({ base_url: event.target.value })} placeholder="http://1c-server/erp/hs/omh" /></label>
        <label className="field-label">Path<input value={service.path} onChange={(event) => patch({ path: event.target.value })} placeholder="/shipment-facts" /></label>
        <label className="field-label full-span">Override full URL<input value={service.url} onChange={(event) => patch({ url: event.target.value })} placeholder="Optional. If set, overrides connector/base URL." /><small>Examples: <code>/shipment-facts</code>, <code>/stock-balances</code>, <code>/inventory-results</code>, <code>/movements</code>.</small></label>
        <label className="field-label">Body source<input value={service.body_source} onChange={(event) => patch({ body_source: event.target.value })} placeholder={payloadSaveAs || 'onec_payload'} /><small>Payload step сейчас сохраняет: {payloadSaveAs || 'onec_payload'}.</small></label>
        <label className="field-label">Body type<select value={service.body_type} onChange={(event) => patch({ body_type: event.target.value as FinalActionBodyType })}><option value="json">JSON</option><option value="xml">XML</option><option value="raw_text">Raw text</option><option value="form" disabled>Form, позже</option></select></label>
        <label className="field-label">Timeout, sec<input type="number" min={1} max={300} value={service.timeout_seconds} onChange={(event) => patch({ timeout_seconds: Number(event.target.value) || 30 })} /></label>
        <label className="field-label">Save response as<input value={service.save_response_as} onChange={(event) => patch({ save_response_as: event.target.value })} placeholder="onec_response" /></label>
      </div>

      <EndpointHeadersEditor value={service.headers ?? { 'Content-Type': 'application/json' }} onChange={(headers) => patch({ headers })} />
    </section>
  );
}
