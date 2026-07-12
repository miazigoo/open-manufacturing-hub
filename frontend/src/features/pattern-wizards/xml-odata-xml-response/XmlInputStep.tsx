import { XmlPathPicker } from '../../../components/xml/XmlPathPicker';
import { BusinessKeySelector } from '../../integration-master/BusinessKeySelector';
import { EndpointSlugEditor } from '../../integration-master/EndpointSlugEditor';
import { InputTypeSelector } from '../../integration-master/InputTypeSelector';
import { OperationKeySelector } from '../../integration-master/OperationKeySelector';
import { ParsedFieldsTable } from '../../integration-master/ParsedFieldsTable';
import { SampleInputEditor } from '../../integration-master/SampleInputEditor';
import type { InputBusinessKey, InputContractField, InputMode, InputOperationKey, InputParseResponse } from '../../integration-master/types';

interface XmlInputStepProps {
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

export function XmlInputStep({ name, slug, sourceSystem, inputMode, sampleText, fields, parseResult, operationKey, businessKey, parseError, parsing, onNameChange, onSlugChange, onSourceSystemChange, onInputModeChange, onSampleTextChange, onFieldsChange, onOperationKeyChange, onBusinessKeyChange, onUseOperation, onUseBusiness, onParse }: XmlInputStepProps) {
  return (
    <section className="wizard-step integration-master-step xml-odata-input-step">
      <span className="step-index">01</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Incoming XML contract</span>
          <h2>XML, который приходит в OMH</h2>
          <p>Вставьте sample XML. OMH покажет paths, route key и business key. Этот pattern дальше извлечёт значения в переменные.</p>
        </div>
        <span className="status-card neutral"><small>Endpoint preview</small><strong>POST /api/bus/in/{slug || 'lookup-order-xml'}</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Название интеграции<input value={name} onChange={(event) => onNameChange(event.target.value)} /></label>
        <label className="field-label">Source system<select value={sourceSystem} onChange={(event) => onSourceSystemChange(event.target.value)}><option value="external_api">External API</option><option value="onec">1C</option><option value="webhook">Webhook</option><option value="other">Other</option></select></label>
        <span className="builder-help-card"><strong>Default business key</strong><span><code>/Request/Number</code> попадёт в Timeline и OData filter.</span></span>
      </div>

      <EndpointSlugEditor value={slug} onChange={onSlugChange} />
      <InputTypeSelector value={inputMode} allowed={['xml']} onChange={onInputModeChange} />
      <SampleInputEditor inputMode={inputMode} value={sampleText} error={parseError} onChange={onSampleTextChange} onParse={onParse} parsing={parsing} />
      <XmlPathPicker xml={sampleText} compact />
      <ParsedFieldsTable fields={fields} operationPath={operationKey.field_path} businessPath={businessKey.path} onChange={onFieldsChange} onUseOperation={onUseOperation} onUseBusiness={onUseBusiness} />

      <section className="panel stack-form">
        <div className="panel-toolbar"><div><span className="eyebrow">Operation key</span><h3>Как отличить сценарий</h3><p className="microcopy">Default: <code>/Request/Operation = lookup_order</code>. Можно переключить на endpoint-only, если endpoint принимает один XML-сценарий.</p></div></div>
        <OperationKeySelector value={operationKey} suggestions={parseResult?.suggested_operation_keys ?? []} fields={fields} onChange={onOperationKeyChange} />
      </section>

      <section className="panel stack-form">
        <div className="panel-toolbar"><div><span className="eyebrow">Business key</span><h3>Ключ для поиска в Timeline</h3><p className="microcopy">Обычно это номер заказа, ИНН или другой lookup key из XML.</p></div></div>
        <BusinessKeySelector value={businessKey} suggestions={parseResult?.suggested_business_keys ?? []} fields={fields} onChange={onBusinessKeyChange} />
      </section>
    </section>
  );
}
