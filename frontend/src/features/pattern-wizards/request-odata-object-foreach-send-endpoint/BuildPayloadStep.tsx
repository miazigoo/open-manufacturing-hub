import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { mappingCenterApi } from '../../../api/mappingCenter';
import { CodeEditor } from '../../../components/CodeEditor';
import type { PayloadStepConfig } from '../../integration-master/types';
import { mappingToTemplate } from '../../mapping-center/utils';

interface BuildPayloadStepProps {
  payload: PayloadStepConfig;
  onChange: (value: PayloadStepConfig) => void;
}

const VARIABLES = ['codes', 'products[0].Номенклатура_Key', 'order.Ref_Key', 'order.Number', 'request.body.order_id', 'request.body.order_name', 'request.body.Number', 'context.run_id', 'context.event_id'];

export function BuildPayloadStep({ payload, onChange }: BuildPayloadStepProps) {
  const mappings = useQuery({ queryKey: ['mapping-center-mappings'], queryFn: () => mappingCenterApi.list() });
  const dnpMapping = mappings.data?.find((item) => item.code === 'mapping_dnp_chz_codes_import') ?? null;
  const bodyText = typeof payload.template === 'string' ? payload.template : JSON.stringify(payload.template ?? {}, null, 2);
  function insert(path: string) {
    onChange({ ...payload, template: `${bodyText}${bodyText.endsWith('\n') || !bodyText ? '' : '\n'}{{${path}}}` });
  }
  function applyDnpMapping() {
    const template = dnpMapping ? mappingToTemplate(dnpMapping) : defaultDnpMappingTemplate();
    onChange({ ...payload, body_type: 'json', json_mode: 'raw_template', template, mapping_profile_id: dnpMapping?.id ?? null, mapping_profile_code: 'mapping_dnp_chz_codes_import', mapping_profile_name: dnpMapping?.name ?? 'DNP — импорт кодов ЧЗ' });
  }
  return (
    <section className="wizard-step integration-master-step dnp-payload-step">
      <span className="step-index">05</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Payload Builder</span>
          <h2>Как собрать JSON для DnP</h2>
          <p>Ключевой момент: <code>{'"rows": "{{codes}}"'}</code> вставляет реальный массив, а не строку, потому весь placeholder занимает значение JSON-поля.</p>
        </div>
        <span className="status-card success"><small>Save as</small><strong>{payload.save_as}</strong></span>
      </div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Body type<select value={payload.body_type} onChange={(event) => onChange({ ...payload, body_type: event.target.value as PayloadStepConfig['body_type'] })}><option value="json">JSON</option><option value="xml">XML</option><option value="raw_text">Raw text</option></select></label>
        <label className="field-label">Save as<input value={payload.save_as} onChange={(event) => onChange({ ...payload, save_as: event.target.value })} /></label>
        <span className="builder-help-card"><strong>Mapping Center</strong><span>{payload.mapping_profile_code ? `Выбран mapping: ${payload.mapping_profile_name ?? payload.mapping_profile_code}` : 'Можно начать с contract-aware template и потом править raw JSON.'}</span></span>
      </div>
      <section className="builder-help-card">
        <div className="panel-toolbar compact-toolbar">
          <div><span className="eyebrow">Contract-aware template</span><h3>Use mapping template: DNP — импорт кодов ЧЗ</h3><p className="microcopy">Mapping Center хранит правила source variables to DNP request contract. Здесь template применяется как raw JSON fallback для совместимости текущего runtime.</p></div>
          <div className="action-row wrap-actions"><button type="button" className="primary-button" onClick={applyDnpMapping}>Использовать template</button><Link className="ghost-button" to="/mapping-center/mappings/new?preset=mapping_dnp_chz_codes_import">Открыть builder</Link></div>
        </div>
        {!dnpMapping && <p className="microcopy">Preset ещё не установлен. Кнопка применит встроенный fallback template; для полноценной проверки установите presets в Mapping Center.</p>}
      </section>
      <details className="variable-card odata-variable-picker" open>
        <summary><span>Переменные DnP payload</span><strong>{VARIABLES.length}</strong></summary>
        <div className="odata-variable-grid">
          {VARIABLES.map((path) => <button key={path} type="button" className="builder-help-card" onClick={() => insert(path)}><strong>{path}</strong><span>Вставить <code>{`{{${path}}}`}</code></span></button>)}
        </div>
      </details>
      <label className="field-label">DnP JSON template<CodeEditor value={bodyText} onChange={(template) => onChange({ ...payload, json_mode: 'raw_template', template })} language="json" minRows={18} /></label>
    </section>
  );
}

function defaultDnpMappingTemplate() {
  return `{
  "omh": {
    "run_id": "{{context.run_id}}",
    "event_id": "{{context.event_id}}",
    "event_type": "ChestniyZnakCodesSyncRequested",
    "entity_id": "{{request.body.order_name}}"
  },
  "payload": {
    "order_ref_key": "{{order.Ref_Key}}",
    "order_number": "{{order.Number}}",
    "rows": "{{codes}}"
  }
}`;
}
