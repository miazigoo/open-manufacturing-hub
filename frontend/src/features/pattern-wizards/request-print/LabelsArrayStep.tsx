import type { RequestPrintLabelsConfig } from './types';

interface LabelsArrayStepProps {
  labels: RequestPrintLabelsConfig;
  onChange: (value: RequestPrintLabelsConfig) => void;
}

export function LabelsArrayStep({ labels, onChange }: LabelsArrayStepProps) {
  return (
    <section className="wizard-step integration-master-step request-print-labels-step">
      <span className="step-index">03</span>
      <div className="odata-step-heading"><div><span className="eyebrow">Labels array</span><h2>Одна этикетка на строку labels[]</h2><p>В ZPL-шаблоне строки доступны как <code>label.sku</code>, <code>label.code</code>, <code>label.title</code>.</p></div></div>
      <div className="form-grid two-columns">
        <label className="field-label">Labels path<input value={labels.path} onChange={(event) => onChange({ ...labels, path: event.target.value })} /></label>
        <label className="field-label">Item alias<input value={labels.item_as} onChange={(event) => onChange({ ...labels, item_as: event.target.value || 'label' })} /></label>
      </div>
      <label className="field-label">Required fields<input value={labels.required_fields.join(', ')} onChange={(event) => onChange({ ...labels, required_fields: splitList(event.target.value) })} /></label>
      <div className="metadata-grid compact-grid no-margin">
        {['label.code', 'label.sku', 'label.title', 'label.qty', 'label.sequence_no'].map((item) => <span key={item} className="status-card neutral"><small>Variable</small><strong>{item}</strong><span>Можно использовать в ZPL.</span></span>)}
      </div>
    </section>
  );
}

function splitList(value: string) {
  return value.split(',').map((item) => item.trim()).filter(Boolean);
}
