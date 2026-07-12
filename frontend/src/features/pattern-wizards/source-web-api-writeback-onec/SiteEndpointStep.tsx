import { useQuery } from '@tanstack/react-query';
import { operationCatalogApi } from '../../../api/operationCatalog';
import { CodeEditor } from '../../../components/CodeEditor';
import { EndpointHeadersEditor } from '../../integration-master/final-action/EndpointHeadersEditor';
import type { FinalActionBodyType, FinalActionMethod } from '../../integration-master/types';
import { operationBodyType, operationHeaders, operationIdentity, operationMethod, operationUrl } from '../operationCatalogHelpers';
import type { SourceWebApiWritebackEndpointConfig } from './types';

interface SiteEndpointStepProps {
  endpoint: SourceWebApiWritebackEndpointConfig;
  payloadSaveAs: string;
  onChange: (value: SourceWebApiWritebackEndpointConfig) => void;
}

export function SiteEndpointStep({ endpoint, payloadSaveAs, onChange }: SiteEndpointStepProps) {
  const operations = useQuery({ queryKey: ['operation-catalog-rest-options'], queryFn: operationCatalogApi.restOptions });
  const patch = (patchValue: Partial<SourceWebApiWritebackEndpointConfig>) => onChange({ ...endpoint, ...patchValue });
  return (
    <section className="wizard-step integration-master-step site-endpoint-step">
      <span className="step-index">04</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Site endpoint</span>
          <h2>Куда отправить данные на сайте</h2>
          <p>Настройте POST на сайт/API и имя переменной, куда сохранить ответ. Default: <code>site_response</code>.</p>
        </div>
        <span className="status-card neutral"><small>Save response as</small><strong>{endpoint.save_response_as || 'site_response'}</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label full-span">Операция сайта/API
          <select value={endpoint.operation_id ?? ''} onChange={(event) => {
            const option = operations.data?.find((item) => item.id === event.target.value);
            if (!option) {
              patch({ operation_id: null, operation_code: null, operation_name: null });
              return;
            }
            patch({ ...operationIdentity(option), method: operationMethod(option, endpoint.method), url: operationUrl(option), headers: operationHeaders(option, endpoint.headers), body_type: operationBodyType(option, endpoint.body_type), timeout_seconds: option.timeout_seconds ?? endpoint.timeout_seconds });
          }}>
            <option value="">Manual site endpoint</option>
            {(operations.data ?? []).map((option) => <option key={option.id} value={option.id}>{option.label} · {option.final_url ?? option.path ?? 'configured'}</option>)}
          </select>
          <small>{operations.isLoading ? 'Загружаю операции...' : 'Для Website API operation, CRM sync или другого REST target.'}</small>
        </label>
        <label className="field-label">Method<select value={endpoint.method} onChange={(event) => patch({ method: event.target.value as FinalActionMethod })}>{['POST', 'PUT', 'PATCH', 'DELETE', 'GET'].map((method) => <option key={method} value={method}>{method}</option>)}</select></label>
        <label className="field-label full-span">URL<input value={endpoint.url} onChange={(event) => patch({ url: event.target.value })} placeholder="http://site.local/api/orders/import" /><small>Training mock endpoint: <code>/api/training/mock-site/orders/import</code>.</small></label>
        <label className="field-label">Body source<input value={endpoint.body_source} onChange={(event) => patch({ body_source: event.target.value })} placeholder={payloadSaveAs || 'site_payload'} /><small>Payload step сейчас сохраняет: {payloadSaveAs || 'site_payload'}.</small></label>
        <label className="field-label">Body type<select value={endpoint.body_type} onChange={(event) => patch({ body_type: event.target.value as FinalActionBodyType })}><option value="json">JSON</option><option value="xml">XML</option><option value="raw_text">Raw text</option><option value="form" disabled>Form, позже</option></select></label>
        <label className="field-label">Timeout, sec<input type="number" min={1} max={300} value={endpoint.timeout_seconds} onChange={(event) => patch({ timeout_seconds: Number(event.target.value) || 20 })} /></label>
        <label className="field-label">Save response as<input value={endpoint.save_response_as} onChange={(event) => patch({ save_response_as: event.target.value })} placeholder="site_response" /></label>
      </div>

      {endpoint.body_source === 'custom' ? (
        <label className="field-label full-span">Custom request body
          <CodeEditor value={typeof endpoint.custom_body === 'string' ? endpoint.custom_body : JSON.stringify(endpoint.custom_body ?? {}, null, 2)} onChange={(value) => patch({ custom_body: value })} language={endpoint.body_type === 'xml' ? 'xml' : endpoint.body_type === 'raw_text' ? 'text' : 'json'} minRows={8} />
        </label>
      ) : null}

      <EndpointHeadersEditor value={endpoint.headers ?? { 'Content-Type': 'application/json' }} onChange={(headers) => patch({ headers })} />
    </section>
  );
}
