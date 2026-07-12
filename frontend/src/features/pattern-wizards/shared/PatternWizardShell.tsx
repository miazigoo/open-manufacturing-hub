import type { ReactNode } from 'react';
import { PatternStepper, type PatternStepperItem } from './PatternStepper';

interface PatternWizardShellProps {
  children: ReactNode;
  className?: string;
  patternId: string;
  steps?: PatternStepperItem[];
  activeStep?: string;
}

export function PatternWizardShell({ children, className = '', patternId, steps, activeStep }: PatternWizardShellProps) {
  return (
    <div className={`page-stack integration-master-page pattern-wizard-shell ${className}`} data-pattern-id={patternId}>
      {steps?.length ? <PatternStepper steps={steps} activeStep={activeStep} /> : null}
      {children}
    </div>
  );
}
