import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Artifact, ArtifactSummary } from '../api/client';
import { artifactsApi } from '../api/artifacts';
import { JsonBlock } from './JsonBlock';
import { LoadingState } from './LoadingState';
import { ErrorState } from './ErrorState';
import { formatDateTime } from '../utils';
import { useT } from '../i18n/useI18n';

interface ArtifactViewerProps {
  artifact: Artifact | ArtifactSummary | null;
  onDiff?: (artifact: Artifact | ArtifactSummary) => void;
  onEdit?: (artifact: Artifact) => void;
}

export function ArtifactViewer({ artifact, onDiff, onEdit }: ArtifactViewerProps) {
  const t = useT();
  const [loadRequested, setLoadRequested] = useState(false);

  // If artifact has content_json already loaded, use it; otherwise fetch on demand
  const hasContent = artifact && 'content_json' in artifact && artifact.content_json !== undefined;
  const artifactQuery = useQuery({
    queryKey: ['artifact-content', artifact?.id],
    queryFn: () => artifactsApi.get(artifact!.id),
    enabled: Boolean(artifact && !hasContent && loadRequested),
  });

  if (!artifact) {
    return <div className="artifact-placeholder">{t('artifact.placeholder')}</div>;
  }

  const fullArtifact = hasContent ? (artifact as Artifact) : artifactQuery.data;
  const sizeMb = (artifact.size_bytes / (1024 * 1024)).toFixed(2);
  const sizeKb = Math.round(artifact.size_bytes / 1024);
  const sizeLabel = artifact.size_bytes >= 1024 * 1024 ? `${sizeMb} МиБ` : `${sizeKb} КиБ`;

  return (
    <div className="artifact-viewer">
      <div className="artifact-head">
        <div>
          <span className="eyebrow">{t('artifact.eyebrow')}</span>
          <h2>{artifact.name}</h2>
        </div>
        <div className="toolbar-actions">
          {onDiff && <button className="ghost-button" onClick={() => onDiff(artifact)}>{t('artifact.diff')}</button>}
          {onEdit && fullArtifact && <button className="primary-button" onClick={() => onEdit(fullArtifact)}>{t('artifact.editReplay')}</button>}
        </div>
      </div>
      <div className="metadata-grid">
        <span>{t('common.type')}<strong>{artifact.artifact_type}</strong></span>
        <span>{t('common.size')}<strong>{t('common.bytes', { count: artifact.size_bytes.toLocaleString() })} ({sizeLabel})</strong></span>
        <span>{t('common.hash')}<strong>{artifact.content_hash.slice(0, 14)}</strong></span>
        <span>{t('common.created')}<strong>{formatDateTime(artifact.created_at)}</strong></span>
      </div>

      {fullArtifact ? (
        <JsonBlock value={fullArtifact.content_json} title={t('common.payload')} />
      ) : (
        <div className="panel" style={{ padding: '1.5rem', textAlign: 'center', marginTop: '1rem' }}>
          <p style={{ marginBottom: '1rem', color: 'var(--text-muted)' }}>
            Содержимое артефакта ({sizeLabel}) не загружено автоматически для экономии трафика.
          </p>
          {artifactQuery.isLoading ? (
            <LoadingState label="Загрузка тела артефакта..." />
          ) : artifactQuery.error ? (
            <ErrorState error={artifactQuery.error} />
          ) : (
            <button className="primary-button" onClick={() => setLoadRequested(true)}>
              Открыть содержимое · {sizeLabel}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
