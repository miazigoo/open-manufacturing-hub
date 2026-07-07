import type { ReactNode } from 'react';

interface MasterStepLayoutProps { index: string; title: string; description: string; children: ReactNode }

export function MasterStepLayout({ index, title, description, children }: MasterStepLayoutProps) {
  return (
    <section className="wizard-step integration-master-step">
      <span className="step-index">{index}</span>
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      {children}
    </section>
  );
}
