import { CodeEditor } from '../../../components/CodeEditor';
import type { PayloadBodyType, PayloadStepConfig } from '../../integration-master/types';

interface PayloadStepProps {
  payload: PayloadStepConfig;
  saveAs: string;
  onChange: (value: PayloadStepConfig) => void;
}

const bodyTypes: Array<{ value: PayloadBodyType; title: string; description: string }> = [
  { value: 'json', title: 'JSON', description: 'Основной режим для API/WMS.' },
  { value: 'xml', title: 'XML', description: 'Для legacy endpoint, который ждёт XML body.' },
  { value: 'raw_text', title: 'Raw text', description: 'Для простого текстового протокола.' },
];

export function PayloadStep({ payload, saveAs, onChange }: PayloadStepProps) {
  const templateText = typeof payload.template === 'string' ? payload.template : JSON.stringify(payload.template ?? {}, null, 2);
  const language = payload.body_type === 'json' ? 'json' : payload.body_type === 'xml' ? 'xml' : 'text';
  const patch = (value: Partial<PayloadStepConfig>) => onChange({ ...payload, ...value });

  function changeBodyType(type: PayloadBodyType) {
    patch({ body_type: type, template: defaultPayloadTemplate(type, saveAs), json_mode: 'raw_template' });
  }

  return (
    <section className="wizard-step integration-master-step poll-payload-step">
      <span className="step-index">05</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Payload builder</span>
          <h2>Что отправить во внешний сервис</h2>
          <p>Payload Builder получает массив <code>{saveAs}</code>, cursor и context. Поле <code>{`"{{${saveAs}}}"`}</code> сохраняет массив, а не строку.</p>
        </div>
        <span className="status-card success"><small>Save as</small><strong>{payload.save_as}</strong></span>
      </div>
      <div className="metadata-grid compact-grid no-margin request-action-cards">
        {bodyTypes.map((type) => (
          <button key={type.value} type="button" className={`builder-help-card action-card ${payload.body_type === type.value ? 'active' : ''}`} onClick={() => changeBodyType(type.value)}>
            <strong>{type.title}</strong><span>{type.description}</span>
          </button>
        ))}
      </div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Save as
          <input value={payload.save_as} onChange={(event) => patch({ save_as: event.target.value })} placeholder="target_payload" />
        </label>
        <span className="builder-help-card"><strong>Available variables</strong><span><code>{`{{${saveAs}}}`}</code>, <code>{`{{${saveAs}.length}}`}</code>, <code>{'{{cursor.last_success_at}}'}</code>, <code>{'{{context.run_id}}'}</code></span></span>
      </div>
      <label className="field-label">Payload template
        <CodeEditor value={templateText} onChange={(template) => patch({ template })} language={language} minRows={12} />
      </label>
    </section>
  );
}

export function defaultPayloadTemplate(type: PayloadBodyType, saveAs = 'orders') {
  if (type === 'xml') {
    return `<OrdersImport>
  <RunId>{{context.run_id}}</RunId>
  <CursorFrom>{{cursor.last_success_at}}</CursorFrom>
  <OrdersCount>{{${saveAs}.length}}</OrdersCount>
</OrdersImport>`;
  }
  if (type === 'raw_text') return `run={{context.run_id}};count={{${saveAs}.length}};cursor={{cursor.last_success_at}}`;
  return `{
  "omh": {
    "run_id": "{{context.run_id}}",
    "event_type": "ODataPollingOrders",
    "source_system": "1C ERP",
    "target_system": "WMS"
  },
  "payload": {
    "orders": "{{${saveAs}}}",
    "cursor_from": "{{cursor.last_success_at}}",
    "count": "{{${saveAs}.length}}"
  }
}`;
}
