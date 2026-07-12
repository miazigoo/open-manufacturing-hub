import type { InputBusinessKey, InputContractField, InputMode, InputOperationKey, InputParseResponse } from '../../integration-master/types';
import { slugError } from '../../integration-master/EndpointSlugEditor';

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
  onSampleTextChange: (value: string) => void;
  onParse: () => void;
}

export function InputStep({ name, slug, sourceSystem, sampleText, fields, operationKey, businessKey, parseError, parsing, onNameChange, onSlugChange, onSourceSystemChange, onSampleTextChange, onParse }: InputStepProps) {
  const slugMessage = slugError(slug);
  return (
    <section className="wizard-step integration-master-step request-print-input-step">
      <span className="step-index">01</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Incoming request</span>
          <h2>JSON-запрос на печать</h2>
          <p>1С, WMS или API отправляет operation, printer, job_key и массив labels[].</p>
        </div>
        <button type="button" className="secondary-button" disabled={parsing} onClick={onParse}>{parsing ? 'Разбираю...' : 'Разобрать поля'}</button>
      </div>
      <div className="form-grid two-columns">
        <label className="field-label">Название интеграции<input value={name} onChange={(event) => onNameChange(event.target.value)} /></label>
        <label className="field-label">Endpoint slug<input value={slug} onChange={(event) => onSlugChange(event.target.value)} /></label>
        <label className="field-label">Source system<select value={sourceSystem} onChange={(event) => onSourceSystemChange(event.target.value)}><option value="onec">1C</option><option value="wms">WMS</option><option value="external_api">External API</option></select></label>
        <label className="field-label">Input mode<input value="json" disabled /></label>
      </div>
      {slugMessage ? <div className="status-card danger"><strong>Slug invalid</strong><span>{slugMessage}</span></div> : null}
      {parseError ? <div className="status-card danger"><strong>Parse failed</strong><span>{parseError}</span></div> : null}
      <label className="field-label">Sample JSON<textarea rows={16} value={sampleText} onChange={(event) => onSampleTextChange(event.target.value)} /></label>
      <div className="metadata-grid compact-grid no-margin">
        <span className="status-card neutral"><small>Operation key</small><strong>{operationKey.field_path ?? 'request.body.operation'}</strong><span>{String(operationKey.value ?? 'print_labels')}</span></span>
        <span className="status-card neutral"><small>Business key</small><strong>{businessKey.path ?? 'request.body.job_key'}</strong><span>Идемпотентность print job.</span></span>
      </div>
      <div className="panel stack-form">
        <div className="panel-toolbar"><div><span className="eyebrow">Extracted fields</span><h3>Поля sample</h3></div></div>
        <div className="table-shell compact-table"><table><thead><tr><th>Path</th><th>Type</th><th>Example</th></tr></thead><tbody>{fields.map((field) => <tr key={field.path}><td><code>{field.path}</code></td><td>{field.type}</td><td>{String(field.example ?? '')}</td></tr>)}</tbody></table></div>
      </div>
    </section>
  );
}
