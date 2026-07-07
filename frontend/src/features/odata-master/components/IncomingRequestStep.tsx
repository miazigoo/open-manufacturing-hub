import { useEffect, useMemo, useState } from 'react';
import { CodeEditor } from '../../../components/CodeEditor';
import type { ODataWizardSpec } from '../types';
import { applySampleText, sampleAsText } from '../utils/wizardPayload';
import { extractJsonPaths } from '../utils/placeholders';

interface IncomingRequestStepProps { spec: ODataWizardSpec; onChange: (spec: ODataWizardSpec) => void }

export function IncomingRequestStep({ spec, onChange }: IncomingRequestStepProps) {
  const [sampleText, setSampleText] = useState(() => sampleAsText(spec));
  const paths = useMemo(() => spec.source.input_mode === 'json' ? extractJsonPaths(spec.source.sample) : [], [spec.source.input_mode, spec.source.sample]);

  useEffect(() => setSampleText(sampleAsText(spec)), [spec.slug]);

  function updateSample(next: string) {
    setSampleText(next);
    onChange(applySampleText(spec, next));
  }

  return (
    <section className="panel form-panel">
      <div className="panel-toolbar">
        <div>
          <span className="eyebrow">1. Входящий запрос</span>
          <h2>Кто вызывает OMH и что приходит?</h2>
          <p className="microcopy">Вставьте реальный пример запроса. Мастер покажет переменные, которые можно использовать в OData.</p>
        </div>
      </div>
      <div className="stack-form">
        <div className="metadata-grid compact-grid no-margin">
          <label className="field-label">Название интеграции<input value={spec.name} onChange={(event) => onChange({ ...spec, name: event.target.value })} /></label>
          <label className="field-label">Endpoint slug<input value={spec.slug} onChange={(event) => onChange({ ...spec, slug: event.target.value.toLowerCase().replace(/[^a-z0-9_-]+/g, '-') })} /></label>
          <label className="field-label">Source system<select value={spec.source.system} onChange={(event) => onChange({ ...spec, source: { ...spec.source, system: event.target.value } })}><option value="external_api">External API / Website</option><option value="onec">1C</option><option value="dnp">DnP</option><option value="wms">WMS</option><option value="other">Other</option></select></label>
        </div>
        <div className="metadata-grid compact-grid no-margin">
          <label className="field-label">Input type<select value={spec.source.input_mode} onChange={(event) => onChange({ ...spec, source: { ...spec.source, input_mode: event.target.value as ODataWizardSpec['source']['input_mode'], sample: event.target.value === 'json' ? {} : '' } })}><option value="json">JSON</option><option value="xml">XML</option><option value="raw_text">raw text</option></select></label>
          <label className="field-label">Ключ запроса<select value={spec.source.operation_key.field || 'operation'} onChange={(event) => onChange({ ...spec, source: { ...spec.source, operation_key: { ...spec.source.operation_key, field: event.target.value } } })}><option value="operation">field operation</option><option value="sinc">field sinc</option><option value="custom">custom field</option><option value="no_key">no key, endpoint slug only</option></select></label>
          {spec.source.operation_key.field === 'custom' && <label className="field-label">Custom field<input value={spec.source.operation_key.custom_field || ''} onChange={(event) => onChange({ ...spec, source: { ...spec.source, operation_key: { ...spec.source.operation_key, custom_field: event.target.value } } })} /></label>}
          <label className="field-label">Значение ключа<input value={spec.source.operation_key.value || ''} onChange={(event) => onChange({ ...spec, source: { ...spec.source, operation_key: { ...spec.source.operation_key, value: event.target.value } } })} placeholder="dnp_sinc_pull_codes" /></label>
        </div>
        <label className="field-label">Sample request<CodeEditor value={sampleText} onChange={updateSample} language={spec.source.input_mode === 'json' ? 'json' : spec.source.input_mode === 'xml' ? 'xml' : 'text'} minRows={8} /></label>
        {paths.length > 0 && <div className="success-note">Извлеченные пути<span>{paths.join(', ')}</span></div>}
        <label className="field-label">Auth mode<select value={spec.source.auth_mode} onChange={(event) => onChange({ ...spec, source: { ...spec.source, auth_mode: event.target.value as 'none' | 'static_token' } })}><option value="none">none</option><option value="static_token">static token</option></select></label>
      </div>
    </section>
  );
}
