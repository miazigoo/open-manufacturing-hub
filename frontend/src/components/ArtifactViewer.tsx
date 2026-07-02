import { Artifact } from '../api/client';
import { JsonBlock } from './JsonBlock';
import { formatDateTime } from '../utils';
import { useT } from '../i18n/I18nProvider';

interface ArtifactViewerProps {
  artifact: Artifact | null;
  onDiff?: (artifact: Artifact) => void;
  onEdit?: (artifact: Artifact) => void;
}

export function ArtifactViewer({ artifact, onDiff, onEdit }: ArtifactViewerProps) {
  const t = useT();
  if (!artifact) {
    return <div className="artifact-placeholder">{t('artifact.placeholder')}</div>;
  }

  return (
    <div className="artifact-viewer">
      <div className="artifact-head">
        <div>
          <span className="eyebrow">{t('artifact.eyebrow')}</span>
          <h2>{artifact.name}</h2>
        </div>
        <div className="toolbar-actions">
          {onDiff && <button className="ghost-button" onClick={() => onDiff(artifact)}>{t('artifact.diff')}</button>}
          {onEdit && <button className="primary-button" onClick={() => onEdit(artifact)}>{t('artifact.editReplay')}</button>}
        </div>
      </div>
      <div className="metadata-grid">
        <span>{t('common.type')}<strong>{artifact.artifact_type}</strong></span>
        <span>{t('common.size')}<strong>{t('common.bytes', { count: artifact.size_bytes.toLocaleString() })}</strong></span>
        <span>{t('common.hash')}<strong>{artifact.content_hash.slice(0, 14)}</strong></span>
        <span>{t('common.created')}<strong>{formatDateTime(artifact.created_at)}</strong></span>
      </div>
      <JsonBlock value={artifact.content_json} title={t('common.payload')} />
    </div>
  );
}
