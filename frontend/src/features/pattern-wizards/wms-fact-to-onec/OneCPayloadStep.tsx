import { CodeEditor } from '../../../components/CodeEditor';
import type { PayloadStepConfig } from '../../integration-master/types';

interface OneCPayloadStepProps {
  payload: PayloadStepConfig;
  orderSaveAs: string;
  onChange: (value: PayloadStepConfig) => void;
}

export function OneCPayloadStep({ payload, orderSaveAs, onChange }: OneCPayloadStepProps) {
  const bodyText = typeof payload.template === 'string' ? payload.template : JSON.stringify(payload.template ?? {}, null, 2);
  const order = orderSaveAs || 'order';
  const variables = [
    `${order}.Ref_Key`,
    'request.body.order_number',
    'request.body.wms_shipment_id',
    'request.body.status',
    'request.body.warehouse_code',
    'request.body.shipped_at',
    'request.body.items',
    'request.body.items[0].sku',
    'request.body.items[0].qty',
    'request.body.items[0].barcode',
  ];

  function insertVariable(path: string) {
    onChange({ ...payload, template: `${bodyText}${bodyText.endsWith('\n') || !bodyText ? '' : '\n'}{{${path}}}` });
  }

  return (
    <section className="wizard-step integration-master-step wms-onec-payload-step">
      <span className="step-index">03</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">1C payload builder</span>
          <h2>Что отправить в 1С HTTP service</h2>
          <p>Payload сохраняется как <code>{payload.save_as || 'onec_payload'}</code>. Значение <code>{'"items": "{{request.body.items}}"'}</code> должно остаться массивом, не строкой.</p>
        </div>
        <span className="status-card success"><small>Save as</small><strong>{payload.save_as || 'onec_payload'}</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Save as<input value={payload.save_as} onChange={(event) => onChange({ ...payload, save_as: event.target.value })} placeholder="onec_payload" /></label>
        <span className="builder-help-card"><strong>Array-safe placeholder</strong><span>Если всё значение JSON-поля равно <code>{'{{request.body.items}}'}</code>, backend сохранит тип array.</span></span>
      </div>

      <details className="variable-card odata-variable-picker" open>
        <summary><span>Переменные для 1С payload</span><strong>{variables.length}</strong></summary>
        <div className="odata-variable-grid">
          {variables.map((path) => (
            <button key={path} type="button" className="builder-help-card" onClick={() => insertVariable(path)}>
              <strong>{path}</strong>
              <span>Вставить <code>{`{{${path}}}`}</code></span>
            </button>
          ))}
        </div>
      </details>

      <label className="field-label">Payload template
        <CodeEditor value={bodyText} onChange={(template) => onChange({ ...payload, template, json_mode: 'raw_template', body_type: 'json' })} language="json" minRows={15} />
      </label>
    </section>
  );
}
