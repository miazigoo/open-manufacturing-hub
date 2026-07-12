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
    <section className="wizard-step integration-master-step pattern-request-step request-multiple-odata-input-step">
      <span className="step-index">01</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Incoming request</span>
          <h2>Что придёт от внешнего сервиса</h2>
          <p>Основной sample: JSON с <code>operation=lookup_order_products</code> и номером заказа в <code>number</code>. Этот номер станет фильтром OData.</p>
        </div>
        <span className="status-card neutral"><small>Endpoint preview</small><strong>POST /api/bus/in/{props.slug || 'lookup-order-products'}</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Название интеграции<input value={props.name} onChange={(event) => props.onNameChange(event.target.value)} /></label>
        <label className="field-label">Source system<select value={props.sourceSystem} onChange={(event) => props.onSourceSystemChange(event.target.value)}><option value="external_api">External API</option><option value="legacy_system">Legacy system</option><option value="site">Website / portal</option><option value="onec">1C</option><option value="other">Other</option></select></label>
        <span className="builder-help-card"><strong>Default sample</strong><span><code>{'{ "operation": "lookup_order_products", "number": "260666/6938", "format": "xml" }'}</code></span></span>
      </div>

      <EndpointSlugEditor value={props.slug} onChange={props.onSlugChange} />
      <InputTypeSelector value={props.inputMode} allowed={['json', 'xml']} onChange={props.onInputModeChange} />
      <SampleInputEditor inputMode={props.inputMode} value={props.sampleText} error={props.parseError} onChange={props.onSampleTextChange} onParse={props.onParse} parsing={props.parsing} />
      <ParsedFieldsTable fields={props.fields} operationPath={props.operationKey.field_path} businessPath={props.businessKey.path} onChange={props.onFieldsChange} onUseOperation={props.onUseOperation} onUseBusiness={props.onUseBusiness} />

      <section className="panel stack-form">
        <div className="panel-toolbar"><div><span className="eyebrow">Route key</span><h3>Как OMH поймёт, что это lookup заказа</h3><p className="microcopy">Default: <code>request.body.operation = lookup_order_products</code>.</p></div></div>
        <OperationKeySelector value={props.operationKey} suggestions={props.parseResult?.suggested_operation_keys ?? []} fields={props.fields} onChange={props.onOperationKeyChange} />
      </section>

      <section className="panel stack-form">
        <div className="panel-toolbar"><div><span className="eyebrow">Business key</span><h3>Номер заказа для Timeline</h3><p className="microcopy">Default: <code>request.body.number</code>.</p></div></div>
        <BusinessKeySelector value={props.businessKey} suggestions={props.parseResult?.suggested_business_keys ?? []} fields={props.fields} onChange={props.onBusinessKeyChange} />
      </section>
    </section>
  );
}
