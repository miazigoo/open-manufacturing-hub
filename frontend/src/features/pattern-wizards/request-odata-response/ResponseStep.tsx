import { CodeEditor } from '../../../components/CodeEditor';
import type { PayloadBodyType } from '../../integration-master/types';
import type { RequestODataResponseResponseConfig } from './types';

interface ResponseStepProps {
  response: RequestODataResponseResponseConfig;
  saveAs: string;
  selectFields: string[];
  onChange: (value: RequestODataResponseResponseConfig) => void;
}

const RESPONSE_TYPES: Array<{ type: PayloadBodyType; title: string; description: string }> = [
  { type: 'json', title: 'JSON', description: 'Основной режим для сайта/API. OMH вернёт object/array с подстановками.' },
  { type: 'xml', title: 'XML', description: 'Для сервисов, которые ждут XML response body.' },
  { type: 'raw_text', title: 'Raw text', description: 'Для одного значения или legacy text protocol.' },
];

export function ResponseStep({ response, saveAs, selectFields, onChange }: ResponseStepProps) {
  const bodyText = typeof response.body === 'string' ? response.body : JSON.stringify(response.body ?? {}, null, 2);
  const language = response.type === 'json' ? 'json' : response.type === 'xml' ? 'xml' : 'text';
  const variables = (selectFields.length ? selectFields : ['Ref_Key', 'Description', 'ИНН', 'КПП']).map((field) => `${saveAs || 'contractor'}.${field}`);

  function changeType(type: PayloadBodyType) {
    onChange({ ...response, type, body: defaultBody(type, saveAs || 'contractor'), headers: defaultHeaders(type) });
  }

  function insertVariable(path: string) {
    onChange({ ...response, body: `${bodyText}${bodyText.endsWith('\n') || !bodyText ? '' : '\n'}{{${path}}}` });
  }

  return (
    <section className="wizard-step integration-master-step pattern-response-step">
      <span className="step-index">03</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Response builder</span>
          <h2>Что вернуть вызывающей системе</h2>
          <p>Основной режим этого паттерна — <code>sync_response</code>. Queue/async здесь не показываем, чтобы пользователь собрал быстрый endpoint.</p>
        </div>
        <span className="status-card success"><small>Response mode</small><strong>sync_response</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin request-action-cards">
        {RESPONSE_TYPES.map((option) => (
          <button key={option.type} type="button" className={`builder-help-card action-card ${response.type === option.type ? 'active' : ''}`} onClick={() => changeType(option.type)}>
            <strong>{option.title}</strong>
            <span>{option.description}</span>
          </button>
        ))}
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">HTTP status<input type="number" min={100} max={599} value={response.status_code} onChange={(event) => onChange({ ...response, status_code: Number(event.target.value) || 200 })} /></label>
        <span className="builder-help-card"><strong>Default action</strong><span>OMH соберёт `target_payload` и вернёт его caller-у без вызова внешнего endpoint.</span></span>
        <span className="builder-help-card"><strong>Save as dependency</strong><span>Если OData Save as = <code>{saveAs}</code>, используйте переменные вида <code>{`{{${saveAs}.Ref_Key}}`}</code>.</span></span>
      </div>

      <details className="variable-card odata-variable-picker" open>
        <summary><span>Переменные из OData result</span><strong>{variables.length}</strong></summary>
        <div className="odata-variable-grid">
          {variables.map((path) => (
            <button key={path} type="button" className="builder-help-card" onClick={() => insertVariable(path)}>
              <strong>{path}</strong>
              <span>Вставить <code>{`{{${path}}}`}</code> в шаблон ответа</span>
            </button>
          ))}
        </div>
      </details>

      <label className="field-label">Response template
        <CodeEditor value={bodyText} onChange={(body) => onChange({ ...response, body })} language={language} minRows={response.type === 'raw_text' ? 4 : 10} />
      </label>
    </section>
  );
}

export function defaultBody(type: PayloadBodyType, saveAs = 'contractor') {
  if (type === 'xml') {
    return `<Response>
  <Success>true</Success>
  <ContractorUUID>{{${saveAs}.Ref_Key}}</ContractorUUID>
  <ContractorName>{{${saveAs}.Description}}</ContractorName>
  <INN>{{${saveAs}.ИНН}}</INN>
</Response>`;
  }
  if (type === 'raw_text') return `{{${saveAs}.Ref_Key}}`;
  return `{
  "success": true,
  "contractor_uuid": "{{${saveAs}.Ref_Key}}",
  "contractor_name": "{{${saveAs}.Description}}",
  "inn": "{{${saveAs}.ИНН}}",
  "kpp": "{{${saveAs}.КПП}}"
}`;
}

export function defaultHeaders(type: PayloadBodyType) {
  if (type === 'xml') return { 'Content-Type': 'application/xml; charset=utf-8' };
  if (type === 'raw_text') return { 'Content-Type': 'text/plain; charset=utf-8' };
  return { 'Content-Type': 'application/json' };
}
