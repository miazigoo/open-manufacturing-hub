import { JsonBlock } from '../JsonBlock';

interface ExternalErrorPanelProps {
  error: unknown;
}

export function ExternalErrorPanel({ error }: ExternalErrorPanelProps) {
  if (!error) return null;
  const message = error instanceof Error ? error.message : 'External system error';
  return (
    <div className="external-error-panel product-error-panel">
      <div>
        <span className="eyebrow">External Error</span>
        <h3>{message}</h3>
      </div>
      {typeof error === 'object' && <JsonBlock title="Error details" value={error as Record<string, unknown>} searchable={false} />}
    </div>
  );
}
