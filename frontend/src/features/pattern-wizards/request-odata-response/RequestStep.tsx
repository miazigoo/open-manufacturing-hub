import { BusinessKeySelector } from '../../integration-master/BusinessKeySelector';
import { EndpointSlugEditor } from '../../integration-master/EndpointSlugEditor';
import { InputTypeSelector } from '../../integration-master/InputTypeSelector';
import { OperationKeySelector } from '../../integration-master/OperationKeySelector';
import { ParsedFieldsTable } from '../../integration-master/ParsedFieldsTable';
import { SampleInputEditor } from '../../integration-master/SampleInputEditor';
import type { InputBusinessKey, InputContractField, InputMode, InputOperationKey, InputParseResponse } from '../../integration-master/types';

interface RequestStepProps {
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

export function RequestStep({
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
}: RequestStepProps) {
  return (
    <section className="wizard-step integration-master-step pattern-request-step">
      <span className="step-index">01</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Incoming request</span>
          <h2>Что приходит во входящем запросе</h2>
          <p>Задайте имя интеграции, endpoint slug, формат входящего тела и sample. OMH разберёт поля и подготовит matcher.</p>
        </div>
        <span className="status-card neutral"><small>Endpoint preview</small><strong>POST /api/bus/in/{slug || 'lookup-contractor'}</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Название интеграции<input value={name} onChange={(event) => onNameChange(event.target.value)} /></label>
        <label className="field-label">Source system<select value={sourceSystem} onChange={(event) => onSourceSystemChange(event.target.value)}><option value="external_api">External API / Website</option><option value="onec">1C</option><option value="wms">WMS</option><option value="other">Other</option></select></label>
        <span className="builder-help-card"><strong>Default example</strong><span>Сайт ищет контрагента по ИНН: `operation=lookup_contractor`, `inn=7707083893`.</span></span>
      </div>

      <EndpointSlugEditor value={slug} onChange={onSlugChange} />
      <InputTypeSelector value={inputMode} allowed={['json', 'xml', 'raw_text']} onChange={onInputModeChange} />
      <SampleInputEditor inputMode={inputMode} value={sampleText} error={parseError} onChange={onSampleTextChange} onParse={onParse} parsing={parsing} />

      <ParsedFieldsTable fields={fields} operationPath={operationKey.field_path} businessPath={businessKey.path} onChange={onFieldsChange} onUseOperation={onUseOperation} onUseBusiness={onUseBusiness} />

      <section className="panel stack-form">
        <div className="panel-toolbar"><div><span className="eyebrow">Route key</span><h3>Как OMH поймёт, что это этот сценарий</h3><p className="microcopy">Для примера используйте `request.body.operation = lookup_contractor`.</p></div></div>
        <OperationKeySelector value={operationKey} suggestions={parseResult?.suggested_operation_keys ?? []} fields={fields} onChange={onOperationKeyChange} />
      </section>

      <section className="panel stack-form">
        <div className="panel-toolbar"><div><span className="eyebrow">Business key</span><h3>Что считать номером события</h3><p className="microcopy">Для поиска контрагента это обычно `request.body.inn`.</p></div></div>
        <BusinessKeySelector value={businessKey} suggestions={parseResult?.suggested_business_keys ?? []} fields={fields} onChange={onBusinessKeyChange} />
      </section>
    </section>
  );
}
