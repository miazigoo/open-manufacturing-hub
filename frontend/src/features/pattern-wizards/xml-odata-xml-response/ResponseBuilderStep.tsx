import { CodeEditor } from '../../../components/CodeEditor';
import type { PayloadBodyType } from '../../integration-master/types';
import type { XmlODataXmlResponseConfig } from './types';

interface ResponseBuilderStepProps {
  response: XmlODataXmlResponseConfig;
  saveAs: string;
  selectFields: string[];
  onChange: (value: XmlODataXmlResponseConfig) => void;
}

const RESPONSE_TYPES: Array<{ type: PayloadBodyType; title: string; description: string }> = [
  { type: 'xml', title: 'XML', description: 'Default для legacy/1C caller-ов.' },
  { type: 'json', title: 'JSON', description: 'Если caller ждёт объект или API-style response.' },
  { type: 'raw_text', title: 'Raw text', description: 'Если нужно вернуть одно значение.' },
];

export function ResponseBuilderStep({ response, saveAs, selectFields, onChange }: ResponseBuilderStepProps) {
  const templateText = typeof response.template === 'string' ? response.template : JSON.stringify(response.template ?? {}, null, 2);
  const language = response.body_type === 'json' ? 'json' : response.body_type === 'xml' ? 'xml' : 'text';
  const variables = (selectFields.length ? selectFields : ['Ref_Key', 'Number', 'Date', 'Posted']).map((field) => `${saveAs || 'order'}.${field}`);

  function changeType(type: PayloadBodyType) {
    onChange({ ...response, body_type: type, template: defaultTemplate(type, saveAs || 'order'), headers: defaultHeaders(type) });
  }

  function insertVariable(path: string) {
    onChange({ ...response, template: `${templateText}${templateText.endsWith('\n') || !templateText ? '' : '\n'}{{${path}}}` });
  }

  return (
    <section className="wizard-step integration-master-step xml-odata-response-step">
      <span className="step-index">04</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Response builder</span>
          <h2>Что вернуть caller-у</h2>
          <p>Шаблон рендерится после OData. XML values экранируются, missing variables попадут в friendly error.</p>
        </div>
        <span className="status-card success"><small>Response mode</small><strong>sync_response</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin request-action-cards">
        {RESPONSE_TYPES.map((option) => (
          <button key={option.type} type="button" className={`builder-help-card action-card ${response.body_type === option.type ? 'active' : ''}`} onClick={() => changeType(option.type)}>
            <strong>{option.title}</strong><span>{option.description}</span>
          </button>
        ))}
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">HTTP status<input type="number" min={100} max={599} value={response.status_code} onChange={(event) => onChange({ ...response, status_code: Number(event.target.value) || 200 })} /></label>
        <span className="builder-help-card"><strong>OData variable</strong><span>Если Save as = <code>{saveAs}</code>, используйте <code>{`{{${saveAs}.Ref_Key}}`}</code>.</span></span>
      </div>

      <details className="variable-card odata-variable-picker" open>
        <summary><span>Переменные из OData result</span><strong>{variables.length}</strong></summary>
        <div className="odata-variable-grid">
          {variables.map((path) => <button key={path} type="button" className="builder-help-card" onClick={() => insertVariable(path)}><strong>{path}</strong><span>Вставить <code>{`{{${path}}}`}</code></span></button>)}
        </div>
      </details>

      <label className="field-label">Response template<CodeEditor value={templateText} onChange={(template) => onChange({ ...response, template })} language={language} minRows={response.body_type === 'raw_text' ? 4 : 10} /></label>
    </section>
  );
}

export function defaultTemplate(type: PayloadBodyType, saveAs = 'order') {
  if (type === 'json') return `{
  "success": true,
  "order": {
    "uuid": "{{${saveAs}.Ref_Key}}",
    "number": "{{${saveAs}.Number}}",
    "date": "{{${saveAs}.Date}}",
    "posted": "{{${saveAs}.Posted}}"
  }
}`;
  if (type === 'raw_text') return `{{${saveAs}.Ref_Key}}`;
  return `<Response>
  <Success>true</Success>
  <Order>
    <UUID>{{${saveAs}.Ref_Key}}</UUID>
    <Number>{{${saveAs}.Number}}</Number>
    <Date>{{${saveAs}.Date}}</Date>
    <Posted>{{${saveAs}.Posted}}</Posted>
  </Order>
</Response>`;
}

export function defaultHeaders(type: PayloadBodyType) {
  if (type === 'xml') return { 'Content-Type': 'application/xml; charset=utf-8' };
  if (type === 'raw_text') return { 'Content-Type': 'text/plain; charset=utf-8' };
  return { 'Content-Type': 'application/json' };
}
