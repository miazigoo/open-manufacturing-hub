import { CodeEditor } from '../../../components/CodeEditor';
import type { PayloadStepConfig } from '../../integration-master/types';

interface OneCWritebackPayloadStepProps {
  payload: PayloadStepConfig;
  orderSaveAs: string;
  siteResponseAs: string;
  onChange: (value: PayloadStepConfig) => void;
}

export function OneCWritebackPayloadStep({ payload, orderSaveAs, siteResponseAs, onChange }: OneCWritebackPayloadStepProps) {
  const bodyText = typeof payload.template === 'string' ? payload.template : JSON.stringify(payload.template ?? {}, null, 2);
  const order = orderSaveAs || 'order';
  const response = siteResponseAs || 'site_response';
  const variables = [`${order}.Ref_Key`, `${order}.Number`, 'request.body.site_code', `${response}.external_id`, `${response}.status`];
  return (
    <section className="wizard-step integration-master-step onec-writeback-payload-step">
      <span className="step-index">06</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">1C writeback payload</span>
          <h2>Что записать обратно в 1С</h2>
          <p>Соберите JSON для 1С HTTP service. Он должен содержать ссылку заказа, внешний ID сайта и статус.</p>
        </div>
        <span className="status-card success"><small>Save as</small><strong>{payload.save_as || 'onec_writeback_payload'}</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Save as<input value={payload.save_as} onChange={(event) => onChange({ ...payload, save_as: event.target.value })} placeholder="onec_writeback_payload" /></label>
        <span className="builder-help-card"><strong>Required dependency</strong><span>Используйте <code>{`{{${response}.external_id}}`}</code>. Wizard отдельно проверит, что сайт его вернул.</span></span>
      </div>

      <details className="variable-card odata-variable-picker" open>
        <summary><span>Переменные для 1С payload</span><strong>{variables.length}</strong></summary>
        <div className="odata-variable-grid">
          {variables.map((path) => <button key={path} type="button" className="builder-help-card" onClick={() => onChange({ ...payload, template: `${bodyText}${bodyText.endsWith('\n') ? '' : '\n'}{{${path}}}` })}><strong>{path}</strong><span>Вставить <code>{`{{${path}}}`}</code></span></button>)}
        </div>
      </details>

      <label className="field-label">Payload template
        <CodeEditor value={bodyText} onChange={(template) => onChange({ ...payload, template, json_mode: 'raw_template', body_type: 'json' })} language="json" minRows={10} />
      </label>
    </section>
  );
}
