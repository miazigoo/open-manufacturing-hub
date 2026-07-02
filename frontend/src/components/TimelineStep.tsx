import { EventStep } from '../api/client';
import { useT } from '../i18n/useI18n';
import { StatusBadge } from './StatusBadge';

interface TimelineStepProps {
  step: EventStep;
  selected: boolean;
  onSelect: () => void;
}

export function TimelineStep({ step, selected, onSelect }: TimelineStepProps) {
  const t = useT();
  return (
    <button className={`timeline-step ${selected ? 'selected' : ''} ${step.status}`} onClick={onSelect}>
      <span className="step-index">{String(step.step_order).padStart(2, '0')}</span>
      <span className="step-body">
        <strong>{step.step_name}</strong>
        <span>{t('artifact.artifactsCount', { count: step.artifacts.length })}</span>
      </span>
      <StatusBadge status={step.status} compact />
    </button>
  );
}
