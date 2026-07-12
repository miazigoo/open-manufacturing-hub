import type { RequestPrintCallerResponseConfig } from './types';

interface CallerResponseStepProps {
  response: RequestPrintCallerResponseConfig;
  onChange: (value: RequestPrintCallerResponseConfig) => void;
}

export function CallerResponseStep({ response, onChange }: CallerResponseStepProps) {
  return (
    <section className="wizard-step integration-master-step request-print-response-step">
      <span className="step-index">06</span>
      <div className="odata-step-heading"><div><span className="eyebrow">Response to caller</span><h2>Что вернуть вызывающей системе</h2><p>Default — нормализованный print job status.</p></div></div>
      <div className="metadata-grid compact-grid no-margin">
        <ResponseCard active={response.type === 'normalized_print_status'} title="Normalized status" text="success, print_job_id, labels_count, printer, status." onClick={() => onChange({ ...response, type: 'normalized_print_status', status_code: 200 })} />
        <ResponseCard active={response.type === 'raw_printer_response'} title="Raw printer response" text="Вернуть ответ printer connector/mock как есть." onClick={() => onChange({ ...response, type: 'raw_printer_response', status_code: 200 })} />
        <ResponseCard active={response.type === 'accepted_event'} title="Accepted event" text="202 accepted без синхронного статуса печати." onClick={() => onChange({ ...response, type: 'accepted_event', status_code: 202 })} />
      </div>
    </section>
  );
}

function ResponseCard({ active, title, text, onClick }: { active: boolean; title: string; text: string; onClick: () => void }) {
  return <button type="button" className={`selectable-card ${active ? 'active' : ''}`} onClick={onClick}><strong>{title}</strong><span>{text}</span></button>;
}
