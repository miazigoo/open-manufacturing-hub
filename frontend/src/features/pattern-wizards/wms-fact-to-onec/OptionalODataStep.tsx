import { ODataStep } from '../request-odata-send-endpoint/ODataStep';
import type { InputContract, ODataStepConfig } from '../../integration-master/types';
import type { WmsFactToOneCODataLookupConfig } from './types';

interface OptionalODataStepProps {
  contract: InputContract;
  lookup: WmsFactToOneCODataLookupConfig;
  onChange: (value: WmsFactToOneCODataLookupConfig) => void;
}

export function OptionalODataStep({ contract, lookup, onChange }: OptionalODataStepProps) {
  const patchConfig = (patch: Partial<ODataStepConfig>) => onChange({ ...lookup, config: { ...lookup.config, ...patch } });
  return (
    <>
      <section className="wizard-step integration-master-step wms-optional-odata-step">
        <span className="step-index">02</span>
        <div className="odata-step-heading">
          <div>
            <span className="eyebrow">Optional OData lookup</span>
            <h2>Нужно найти заказ в 1С OData?</h2>
            <p>Default — найти <code>Document_ЗаказКлиента</code> по номеру. Если WMS уже присылает UUID 1С, выключите lookup и укажите путь к Ref_Key.</p>
          </div>
          <span className={`status-card ${lookup.enabled ? 'success' : 'neutral'}`}><small>Mode</small><strong>{lookup.enabled ? 'find order by number' : 'use WMS Ref_Key'}</strong></span>
        </div>
        <div className="metadata-grid compact-grid no-margin request-action-cards">
          <button type="button" className={`builder-help-card action-card ${lookup.enabled ? 'active' : ''}`} onClick={() => onChange({ ...lookup, enabled: true })}>
            <strong>Да, найти заказ по номеру</strong>
            <span>OMH выполнит OData filter <code>Number eq order_number</code> и сохранит результат как <code>{lookup.config.save_as || 'order'}</code>.</span>
          </button>
          <button type="button" className={`builder-help-card action-card ${!lookup.enabled ? 'active' : ''}`} onClick={() => onChange({ ...lookup, enabled: false })}>
            <strong>Нет, WMS присылает UUID 1С</strong>
            <span>OMH возьмёт Ref_Key из входящего JSON и не будет делать OData-запрос.</span>
          </button>
        </div>
        {!lookup.enabled ? (
          <label className="field-label">order_ref_key path<input value={lookup.order_ref_key_path} onChange={(event) => onChange({ ...lookup, order_ref_key_path: event.target.value })} placeholder="request.body.order_ref_key" /><small>Payload всё равно сможет использовать <code>{`{{${lookup.config.save_as || 'order'}.Ref_Key}}`}</code>.</small></label>
        ) : null}
      </section>
      {lookup.enabled ? <ODataStep contract={contract} step={lookup.config} onChange={patchConfig} /> : null}
    </>
  );
}
