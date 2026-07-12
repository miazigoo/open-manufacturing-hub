import { useQuery } from '@tanstack/react-query';
import { connectionCenterApi } from '../../../api/connectionCenter';
import { operationCatalogApi } from '../../../api/operationCatalog';
import { CodeEditor } from '../../../components/CodeEditor';
import { EndpointHeadersEditor } from '../../integration-master/final-action/EndpointHeadersEditor';
import type { FinalActionBodySource, FinalActionBodyType, FinalActionMethod, FinalActionReturnType } from '../../integration-master/types';
import { operationBodyType, operationHeaders, operationIdentity, operationMethod, operationUrl } from '../operationCatalogHelpers';
import type { DnpCallerResponseConfig, DnpTargetConfig } from './types';

interface SendDnpStepProps {
  target: DnpTargetConfig;
  response: DnpCallerResponseConfig;
  onTargetChange: (value: DnpTargetConfig) => void;
  onResponseChange: (value: DnpCallerResponseConfig) => void;
}

export function SendDnpStep({ target, response, onTargetChange, onResponseChange }: SendDnpStepProps) {
  const restProfiles = useQuery({ queryKey: ['connection-center-rest-options'], queryFn: connectionCenterApi.restOptions });
  const operations = useQuery({ queryKey: ['operation-catalog-rest-options'], queryFn: operationCatalogApi.restOptions });
  const patchTarget = (patch: Partial<DnpTargetConfig>) => onTargetChange({ ...target, ...patch });
  const patchResponse = (patch: Partial<DnpCallerResponseConfig>) => onResponseChange({ ...response, ...patch });
  const responseText = typeof response.body === 'string' ? response.body : JSON.stringify(response.body ?? { ok: true }, null, 2);
  return (
    <section className="wizard-step integration-master-step dnp-send-step">
      <span className="step-index">06</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Send to DnP</span>
          <h2>Куда отправить JSON и что вернуть caller-у</h2>
          <p>По умолчанию OMH отправляет <code>target_payload</code> в DnP и возвращает DnP простой <code>{'{"ok": true}'}</code>.</p>
        </div>
        <span className="status-card neutral"><small>Final action</small><strong>send_endpoint</strong></span>
      </div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label full-span">Операция подключения
          <select value={target.operation_id ?? ''} onChange={(event) => {
            const option = operations.data?.find((item) => item.id === event.target.value);
            if (!option) {
              patchTarget({ operation_id: null, operation_code: null, operation_name: null });
              return;
            }
            patchTarget({ ...operationIdentity(option), method: operationMethod(option, target.method), url: operationUrl(option), headers: operationHeaders(option, target.headers), body_type: operationBodyType(option, target.body_type), timeout_seconds: option.timeout_seconds ?? target.timeout_seconds });
          }}>
            <option value="">Ручной DnP URL</option>
            {(operations.data ?? []).map((option) => <option key={option.id} value={option.id}>{option.label} · {option.final_url ?? option.path ?? 'configured'}</option>)}
          </select>
          <small>{operations.isLoading ? 'Загружаю операции...' : 'Например DNP import CHZ codes из Operation Catalog.'}</small>
        </label>
        <label className="field-label full-span">REST profile
          <select value={target.url} onChange={(event) => patchTarget({ url: event.target.value })}>
            <option value="">Ручной DnP URL</option>
            {(restProfiles.data ?? []).map((option) => <option key={option.profile_id} value={option.base_url ?? ''}>{option.label} · {option.base_url ?? 'configured'}</option>)}
          </select>
          <small>{restProfiles.isLoading ? 'Загружаю REST profiles...' : 'Enabled REST/API profiles из Connection Center.'}</small>
        </label>
        <label className="field-label">Method<select value={target.method} onChange={(event) => patchTarget({ method: event.target.value as FinalActionMethod })}>{['POST', 'PUT', 'PATCH'].map((method) => <option key={method} value={method}>{method}</option>)}</select></label>
        <label className="field-label full-span">DnP URL<input value={target.url} onChange={(event) => patchTarget({ url: event.target.value })} /></label>
        <label className="field-label">Body source<select value={target.body_source} onChange={(event) => patchTarget({ body_source: event.target.value as FinalActionBodySource })}><option value="target_payload">target_payload</option><option value="custom">custom</option><option value="none">none</option></select></label>
        <label className="field-label">Body type<select value={target.body_type} onChange={(event) => patchTarget({ body_type: event.target.value as FinalActionBodyType })}><option value="json">JSON</option><option value="xml">XML</option><option value="raw_text">Raw text</option></select></label>
        <label className="field-label">Timeout, sec<input type="number" min={1} max={300} value={target.timeout_seconds} onChange={(event) => patchTarget({ timeout_seconds: Number(event.target.value) || 30 })} /></label>
      </div>
      <EndpointHeadersEditor value={target.headers} onChange={(headers) => patchTarget({ headers })} />
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Caller response<select value={response.type} onChange={(event) => patchResponse({ type: event.target.value as FinalActionReturnType, body: event.target.value === 'fixed_success' ? { ok: true } : response.body })}><option value="fixed_success">HTTP 200 {'{"ok": true}'}</option><option value="proxy_response">Return endpoint response</option><option value="custom_json">Custom JSON</option><option value="accepted_event">Accepted event</option></select></label>
        <label className="field-label">HTTP status<input type="number" min={100} max={599} value={response.status_code} onChange={(event) => patchResponse({ status_code: Number(event.target.value) || 200 })} /></label>
      </div>
      {response.type === 'custom_json' ? <label className="field-label">Custom caller response<CodeEditor value={responseText} onChange={(body) => patchResponse({ body })} language="json" minRows={5} /></label> : null}
    </section>
  );
}
