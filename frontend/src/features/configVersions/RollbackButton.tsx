import { useState } from 'react';
import { ConfigVersion } from '../../api/configVersions';

export function RollbackButton({ version, pending, onRollback }: { version: ConfigVersion; pending?: boolean; onRollback: (comment: string) => void }) {
  const [armed, setArmed] = useState(false);
  if (version.status === 'draft') return null;
  return (
    <div className="action-row config-rollback-row">
      {!armed ? <button className="ghost-button danger" onClick={() => setArmed(true)}>Rollback to v{version.version_number}</button> : <button className="primary-button danger" disabled={pending} onClick={() => onRollback(`Rollback to v${version.version_number}`)}>Confirm rollback</button>}
    </div>
  );
}
