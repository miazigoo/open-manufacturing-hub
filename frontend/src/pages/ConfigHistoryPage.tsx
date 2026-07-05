import { Link, useParams } from 'react-router-dom';
import { ConfigObjectType } from '../api/configVersions';
import { VersionHistoryPanel } from '../features/configVersions';

function title(value: string | undefined) {
  return (value ?? '').replace(/_/g, ' ') || 'configuration';
}

export function ConfigHistoryPage() {
  const { objectType = '', objectId = '' } = useParams();
  return (
    <div className="page-stack config-history-page">
      <section className="page-header config-history-hero">
        <span className="eyebrow">Configuration lifecycle</span>
        <h1>Draft, test, publish, monitor, rollback</h1>
        <p>Controlled release history for {title(objectType)} <code>{objectId}</code>. Runtime objects are changed only after publish or rollback.</p>
        <div className="hero-meta"><Link className="primary-link" to="/audit">Open audit log</Link><Link className="primary-link" to="/production">Production checks</Link></div>
      </section>
      {objectType && objectId && <VersionHistoryPanel objectType={objectType as ConfigObjectType} objectId={objectId} />}
    </div>
  );
}
