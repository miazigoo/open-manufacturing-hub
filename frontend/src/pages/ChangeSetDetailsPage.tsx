import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { changeSetsApi } from '../api/changeSets';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { formatDateTime } from '../utils';

export function ChangeSetDetailsPage() {
  const { id = '' } = useParams();
  const queryClient = useQueryClient();
  const changeSet = useQuery({ queryKey: ['change-set', id], queryFn: () => changeSetsApi.get(id), enabled: Boolean(id) });
  const [exportPayload, setExportPayload] = useState<Record<string, unknown> | null>(null);
  const exportedText = useMemo(() => exportPayload ? asJson(exportPayload) : '', [exportPayload]);
  const exportChangeSet = useMutation({ mutationFn: () => changeSetsApi.export(id), onSuccess: (data) => { setExportPayload(data as unknown as Record<string, unknown>); queryClient.invalidateQueries({ queryKey: ['change-set', id] }); } });
  const smoke = useMutation({ mutationFn: () => changeSetsApi.runSmokeTests(id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['change-set', id] }) });

  if (changeSet.isLoading) return <LoadingState label="Loading change set" />;
  if (changeSet.error) return <ErrorState error={changeSet.error} />;
  const item = changeSet.data;
  if (!item) return <ErrorState error={new Error('Change set not found')} />;

  async function copyExport() {
    if (exportedText) await navigator.clipboard?.writeText(exportedText);
  }

  return (
    <div className="page-stack promotion-page">
      <section className="page-header promotion-hero change-set-hero">
        <div>
          <span className="eyebrow">Change Set</span>
          <h1>{item.name}</h1>
          <p>{item.description ?? 'Audited promotion package with config versions, dependencies and import safety metadata.'}</p>
        </div>
        <div className="product-header-actions"><StatusBadge status={item.status === 'applied' ? 'ok' : item.status === 'failed' ? 'failed' : 'warning'} label={item.status} /><Link className="ghost-button" to="/change-sets/import">Import another</Link></div>
      </section>

      <section className="metric-grid production-metrics">
        <article className="metric-card"><span>Source</span><strong>{item.source_environment ?? 'local'}</strong><small>created {formatDateTime(item.created_at)}</small></article>
        <article className="metric-card"><span>Target</span><strong>{item.target_environment ?? 'not applied'}</strong><small>{item.applied_at ? formatDateTime(item.applied_at) : 'pending'}</small></article>
        <article className="metric-card"><span>Items</span><strong>{item.items.length}</strong><small>versions and dependencies</small></article>
        <article className="metric-card"><span>Exported</span><strong>{item.exported_at ? 'yes' : 'no'}</strong><small>{item.exported_at ? formatDateTime(item.exported_at) : 'reference-only export'}</small></article>
      </section>

      <section className="promotion-grid">
        <section className="panel">
          <div className="panel-toolbar"><div><span className="eyebrow">Release Package</span><h2>Export for production</h2></div></div>
          <p className="microcopy">Export never includes raw secret values. Target installation must map secrets and environment variables during import preview/apply.</p>
          <div className="action-row wrap-actions">
            <button className="primary-button" onClick={() => exportChangeSet.mutate()} disabled={exportChangeSet.isPending}>Export JSON</button>
            <button className="ghost-button" onClick={copyExport} disabled={!exportPayload}>Copy export</button>
            <button className="ghost-button" onClick={() => smoke.mutate()} disabled={smoke.isPending}>Run smoke tests</button>
          </div>
          {(exportChangeSet.error ?? smoke.error) instanceof Error && <div className="error-state compact">{((exportChangeSet.error ?? smoke.error) as Error).message}</div>}
          {smoke.data && <JsonBlock title="Smoke result" value={smoke.data} searchable={false} />}
        </section>

        <section className="panel">
          <div className="panel-toolbar"><h2>Items</h2><span className="microcopy">{item.items.length}</span></div>
          <div className="compact-run-list">
            {item.items.map((row) => (
              <div className="success-note" key={row.id}>
                <strong>{row.object_type} · {row.object_name ?? row.object_id}</strong>
                <span>{row.operation} · version {row.version_id ?? 'not linked'} · package {row.package_id ?? 'core'}</span>
              </div>
            ))}
          </div>
        </section>
      </section>

      {exportPayload && <JsonBlock title="Export payload" value={exportPayload} />}
      <JsonBlock title="Change set metadata" value={item} />
    </div>
  );
}
