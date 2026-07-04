import type { ReactNode } from 'react';

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description?: string;
  meta?: ReactNode;
  actions?: ReactNode;
  className?: string;
}

export function PageHeader({ eyebrow, title, description, meta, actions, className = '' }: PageHeaderProps) {
  return (
    <section className={`page-header product-page-header ${className}`.trim()}>
      <div>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
        {meta && <div className="hero-meta">{meta}</div>}
      </div>
      {actions && <div className="product-header-actions">{actions}</div>}
    </section>
  );
}
