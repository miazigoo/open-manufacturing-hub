import { EventStep } from '../api/client';
import { StatusBadge } from './StatusBadge';

interface TimelineStepProps {
  step: EventStep;
  selected: boolean;
  onSelect: () => void;
}

export function TimelineStep({ step, selected, onSelect }: TimelineStepProps) {
  return (
    <button className={`timeline-step ${selected ? 'selected' : ''} ${step.status}`} onClick={onSelect}>
      <span className="step-index">{String(step.step_order).padStart(2, '0')}</span>
      <span className="step-body">
        <strong>{step.step_name}</strong>
        <span>{step.artifacts.length} artifacts</span>
      </span>
      <StatusBadge status={step.status} compact />
    </button>
  );
}
