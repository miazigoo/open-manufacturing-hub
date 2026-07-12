export interface PatternStepperItem {
  id: string;
  label: string;
  status?: 'done' | 'active' | 'pending';
}

interface PatternStepperProps {
  steps: PatternStepperItem[];
  activeStep?: string;
}

export function PatternStepper({ steps, activeStep }: PatternStepperProps) {
  return (
    <ol className="pattern-stepper" aria-label="Pattern wizard steps">
      {steps.map((step, index) => {
        const status = step.status ?? (activeStep === step.id ? 'active' : 'pending');
        return <li key={step.id} className={status}><span>{index + 1}</span><strong>{step.label}</strong></li>;
      })}
    </ol>
  );
}
