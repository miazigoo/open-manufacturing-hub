import { JsonBlock } from '../JsonBlock';
import { EmptyPanel } from './EmptyPanel';
import { TimelineLink } from './TimelineLink';

interface ResultPanelProps {
  title?: string;
  result: unknown;
}

function eventIdFrom(value: unknown): string | null {
  if (!value || typeof value !== 'object') return null;
  const record = value as Record<string, unknown>;
  if (typeof record.event_id === 'string') return record.event_id;
  const response = record.bus_response;
  if (response && typeof response === 'object' && typeof (response as Record<string, unknown>).event_id === 'string') return (response as Record<string, unknown>).event_id as string;
  return null;
}

export function ResultPanel({ title = 'Result', result }: ResultPanelProps) {
  if (result === null || result === undefined) return <EmptyPanel title="No result yet" detail="Run a preview, save, compile or test action to inspect the response." />;
  const eventId = eventIdFrom(result);
  return (
    <div className="result-panel">
      <div className="panel-toolbar">
        <h2>{title}</h2>
        <div className="toolbar-actions">{eventId && <TimelineLink eventId={eventId} label="Open timeline" />}</div>
      </div>
      <JsonBlock title="Response JSON" value={(result as Record<string, unknown>) ?? {}} searchable />
    </div>
  );
}
