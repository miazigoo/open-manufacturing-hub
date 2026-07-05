import { useState } from 'react';
import { HelpPanel } from './HelpPanel';
import { helpTopics, type HelpTopic } from './helpRegistry';

export function ContextHelpButton({ topicId, topic }: { topicId?: string; topic?: HelpTopic | null }) {
  const resolved = topic ?? (topicId ? helpTopics[topicId] : null);
  const [open, setOpen] = useState(false);
  if (!resolved) return null;
  return (
    <>
      <button type="button" className="context-help-button" onClick={() => setOpen(true)}>Help</button>
      {open && <HelpPanel topic={resolved} onClose={() => setOpen(false)} />}
    </>
  );
}
