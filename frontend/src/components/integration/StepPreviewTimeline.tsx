import type { FlowBuilderPreviewResponse } from '../../api/integrationFlows';
import { StatusBadge } from '../StatusBadge';

interface StepPreviewTimelineProps {
  preview?: FlowBuilderPreviewResponse | null;
}

export function StepPreviewTimeline({ preview }: StepPreviewTimelineProps) {
  if (!preview) return <p>Preview has not run yet.</p>;
  return (
    <div className="builder-preview-steps cockpit-preview-steps">
      {preview.steps.map((step, index) => (
        <article key={step.id} className={`preview-step ${step.status}`}>
          <span className="step-index">{String(index + 1).padStart(2, '0')}</span>
          <strong>{step.name ?? step.id}</strong>
          <StatusBadge status={step.status === 'success' ? 'ok' : 'failed'} label={step.status} compact />
          <small>{step.type}</small>
          {step.error && <small>{String(step.error.message ?? step.error.code)}</small>}
        </article>
      ))}
    </div>
  );
}
