import { useQuery } from '@tanstack/react-query';
import { connectionCenterApi } from '../../../api/connectionCenter';
import { operationCatalogApi } from '../../../api/operationCatalog';
import { EndpointHeadersEditor } from '../../integration-master/final-action/EndpointHeadersEditor';
import type { FinalActionBodySource, FinalActionBodyType, FinalActionMethod } from '../../integration-master/types';
import { operationBodyType, operationHeaders, operationIdentity, operationMethod, operationUrl } from '../operationCatalogHelpers';
import type { PollODataEmptyResultBehavior, PollODataTargetConfig } from './types';

interface TargetEndpointStepProps {
  target: PollODataTargetConfig;
  payloadSaveAs: string;
  onChange: (value: PollODataTargetConfig) => void;
}

const emptyBehaviors: Array<{ value: PollODataEmptyResultBehavior; title: string; description: string }> = [
  { value: 'do_nothing_success', title: 'Do nothing and mark success', description: 'Если 1С не вернула новых данных, это не ошибка.' },
  { value: 'send_empty_payload', title: 'Send empty payload', description: 'Отправить target request даже с пустым массивом.' },
  { value: 'mark_warning', title: 'Mark warning', description: 'Run successful, но в истории будет warning.' },
];

export function TargetEndpointStep({ target, payloadSaveAs, onChange }: TargetEndpointStepProps) {
  const restProfiles = useQuery({ queryKey: ['connection-center-rest-options'], queryFn: connectionCenterApi.restOptions });
  const operations = useQuery({ queryKey: ['operation-catalog-rest-options'], queryFn: operationCatalogApi.restOptions });
  const patch = (value: Partial<PollODataTargetConfig>) => onChange({ ...target, ...value });
  return (
    <section className="wizard-step integration-master-step poll-target-step">
      <span className="step-index">06</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Target endpoint</span>
          <h2>Куда отправить результат polling</h2>
          <p>OMH отправит собранный payload во внешний API/WMS/site. Если target вернёт ошибку, cursor не обновится.</p>
        </div>
        <span className="status-card neutral"><small>Body source</small><strong>{target.body_source}</strong><span>Payload step сохраняет {payloadSaveAs}.</span></span>
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
          <small>{operations.isLoading ? 'Загружаю операции...' : 'Enabled REST operations из Operation Catalog.'}</small>
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
          <input value={target.url} onChange={(event) => patch({ url: event.target.value })} placeholder="http://wms.local/api/orders/import" />
          <small>Training mock: <code>/api/training/mock-wms/orders/import</code>.</small>
        </label>
        <label className="field-label">Body source
          <select value={String(target.body_source)} onChange={(event) => patch({ body_source: event.target.value as FinalActionBodySource })}>
            <option value="target_payload">target_payload</option>
            <option value="custom">custom</option>
            <option value="none">none</option>
          </select>
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
          <input type="number" min={1} max={300} value={target.timeout_seconds} onChange={(event) => patch({ timeout_seconds: Number(event.target.value) || 30 })} />
        </label>
      </div>
      <EndpointHeadersEditor value={target.headers} onChange={(headers) => patch({ headers })} />
      <div className="metadata-grid compact-grid no-margin request-action-cards">
        {emptyBehaviors.map((option) => (
          <button key={option.value} type="button" className={`builder-help-card action-card ${target.empty_result_behavior === option.value ? 'active' : ''}`} onClick={() => patch({ empty_result_behavior: option.value })}>
            <strong>{option.title}</strong><span>{option.description}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
