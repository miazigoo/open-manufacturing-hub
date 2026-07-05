import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { changeSetsApi } from '../../api/changeSets';
import { ConfigObjectType, ConfigVersion, configVersionQueryKey, configVersionsApi } from '../../api/configVersions';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { formatDateTime } from '../../utils';
import { ConfigDiffViewer } from './ConfigDiffViewer';
import { ConfigVersionBadge } from './ConfigVersionBadge';
import { DraftBanner } from './DraftBanner';
import { DraftTestPanel } from './DraftTestPanel';
import { PublishButton } from './PublishButton';
import { RollbackButton } from './RollbackButton';

interface Props {
  objectType: ConfigObjectType | string;
  objectId: string;
  compact?: boolean;
  onChanged?: () => void;
}

export function VersionHistoryPanel({ objectType, objectId, compact = false, onChanged }: Props) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const versions = useQuery({ queryKey: configVersionQueryKey(objectType, objectId), queryFn: () => configVersionsApi.versions(objectType, objectId), enabled: Boolean(objectId) });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [fromId, setFromId] = useState<string | null>(null);
  const [toId, setToId] = useState<string | null>(null);
  const selected = useMemo(() => (versions.data?.versions ?? []).find((item) => item.id === selectedId) ?? versions.data?.draft_version ?? versions.data?.active_version ?? null, [selectedId, versions.data]);
  const from = fromId ?? versions.data?.active_version?.id ?? null;
  const to = toId ?? versions.data?.draft_version?.id ?? selected?.id ?? null;
  const diff = useQuery({ queryKey: ['config-version-diff', objectType, objectId, from, to], queryFn: () => configVersionsApi.diff(objectType, objectId, from!, to!), enabled: Boolean(from && to && from !== to) });
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: configVersionQueryKey(objectType, objectId) });
    onChanged?.();
  };
  const publish = useMutation({ mutationFn: (payload: { id: string; comment: string }) => configVersionsApi.publish(objectType, objectId, payload.id, payload.comment), onSuccess: refresh });
  const rollback = useMutation({ mutationFn: (payload: { id: string; comment: string }) => configVersionsApi.rollback(objectType, objectId, payload.id, payload.comment), onSuccess: refresh });
  const discard = useMutation({ mutationFn: () => configVersionsApi.discardDraft(objectType, objectId), onSuccess: refresh });
  const createChangeSet = useMutation({
    mutationFn: () => changeSetsApi.createFromDrafts({ name: `Promote ${objectType} ${selected?.object_name ?? objectId}`, description: 'Created from release control', object_refs: [{ object_type: String(objectType), object_id: objectId }], include_dependencies: true }),
    onSuccess: (changeSet) => navigate(`/change-sets/${changeSet.id}`),
  });

  if (versions.isLoading) return <LoadingState label="Loading config versions" />;
  if (versions.error) return <ErrorState error={versions.error} />;
  const data = versions.data;
  if (!data) return <ErrorState error={new Error('Config versions not found')} />;
  const ordered = [...data.versions].sort((left, right) => right.version_number - left.version_number);

  if (compact) {
    return (
      <section className="panel config-version-panel compact-panel">
        <div className="panel-toolbar"><div><span className="eyebrow">Release control</span><h2>Configuration versions</h2></div><div className="toolbar-actions"><button className="ghost-button" onClick={() => createChangeSet.mutate()} disabled={createChangeSet.isPending}>Create Change Set</button><Link className="primary-link" to={`/config-history/${objectType}/${objectId}`}>Open full history</Link></div></div>
        <DraftBanner objectType={objectType} objectId={objectId} draft={data.draft_version} />
        <div className="config-version-strip">{ordered.slice(0, 5).map((version) => <ConfigVersionBadge key={version.id} version={version} compact />)}</div>
        {createChangeSet.error instanceof Error && <div className="error-state compact">{createChangeSet.error.message}</div>}
      </section>
    );
  }

  return (
    <section className="config-history-grid">
      <aside className="panel config-version-panel">
        <div className="panel-toolbar"><div><span className="eyebrow">Release control</span><h2>Version timeline</h2></div>{data.active_version && <ConfigVersionBadge version={data.active_version} />}</div>
        <DraftBanner objectType={objectType} objectId={objectId} draft={data.draft_version} />
        <div className="config-version-list">
          {ordered.map((version) => (
            <button key={version.id} className={`config-version-card ${selected?.id === version.id ? 'active' : ''}`} onClick={() => { setSelectedId(version.id); setToId(version.id); }}>
              <ConfigVersionBadge version={version} />
              <span>{version.comment || 'No comment'}</span>
              <small>{formatDateTime(version.published_at ?? version.updated_at)}</small>
            </button>
          ))}
        </div>
      </aside>
      <section className="panel config-release-panel">
        <div className="panel-toolbar"><div><span className="eyebrow">Draft - Test - Publish</span><h2>{selected ? `Version v${selected.version_number}` : 'No version selected'}</h2></div>{selected && <ConfigVersionBadge version={selected} />}</div>
        <DraftTestPanel objectType={objectType} objectId={objectId} draft={data.draft_version} />
        <div className="config-release-actions">
          <button className="primary-button" onClick={() => createChangeSet.mutate()} disabled={createChangeSet.isPending}>Create Change Set from Draft</button>
          <PublishButton draft={data.draft_version} pending={publish.isPending} onPublish={(comment) => data.draft_version && publish.mutate({ id: data.draft_version.id, comment })} />
          {data.draft_version && <button className="ghost-button danger" disabled={discard.isPending} onClick={() => discard.mutate()}>Discard draft</button>}
          {selected && <RollbackButton version={selected} pending={rollback.isPending} onRollback={(comment) => rollback.mutate({ id: selected.id, comment })} />}
        </div>
        {(publish.error ?? rollback.error ?? discard.error ?? createChangeSet.error) instanceof Error && <div className="error-state compact">{((publish.error ?? rollback.error ?? discard.error ?? createChangeSet.error) as Error).message}</div>}
      </section>
      <section className="panel config-diff-panel">
        <div className="panel-toolbar"><div><span className="eyebrow">Redacted diff</span><h2>Compare versions</h2></div></div>
        <div className="metadata-grid compact-grid no-margin">
          <label className="field-label">From<select value={from ?? ''} onChange={(event) => setFromId(event.target.value)}>{ordered.map((version) => <option key={version.id} value={version.id}>v{version.version_number} {version.status}</option>)}</select></label>
          <label className="field-label">To<select value={to ?? ''} onChange={(event) => setToId(event.target.value)}>{ordered.map((version) => <option key={version.id} value={version.id}>v{version.version_number} {version.status}</option>)}</select></label>
        </div>
        {diff.error instanceof Error && <div className="error-state compact">{diff.error.message}</div>}
        <ConfigDiffViewer diff={from && to && from !== to ? diff.data : null} />
      </section>
    </section>
  );
}
