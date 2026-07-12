import { useEffect, useState } from 'react';
import { CodeEditor } from '../../../components/CodeEditor';
import type { SourceWebApiWritebackConditionOperator, SourceWebApiWritebackExtractionConfig } from './types';

interface SiteResponseExtractionStepProps {
  extraction: SourceWebApiWritebackExtractionConfig;
  siteResponseAs: string;
  onChange: (value: SourceWebApiWritebackExtractionConfig) => void;
}

export function SiteResponseExtractionStep({ extraction, siteResponseAs, onChange }: SiteResponseExtractionStepProps) {
  const [sampleText, setSampleText] = useState(() => JSON.stringify(extraction.sample_response ?? {}, null, 2));
  const responseName = siteResponseAs || 'site_response';
  useEffect(() => { setSampleText(JSON.stringify(extraction.sample_response ?? {}, null, 2)); }, [extraction.sample_response]);

  function patch(patchValue: Partial<SourceWebApiWritebackExtractionConfig>) {
    onChange({ ...extraction, ...patchValue });
  }

  function patchCondition(patchValue: Partial<SourceWebApiWritebackExtractionConfig['success_condition']>) {
    onChange({ ...extraction, success_condition: { ...extraction.success_condition, ...patchValue } });
  }

  function commitSample(value: string) {
    try {
      const parsed = JSON.parse(value);
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) patch({ sample_response: parsed as Record<string, unknown> });
    } catch {
      // Keep the editor editable; preview will keep using the last valid JSON sample.
    }
  }

  return (
    <section className="wizard-step integration-master-step site-response-extraction-step">
      <span className="step-index">05</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Response extraction</span>
          <h2>Как понять, что сайт принял данные</h2>
          <p>OMH сохранит ответ сайта как <code>{responseName}</code>, проверит success condition и извлечёт <code>external_id</code>/<code>status</code>.</p>
        </div>
        <span className="status-card success"><small>Default</small><strong>{responseName}.external_id</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">External ID path<input value={extraction.external_id_path} onChange={(event) => patch({ external_id_path: event.target.value })} placeholder={`${responseName}.external_id`} /></label>
        <label className="field-label">Status path<input value={extraction.status_path} onChange={(event) => patch({ status_path: event.target.value })} placeholder={`${responseName}.status`} /></label>
        <label className="field-label">Success path<input value={extraction.success_condition.path} onChange={(event) => patchCondition({ path: event.target.value })} placeholder={`${responseName}.success`} /></label>
        <label className="field-label">Operator<select value={extraction.success_condition.operator} onChange={(event) => patchCondition({ operator: event.target.value as SourceWebApiWritebackConditionOperator })}><option value="eq">equals</option><option value="ne">not equals</option></select></label>
        <label className="field-label">Expected value<input value={String(extraction.success_condition.value)} onChange={(event) => patchCondition({ value: parseLiteral(event.target.value) })} placeholder="true" /></label>
      </div>

      <label className="field-label">Sample site response for preview
        <CodeEditor value={sampleText} onChange={(value) => { setSampleText(value); commitSample(value); }} language="json" minRows={7} />
        <small>Если в sample убрать <code>external_id</code>, preview покажет friendly error до сохранения flow.</small>
      </label>
    </section>
  );
}

function parseLiteral(value: string): unknown {
  const trimmed = value.trim();
  if (trimmed === 'true') return true;
  if (trimmed === 'false') return false;
  if (trimmed === 'null') return null;
  if (/^-?\d+(\.\d+)?$/.test(trimmed)) return Number(trimmed);
  return trimmed;
}
