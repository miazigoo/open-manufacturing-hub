import type { ReactNode } from 'react';

interface SectionCardProps {
  eyebrow?: string;
  title?: string;
  description?: string | null;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function SectionCard({ eyebrow, title, description, actions, children, className = '' }: SectionCardProps) {
  return (
    <section className={`panel product-section-card ${className}`.trim()}>
      {(eyebrow || title || description || actions) && (
        <div className="panel-toolbar">
          <div>
            {eyebrow && <span className="eyebrow">{eyebrow}</span>}
            {title && <h2>{title}</h2>}
            {description && <p>{description}</p>}
          </div>
          {actions && <div className="toolbar-actions">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}
