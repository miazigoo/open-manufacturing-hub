import { useQuery } from '@tanstack/react-query';
import { connectionCenterApi } from '../../../api/connectionCenter';
import { operationCatalogApi } from '../../../api/operationCatalog';
import { CodeEditor } from '../../../components/CodeEditor';
import { EndpointHeadersEditor } from '../../integration-master/final-action/EndpointHeadersEditor';
import type { FinalActionBodySource, FinalActionBodyType, FinalActionMethod } from '../../integration-master/types';
import { operationBodyType, operationHeaders, operationIdentity, operationMethod, operationUrl } from '../operationCatalogHelpers';
import type { RequestODataSendEndpointTargetConfig } from './types';

interface TargetEndpointStepProps {
  target: RequestODataSendEndpointTargetConfig;
  payloadSaveAs: string;
  onChange: (value: RequestODataSendEndpointTargetConfig) => void;
}

export function TargetEndpointStep({ target, payloadSaveAs, onChange }: TargetEndpointStepProps) {
  const restProfiles = useQuery({ queryKey: ['connection-center-rest-options'], queryFn: connectionCenterApi.restOptions });
  const operations = useQuery({ queryKey: ['operation-catalog-rest-options'], queryFn: operationCatalogApi.restOptions });
  const patch = (patchValue: Partial<RequestODataSendEndpointTargetConfig>) => onChange({ ...target, ...patchValue });
  return (
    <section className="wizard-step integration-master-step pattern-target-step">
      <span className="step-index">04</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Target endpoint</span>
          <h2>Куда отправить payload</h2>
          <p>Настройте HTTP endpoint, headers, body source и timeout. Preview покажет outgoing request без реальной отправки.</p>
        </div>
        <span className="status-card neutral"><small>Body source</small><strong>{target.body_source}</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label full-span">Операция подключения
          <select value={target.operation_id ?? ''} onChange={(event) => {
            const option = operations.data?.find((item) => item.id === event.target.value);
            if (!option) {
              patch({ operation_id: null, operation_code: null, operation_name: null });
              return;
            }
            patch({ ...operationIdentity(option), method: operationMethod(option, target.method), url: operationUrl(option), headers: operationHeaders(option, target.headers), body_type: operationBodyType(option, target.body_type), timeout_seconds: option.timeout_seconds ?? target.timeout_seconds });
          }}>
            <option value="">Manual endpoint / raw URL</option>
            {(operations.data ?? []).map((option) => <option key={option.id} value={option.id}>{option.label} · {option.final_url ?? option.path ?? 'configured'}</option>)}
          </select>
          <small>{operations.isLoading ? 'Загружаю операции...' : 'Enabled REST operations из Operation Catalog. Старый ручной URL ниже остаётся рабочим.'}</small>
        </label>
        <label className="field-label full-span">REST profile
          <select value={target.url} onChange={(event) => patch({ url: event.target.value })}>
            <option value="">Ручной URL</option>
            {(restProfiles.data ?? []).map((option) => <option key={option.profile_id} value={option.base_url ?? ''}>{option.label} · {option.base_url ?? 'configured'}</option>)}
          </select>
          <small>{restProfiles.isLoading ? 'Загружаю REST profiles...' : 'Enabled REST/API profiles из Connection Center.'}</small>
        </label>
        <label className="field-label">Method
          <select value={target.method} onChange={(event) => patch({ method: event.target.value as FinalActionMethod })}>
            {['POST', 'PUT', 'PATCH', 'DELETE', 'GET'].map((method) => <option key={method} value={method}>{method}</option>)}
          </select>
        </label>
        <label className="field-label full-span">URL
          <input value={target.url} onChange={(event) => patch({ url: event.target.value })} placeholder="http://site.local/api/orders/import" />
          <small>Для Training Sandbox можно указать URL backend-а до `/api/training/mock-external-api/orders/import`.</small>
        </label>
        <label className="field-label">Body source
          <select value={target.body_source} onChange={(event) => patch({ body_source: event.target.value as FinalActionBodySource })}>
            <option value="target_payload">target_payload</option>
            <option value="custom">Custom body</option>
            <option value="none">No body</option>
          </select>
          <small>Payload step сейчас сохраняет: {payloadSaveAs || 'target_payload'}.</small>
        </label>
        <label className="field-label">Body type
          <select value={target.body_type} onChange={(event) => patch({ body_type: event.target.value as FinalActionBodyType })}>
            <option value="json">JSON</option>
            <option value="xml">XML</option>
            <option value="raw_text">Raw text</option>
            <option value="form" disabled>Form, позже</option>
          </select>
        </label>
        <label className="field-label">Timeout, sec
          <input type="number" min={1} max={300} value={target.timeout_seconds} onChange={(event) => patch({ timeout_seconds: Number(event.target.value) || 20 })} />
        </label>
      </div>

      {target.body_source === 'custom' ? (
        <label className="field-label full-span">Custom request body
          <CodeEditor
            value={String(target.custom_body ?? '')}
            onChange={(value) => patch({ custom_body: value })}
            language={target.body_type === 'xml' ? 'xml' : target.body_type === 'raw_text' ? 'text' : 'json'}
            minRows={8}
            placeholder={target.body_type === 'xml' ? '<Request>{{target_payload}}</Request>' : '{"payload": "{{target_payload}}"}'}
          />
        </label>
      ) : null}

      <EndpointHeadersEditor value={target.headers ?? { 'Content-Type': 'application/json' }} onChange={(headers) => patch({ headers })} />
    </section>
  );
}
