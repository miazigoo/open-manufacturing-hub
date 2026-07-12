import { BusinessKeySelector } from '../../integration-master/BusinessKeySelector';
import { EndpointSlugEditor } from '../../integration-master/EndpointSlugEditor';
import { InputTypeSelector } from '../../integration-master/InputTypeSelector';
import { OperationKeySelector } from '../../integration-master/OperationKeySelector';
import { ParsedFieldsTable } from '../../integration-master/ParsedFieldsTable';
import { SampleInputEditor } from '../../integration-master/SampleInputEditor';
import type { InputBusinessKey, InputContractField, InputMode, InputOperationKey, InputParseResponse } from '../../integration-master/types';

interface InputStepProps {
  name: string;
  slug: string;
  sourceSystem: string;
  inputMode: InputMode;
  sampleText: string;
  fields: InputContractField[];
  parseResult: InputParseResponse | null;
  operationKey: InputOperationKey;
  businessKey: InputBusinessKey;
  parseError?: string | null;
  parsing: boolean;
  onNameChange: (value: string) => void;
  onSlugChange: (value: string) => void;
  onSourceSystemChange: (value: string) => void;
  onInputModeChange: (value: InputMode) => void;
  onSampleTextChange: (value: string) => void;
  onFieldsChange: (value: InputContractField[]) => void;
  onOperationKeyChange: (value: InputOperationKey) => void;
  onBusinessKeyChange: (value: InputBusinessKey) => void;
  onUseOperation: (field: InputContractField) => void;
  onUseBusiness: (field: InputContractField) => void;
  onParse: () => void;
}

export function InputStep(props: InputStepProps) {
  return (
    <section className="wizard-step integration-master-step pattern-request-step dnp-input-step">
      <span className="step-index">01</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Incoming DnP request</span>
          <h2>Что придёт от DnP</h2>
          <p>DnP передаёт номер заказа в поле <code>Number</code>. Это поле будет использовано для поиска заказа в 1С OData.</p>
        </div>
        <span className="status-card neutral"><small>Endpoint preview</small><strong>POST /api/bus/in/{props.slug || 'dnp_sinc_pull_codes'}</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Название интеграции<input value={props.name} onChange={(event) => props.onNameChange(event.target.value)} /></label>
        <label className="field-label">Source system<select value={props.sourceSystem} onChange={(event) => props.onSourceSystemChange(event.target.value)}><option value="dnp">DnP</option><option value="external_api">External API</option><option value="onec">1C</option><option value="other">Other</option></select></label>
        <span className="builder-help-card"><strong>Default DnP sample</strong><span>`sinc=dnp_sinc_pull_codes`, `order_name=26-0666/6938`, `Number=260666/6938`.</span></span>
      </div>

      <EndpointSlugEditor value={props.slug} onChange={props.onSlugChange} />
      <InputTypeSelector value={props.inputMode} allowed={['json']} onChange={props.onInputModeChange} />
      <SampleInputEditor inputMode={props.inputMode} value={props.sampleText} error={props.parseError} onChange={props.onSampleTextChange} onParse={props.onParse} parsing={props.parsing} />
      <ParsedFieldsTable fields={props.fields} operationPath={props.operationKey.field_path} businessPath={props.businessKey.path} onChange={props.onFieldsChange} onUseOperation={props.onUseOperation} onUseBusiness={props.onUseBusiness} />

      <section className="panel stack-form">
        <div className="panel-toolbar"><div><span className="eyebrow">Route key</span><h3>Как OMH поймёт, что это DnP sinc</h3><p className="microcopy">Основной ключ: `request.body.sinc = dnp_sinc_pull_codes`; fallback: `request.body.operation`.</p></div></div>
        <OperationKeySelector value={props.operationKey} suggestions={props.parseResult?.suggested_operation_keys ?? []} fields={props.fields} onChange={props.onOperationKeyChange} />
      </section>

      <section className="panel stack-form">
        <div className="panel-toolbar"><div><span className="eyebrow">Business key</span><h3>Как искать событие в Timeline</h3><p className="microcopy">Для DnP используем `request.body.order_name`, fallback — `request.body.Number`.</p></div></div>
        <BusinessKeySelector value={props.businessKey} suggestions={props.parseResult?.suggested_business_keys ?? []} fields={props.fields} onChange={props.onBusinessKeyChange} />
      </section>
    </section>
  );
}
