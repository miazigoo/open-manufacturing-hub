import type { ReactNode } from 'react';

interface EmptyStateProps {
  title: string;
  detail?: string;
  actions?: ReactNode;
}

export function EmptyState({ title, detail, actions }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <div className="empty-mark">Ø</div>
      <h3>{title}</h3>
      {detail && <p>{detail}</p>}
      {actions && <div className="action-row">{actions}</div>}
    </div>
  );
}
