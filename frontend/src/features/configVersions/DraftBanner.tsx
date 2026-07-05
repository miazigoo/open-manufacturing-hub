import { Link } from 'react-router-dom';
import { ConfigObjectType, ConfigVersion } from '../../api/configVersions';
import { formatDateTime } from '../../utils';
import { ConfigVersionBadge } from './ConfigVersionBadge';

export function DraftBanner({ objectType, objectId, draft }: { objectType: ConfigObjectType | string; objectId: string; draft: ConfigVersion | null | undefined }) {
  if (!draft) return null;
  return (
    <div className="config-draft-banner">
      <div>
        <span className="eyebrow">Unpublished draft</span>
        <strong>Changes are staged in version v{draft.version_number}</strong>
        <small>Updated {formatDateTime(draft.updated_at)}. Publish only after testing.</small>
      </div>
      <ConfigVersionBadge version={draft} />
      <Link className="primary-link" to={`/config-history/${objectType}/${objectId}`}>Open release control</Link>
    </div>
  );
}
