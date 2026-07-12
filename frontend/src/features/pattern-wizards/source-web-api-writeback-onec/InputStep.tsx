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

export function InputStep({
  name,
  slug,
  sourceSystem,
  inputMode,
  sampleText,
  fields,
  parseResult,
  operationKey,
  businessKey,
  parseError,
  parsing,
  onNameChange,
  onSlugChange,
  onSourceSystemChange,
  onInputModeChange,
  onSampleTextChange,
  onFieldsChange,
  onOperationKeyChange,
  onBusinessKeyChange,
  onUseOperation,
  onUseBusiness,
  onParse,
}: InputStepProps) {
  return (
    <section className="wizard-step integration-master-step pattern-request-step">
      <span className="step-index">01</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Incoming request</span>
          <h2>Что 1С отправляет в OMH</h2>
          <p>Default sample: 1С просит опубликовать заказ на сайте. OMH матчится по <code>operation=publish_order_to_site</code> и берёт бизнес-ключ <code>order_number</code>.</p>
        </div>
        <span className="status-card neutral"><small>Endpoint preview</small><strong>POST /api/bus/in/{slug || 'publish-order-to-site'}</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Название интеграции<input value={name} onChange={(event) => onNameChange(event.target.value)} /></label>
        <label className="field-label">Source system<select value={sourceSystem} onChange={(event) => onSourceSystemChange(event.target.value)}><option value="onec">1C</option><option value="external_api">External API / Website</option><option value="wms">WMS</option><option value="other">Other</option></select></label>
        <span className="builder-help-card"><strong>Default example</strong><span><code>operation=publish_order_to_site</code>, <code>order_number=260666/6938</code>, <code>site_code=B2B</code>.</span></span>
      </div>

      <EndpointSlugEditor value={slug} onChange={onSlugChange} />
      <InputTypeSelector value={inputMode} allowed={['json']} onChange={onInputModeChange} />
      <SampleInputEditor inputMode={inputMode} value={sampleText} error={parseError} onChange={onSampleTextChange} onParse={onParse} parsing={parsing} />

      <ParsedFieldsTable fields={fields} operationPath={operationKey.field_path} businessPath={businessKey.path} onChange={onFieldsChange} onUseOperation={onUseOperation} onUseBusiness={onUseBusiness} />

      <section className="panel stack-form">
        <div className="panel-toolbar"><div><span className="eyebrow">Route key</span><h3>Как OMH выберет этот flow</h3><p className="microcopy">Используйте <code>request.body.operation = publish_order_to_site</code>.</p></div></div>
        <OperationKeySelector value={operationKey} suggestions={parseResult?.suggested_operation_keys ?? []} fields={fields} onChange={onOperationKeyChange} />
      </section>

      <section className="panel stack-form">
        <div className="panel-toolbar"><div><span className="eyebrow">Business key</span><h3>Номер заказа для поиска в OData</h3><p className="microcopy">Default: <code>request.body.order_number</code>.</p></div></div>
        <BusinessKeySelector value={businessKey} suggestions={parseResult?.suggested_business_keys ?? []} fields={fields} onChange={onBusinessKeyChange} />
      </section>
    </section>
  );
}
