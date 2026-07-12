import { CodeEditor } from '../../../components/CodeEditor';
import type { PayloadStepConfig } from '../../integration-master/types';

interface SitePayloadStepProps {
  payload: PayloadStepConfig;
  orderSaveAs: string;
  selectFields: string[];
  onChange: (value: PayloadStepConfig) => void;
}

export function SitePayloadStep({ payload, orderSaveAs, selectFields, onChange }: SitePayloadStepProps) {
  const bodyText = typeof payload.template === 'string' ? payload.template : JSON.stringify(payload.template ?? {}, null, 2);
  const order = orderSaveAs || 'order';
  const variables = ['request.body.site_code', 'request.body.order_number', ...(selectFields.length ? selectFields : ['Ref_Key', 'Number', 'Date', 'Posted']).map((field) => `${order}.${field}`)];
  return (
    <section className="wizard-step integration-master-step source-site-payload-step">
      <span className="step-index">03</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Site payload</span>
          <h2>JSON, который уйдёт на сайт</h2>
          <p>Соберите payload из входящего запроса и найденного заказа. Default save as: <code>site_payload</code>.</p>
        </div>
        <span className="status-card success"><small>Save as</small><strong>{payload.save_as || 'site_payload'}</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Save as<input value={payload.save_as} onChange={(event) => onChange({ ...payload, save_as: event.target.value })} placeholder="site_payload" /></label>
        <span className="builder-help-card"><strong>Body source</strong><span>Следующий HTTP-шаг отправляет <code>{payload.save_as || 'site_payload'}</code>.</span></span>
        <span className="builder-help-card"><strong>OData dependency</strong><span>Используйте <code>{`{{${order}.Ref_Key}}`}</code>, <code>{`{{${order}.Number}}`}</code>.</span></span>
      </div>

      <details className="variable-card odata-variable-picker" open>
        <summary><span>Переменные для site payload</span><strong>{variables.length}</strong></summary>
        <div className="odata-variable-grid">
          {variables.map((path) => <button key={path} type="button" className="builder-help-card" onClick={() => onChange({ ...payload, template: `${bodyText}${bodyText.endsWith('\n') ? '' : '\n'}{{${path}}}` })}><strong>{path}</strong><span>Вставить <code>{`{{${path}}}`}</code></span></button>)}
        </div>
      </details>

      <label className="field-label">Payload template
        <CodeEditor value={bodyText} onChange={(template) => onChange({ ...payload, template, json_mode: 'raw_template', body_type: 'json' })} language="json" minRows={12} />
      </label>
    </section>
  );
}
