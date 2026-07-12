import { useQuery } from '@tanstack/react-query';
import { connectionCenterApi } from '../../../api/connectionCenter';
import { operationCatalogApi } from '../../../api/operationCatalog';
import { EndpointHeadersEditor } from '../../integration-master/final-action/EndpointHeadersEditor';
import type { FinalActionMethod } from '../../integration-master/types';
import { operationBaseUrl, operationHeaders, operationIdentity, operationMethod } from '../operationCatalogHelpers';
import type { XmlRawBridgeTargetConfig } from './types';

interface TargetEndpointStepProps {
  target: XmlRawBridgeTargetConfig;
  onChange: (value: XmlRawBridgeTargetConfig) => void;
}

export function TargetEndpointStep({ target, onChange }: TargetEndpointStepProps) {
  const profiles = useQuery({ queryKey: ['connection-center-onec-http-options'], queryFn: connectionCenterApi.onecHttpOptions });
  const operations = useQuery({ queryKey: ['operation-catalog-onec-http-options'], queryFn: operationCatalogApi.onecHttpOptions });
  const patch = (patchValue: Partial<XmlRawBridgeTargetConfig>) => onChange({ ...target, ...patchValue });
  const connectorName = target.connector_name?.trim();
  const fullUrl = target.url?.trim() || `${(target.base_url || '').replace(/\/+$/, '')}/${(target.path || '').replace(/^\/+/, '')}`;
  const route = target.mode === 'onec_connector' && connectorName ? `${connectorName}:${target.path || '/receive-upd-xml'}` : fullUrl;

  return (
    <section className="wizard-step integration-master-step xml-raw-target-step">
      <span className="step-index">03</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Target endpoint / 1C HTTP Service</span>
          <h2>Куда переслать исходный XML</h2>
          <p>Выберите connector 1C HTTP Service или укажите полный raw URL. Body будет отправлен как XML, без JSON wrapper.</p>
        </div>
        <span className="status-card neutral"><small>Target</small><strong>{route}</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label full-span">Операция 1С для raw XML
          <select value={target.operation_id ?? ''} onChange={(event) => {
            const option = operations.data?.find((item) => item.id === event.target.value);
            if (!option) {
              patch({ operation_id: null, operation_code: null, operation_name: null });
              return;
            }
            patch({ ...operationIdentity(option), mode: option.connection_profile_id ? 'onec_connector' : 'raw_url', connector_id: option.connection_profile_id ?? target.connector_id, connector_name: option.connection_name ?? target.connector_name, method: operationMethod(option, target.method), base_url: operationBaseUrl(option) || target.base_url, path: option.path ?? target.path, url: option.full_url ?? '', headers: operationHeaders(option, target.headers), timeout_seconds: option.timeout_seconds ?? target.timeout_seconds });
          }}>
            <option value="">Manual target</option>
            {(operations.data ?? []).map((option) => <option key={option.id} value={option.id}>{option.label} · {option.path ?? option.final_url ?? 'configured'}</option>)}
          </select>
          <small>{operations.isLoading ? 'Загружаю операции...' : 'Например onec_receive_raw_xml из Operation Catalog.'}</small>
        </label>
        <label className="field-label">Mode<select value={target.mode} onChange={(event) => patch({ mode: event.target.value as XmlRawBridgeTargetConfig['mode'] })}><option value="raw_url">Raw URL</option><option value="onec_connector">1C HTTP Service connector</option></select></label>
        <label className="field-label">Method<select value={target.method} onChange={(event) => patch({ method: event.target.value as FinalActionMethod })}>{['POST', 'PUT', 'PATCH'].map((method) => <option key={method} value={method}>{method}</option>)}</select></label>
        <label className="field-label">Timeout, sec<input type="number" min={1} max={300} value={target.timeout_seconds} onChange={(event) => patch({ timeout_seconds: Number(event.target.value) || 30 })} /></label>
        <label className="field-label">Save response as<input value={target.save_response_as} onChange={(event) => patch({ save_response_as: event.target.value })} placeholder="target_response" /></label>
      </div>

      {target.mode === 'onec_connector' ? (
        <div className="metadata-grid compact-grid no-margin">
          <label className="field-label full-span">Профиль подключения
            <select value={target.connector_id ?? ''} onChange={(event) => {
              const option = profiles.data?.find((item) => item.connector_id === event.target.value);
              patch({ connector_id: option?.connector_id ?? null, connector_name: option?.label ?? '', base_url: option?.base_url ?? target.base_url });
            }}>
              <option value="">Ручные параметры / legacy</option>
              {(profiles.data ?? []).map((option) => <option key={option.profile_id} value={option.connector_id}>{option.label} · {option.base_url ?? 'configured'}</option>)}
            </select>
            <small>{profiles.isLoading ? 'Загружаю профили...' : 'Берутся только enabled 1C HTTP Service профили из Connection Center.'}</small>
          </label>
          <label className="field-label">1C connector<input value={target.connector_name ?? ''} onChange={(event) => patch({ connector_name: event.target.value })} placeholder="1C ERP HTTP Service" /></label>
          <label className="field-label">HTTP service path<input value={target.path} onChange={(event) => patch({ path: event.target.value })} placeholder="/receive-upd-xml" /></label>
          <span className="builder-help-card"><strong>Final URL preview</strong><span><code>{connectorName || '1C ERP HTTP Service'}:{target.path || '/receive-upd-xml'}</code></span></span>
        </div>
      ) : (
        <div className="metadata-grid compact-grid no-margin">
          <label className="field-label full-span">Raw URL<input value={target.url} onChange={(event) => patch({ url: event.target.value })} placeholder="http://1c-server/erp/hs/omh/receive-upd-xml" /></label>
          <label className="field-label">Base URL<input value={target.base_url} onChange={(event) => patch({ base_url: event.target.value })} placeholder="http://1c-server/erp/hs/omh" /></label>
          <label className="field-label">Path<input value={target.path} onChange={(event) => patch({ path: event.target.value })} placeholder="/receive-upd-xml" /></label>
        </div>
      )}

      <EndpointHeadersEditor value={target.headers ?? { 'Content-Type': 'application/xml; charset=utf-8' }} onChange={(headers) => patch({ headers })} />
      <label className="check-row"><input type="checkbox" checked={Boolean(target.training_mock_onec_xml_receiver)} onChange={(event) => patch({ training_mock_onec_xml_receiver: event.target.checked })} /> Использовать Training mock receiver для теста</label>
    </section>
  );
}
