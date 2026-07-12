import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { mappingCenterApi } from '../../../api/mappingCenter';
import { CodeEditor } from '../../../components/CodeEditor';
import type { PayloadBodyType, PayloadStepConfig } from '../../integration-master/types';
import { mappingToTemplate } from '../../mapping-center/utils';

interface PayloadStepProps {
  payload: PayloadStepConfig;
  saveAs: string;
  selectFields: string[];
  onChange: (value: PayloadStepConfig) => void;
}

const BODY_TYPES: Array<{ type: PayloadBodyType; title: string; description: string }> = [
  { type: 'json', title: 'JSON', description: 'Основной режим для сайта/API. OMH соберёт target_payload из request и OData result.' },
  { type: 'xml', title: 'XML', description: 'Если внешний endpoint ждёт XML body.' },
  { type: 'raw_text', title: 'Raw text', description: 'Для legacy endpoint или простого текстового protocol.' },
];

export function PayloadStep({ payload, saveAs, selectFields, onChange }: PayloadStepProps) {
  const mappings = useQuery({ queryKey: ['mapping-center-mappings'], queryFn: () => mappingCenterApi.list() });
  const websiteMapping = mappings.data?.find((item) => item.code === 'mapping_website_order_import') ?? null;
  const bodyText = typeof payload.template === 'string' ? payload.template : JSON.stringify(payload.template ?? {}, null, 2);
  const language = payload.body_type === 'json' ? 'json' : payload.body_type === 'xml' ? 'xml' : 'text';
  const odataSaveAs = saveAs || 'order';
  const variables = [
    'request.body.site_code',
    'request.body.order_number',
    ...(selectFields.length ? selectFields : ['Ref_Key', 'Number', 'Date', 'Posted']).map((field) => `${odataSaveAs}.${field}`),
  ];

  function changeType(type: PayloadBodyType) {
    onChange({ ...payload, body_type: type, json_mode: 'raw_template', template: defaultPayloadTemplate(type, odataSaveAs), save_as: payload.save_as || 'target_payload', overwrite: true });
  }

  function insertVariable(path: string) {
    onChange({ ...payload, template: `${bodyText}${bodyText.endsWith('\n') || !bodyText ? '' : '\n'}{{${path}}}` });
  }

  function applyWebsiteMapping() {
    const template = websiteMapping ? mappingToTemplate(websiteMapping) : defaultPayloadTemplate('json', odataSaveAs);
    onChange({ ...payload, body_type: 'json', json_mode: 'raw_template', template, save_as: payload.save_as || 'target_payload', overwrite: true, mapping_profile_id: websiteMapping?.id ?? null, mapping_profile_code: 'mapping_website_order_import', mapping_profile_name: websiteMapping?.name ?? 'Сайт/API — импорт заказа' });
  }

  return (
    <section className="wizard-step integration-master-step pattern-payload-step">
      <span className="step-index">03</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Payload builder</span>
          <h2>Что отправить во внешний endpoint</h2>
          <p>Соберите body из входящего запроса и результата OData. По умолчанию результат сохраняется как <code>target_payload</code>.</p>
        </div>
        <span className="status-card success"><small>Save as</small><strong>{payload.save_as || 'target_payload'}</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin request-action-cards">
        {BODY_TYPES.map((option) => (
          <button key={option.type} type="button" className={`builder-help-card action-card ${payload.body_type === option.type ? 'active' : ''}`} onClick={() => changeType(option.type)}>
            <strong>{option.title}</strong>
            <span>{option.description}</span>
          </button>
        ))}
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Save as<input value={payload.save_as} onChange={(event) => onChange({ ...payload, save_as: event.target.value })} placeholder="target_payload" /></label>
        <span className="builder-help-card"><strong>Target dependency</strong><span>Target Endpoint обычно отправляет <code>target_payload</code>. Если поменяете Save as, поменяйте Body source.</span></span>
        <span className="builder-help-card"><strong>OData dependency</strong><span>Если OData Save as = <code>{odataSaveAs}</code>, используйте <code>{`{{${odataSaveAs}.Ref_Key}}`}</code>.</span></span>
      </div>

      <section className="builder-help-card">
        <div className="panel-toolbar compact-toolbar">
          <div><span className="eyebrow">Mapping Center</span><h3>Use mapping template: Сайт/API — импорт заказа</h3><p className="microcopy">Если target operation описан контрактом, лучше начать с reusable mapping и уже потом перейти в raw JSON при необходимости.</p></div>
          <div className="action-row wrap-actions"><button type="button" className="primary-button" onClick={applyWebsiteMapping}>Использовать template</button><Link className="ghost-button" to="/mapping-center/mappings/new?preset=mapping_website_order_import">Открыть builder</Link></div>
        </div>
        <p className="microcopy">{payload.mapping_profile_code ? `Выбран mapping: ${payload.mapping_profile_name ?? payload.mapping_profile_code}` : 'Fallback raw JSON остаётся доступен ниже.'}</p>
      </section>

      <details className="variable-card odata-variable-picker" open>
        <summary><span>Переменные для payload</span><strong>{variables.length}</strong></summary>
        <div className="odata-variable-grid">
          {variables.map((path) => (
            <button key={path} type="button" className="builder-help-card" onClick={() => insertVariable(path)}>
              <strong>{path}</strong>
              <span>Вставить <code>{`{{${path}}}`}</code> в payload</span>
            </button>
          ))}
        </div>
      </details>

      <label className="field-label">Payload template
        <CodeEditor value={bodyText} onChange={(template) => onChange({ ...payload, template })} language={language} minRows={payload.body_type === 'raw_text' ? 5 : 12} />
      </label>
    </section>
  );
}

export function defaultPayloadTemplate(type: PayloadBodyType, saveAs = 'order') {
  if (type === 'xml') {
    return `<OrderImport>
  <Source>OMH</Source>
  <SiteCode>{{request.body.site_code}}</SiteCode>
  <Order>
    <UUID>{{${saveAs}.Ref_Key}}</UUID>
    <Number>{{${saveAs}.Number}}</Number>
    <Date>{{${saveAs}.Date}}</Date>
    <Posted>{{${saveAs}.Posted}}</Posted>
  </Order>
</OrderImport>`;
  }
  if (type === 'raw_text') return `order={{${saveAs}.Number}};uuid={{${saveAs}.Ref_Key}};site={{request.body.site_code}}`;
  return `{
  "source": "OMH",
  "site_code": "{{request.body.site_code}}",
  "order": {
    "uuid": "{{${saveAs}.Ref_Key}}",
    "number": "{{${saveAs}.Number}}",
    "date": "{{${saveAs}.Date}}",
    "posted": "{{${saveAs}.Posted}}"
  }
}`;
}
