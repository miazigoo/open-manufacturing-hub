import type { ReactNode } from 'react';

export function FormGrid({ children, columns = 3, className = '' }: { children: ReactNode; columns?: 2 | 3 | 4; className?: string }) {
  return <div className={`form-grid form-grid-${columns} ${className}`.trim()}>{children}</div>;
}
