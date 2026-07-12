import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

export interface PatternIntroLink {
  label: string;
  to: string;
}

interface PatternIntroPanelProps {
  eyebrow?: string;
  title: string;
  description: string;
  links?: PatternIntroLink[];
  diagram?: ReactNode;
}

export function PatternIntroPanel({ eyebrow = 'Pattern Wizard', title, description, links = [], diagram }: PatternIntroPanelProps) {
  return (
    <section className="hero-panel integration-master-hero pattern-wizard-hero pattern-intro-panel">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
        {links.length ? (
          <div className="hero-meta">
            {links.map((link) => <Link key={link.to} className="primary-link" to={link.to}>{link.label}</Link>)}
          </div>
        ) : null}
      </div>
      {diagram}
    </section>
  );
}
