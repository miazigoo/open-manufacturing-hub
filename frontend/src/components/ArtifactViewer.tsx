import { Artifact } from '../api/client';
import { JsonBlock } from './JsonBlock';
import { formatDateTime } from '../utils';

interface ArtifactViewerProps {
  artifact: Artifact | null;
  onDiff?: (artifact: Artifact) => void;
  onEdit?: (artifact: Artifact) => void;
}

export function ArtifactViewer({ artifact, onDiff, onEdit }: ArtifactViewerProps) {
  if (!artifact) {
    return <div className="artifact-placeholder">Select an artifact to inspect payload, hash and replay options.</div>;
  }

  return (
    <div className="artifact-viewer">
      <div className="artifact-head">
        <div>
          <span className="eyebrow">Artifact</span>
          <h2>{artifact.name}</h2>
        </div>
        <div className="toolbar-actions">
          {onDiff && <button className="ghost-button" onClick={() => onDiff(artifact)}>Diff</button>}
          {onEdit && <button className="primary-button" onClick={() => onEdit(artifact)}>Edit & Replay</button>}
        </div>
      </div>
      <div className="metadata-grid">
        <span>Type<strong>{artifact.artifact_type}</strong></span>
        <span>Size<strong>{artifact.size_bytes.toLocaleString()} bytes</strong></span>
        <span>Hash<strong>{artifact.content_hash.slice(0, 14)}</strong></span>
        <span>Created<strong>{formatDateTime(artifact.created_at)}</strong></span>
      </div>
      <JsonBlock value={artifact.content_json} title="Payload" />
    </div>
  );
}
