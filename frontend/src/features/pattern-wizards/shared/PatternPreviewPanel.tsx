import type { ReactNode } from 'react';
import { JsonBlock } from '../../../components/JsonBlock';

interface PatternPreviewPanelProps {
  title?: string;
  description?: string;
  value: unknown;
  actions?: ReactNode;
}

export function PatternPreviewPanel({ title = 'Preview', description, value, actions }: PatternPreviewPanelProps) {
  return (
    <section className="panel pattern-preview-panel">
      <div className="panel-toolbar">
        <div><span className="eyebrow">Preview</span><h3>{title}</h3>{description ? <p className="microcopy">{description}</p> : null}</div>
        {actions}
      </div>
      <JsonBlock title={title} value={value as Record<string, unknown>} searchable={false} />
    </section>
  );
}
