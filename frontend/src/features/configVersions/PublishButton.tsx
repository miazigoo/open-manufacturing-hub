import { useState } from 'react';
import { ConfigVersion } from '../../api/configVersions';

export function PublishButton({ draft, pending, onPublish }: { draft: ConfigVersion | null | undefined; pending?: boolean; onPublish: (comment: string) => void }) {
  const [comment, setComment] = useState('');
  if (!draft) return <button className="primary-button" disabled>No draft to publish</button>;
  return (
    <div className="config-action-box">
      <label className="field-label">Publish comment<input value={comment} onChange={(event) => setComment(event.target.value)} placeholder="What changed and why" /></label>
      <button className="primary-button" disabled={pending} onClick={() => onPublish(comment)}>Publish v{draft.version_number}</button>
    </div>
  );
}
