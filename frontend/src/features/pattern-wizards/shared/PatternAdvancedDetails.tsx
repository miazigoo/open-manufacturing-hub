import type { ReactNode } from 'react';

interface PatternAdvancedDetailsProps {
  title?: string;
  children: ReactNode;
}

export function PatternAdvancedDetails({ title = 'Advanced details', children }: PatternAdvancedDetailsProps) {
  return (
    <details className="pattern-advanced-details">
      <summary><span>{title}</span></summary>
      {children}
    </details>
  );
}
