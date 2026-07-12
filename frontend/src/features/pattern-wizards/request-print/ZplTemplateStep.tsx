import { CodeBlock } from '../../../components/CodeBlock';
import type { RequestPrintZplConfig } from './types';

interface ZplTemplateStepProps {
  zpl: RequestPrintZplConfig;
  onChange: (value: RequestPrintZplConfig) => void;
}

export function ZplTemplateStep({ zpl, onChange }: ZplTemplateStepProps) {
  return (
    <section className="wizard-step integration-master-step request-print-zpl-step">
      <span className="step-index">04</span>
      <div className="odata-step-heading"><div><span className="eyebrow">ZPL template</span><h2>Шаблон этикетки</h2><p>Это текстовый ZPL template, не графический дизайнер. Preview подставит первую строку labels[].</p></div></div>
      <label className="field-label">ZPL<textarea rows={14} value={zpl.template} onChange={(event) => onChange({ template: event.target.value })} /></label>
      <details className="variable-card"><summary><span>Default variables</span><strong>ZPL</strong></summary><CodeBlock code={'{{label.title}}\n{{label.sku}}\n{{label.code}}\n{{label.sequence_no}}\n{{request.body.job_key}}'} language="text" showToolbar={false} /></details>
    </section>
  );
}
