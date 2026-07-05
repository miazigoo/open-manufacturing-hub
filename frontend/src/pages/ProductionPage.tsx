import { ChangeEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { API_BASE_URL, asJson } from '../api/client';
import { productionApi, type ImportPreview, type UpdateCheck } from '../api/production';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

export function ProductionPage() {
  const queryClient = useQueryClient();
  const snapshot = useQuery({ queryKey: ['production-snapshot'], queryFn: productionApi.snapshot });
  const exportsQuery = useQuery({ queryKey: ['production-exports'], queryFn: productionApi.exports });
  const doctor = useQuery({ queryKey: ['production-doctor'], queryFn: productionApi.doctor });
  const checklist = useQuery({ queryKey: ['production-checklist'], queryFn: productionApi.checklist });
  const [importPayload, setImportPayload] = useState<Record<string, unknown> | null>(null);
  const [importMode, setImportMode] = useState('create_only');
  const [checkResult, setCheckResult] = useState<UpdateCheck | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['production-snapshot'] });
    queryClient.invalidateQueries({ queryKey: ['production-status'] });
    queryClient.invalidateQueries({ queryKey: ['production-exports'] });
    queryClient.invalidateQueries({ queryKey: ['production-doctor'] });
    queryClient.invalidateQueries({ queryKey: ['production-checklist'] });
  };
  const exportConfig = useMutation({ mutationFn: productionApi.exportConfig, onSuccess: refresh });
  const preCheck = useMutation({ mutationFn: productionApi.preUpdateCheck, onSuccess: setCheckResult });
  const postCheck = useMutation({ mutationFn: productionApi.postUpdateCheck, onSuccess: setCheckResult });
  const enableMode = useMutation({ mutationFn: productionApi.enableUpdateMode, onSuccess: refresh });
  const disableMode = useMutation({ mutationFn: productionApi.disableUpdateMode, onSuccess: refresh });
  const previewImport = useMutation({ mutationFn: () => productionApi.previewImport(importPayload ?? {}, importMode), onSuccess: setPreview });
  const applyImport = useMutation({ mutationFn: () => productionApi.applyImport(importPayload ?? {}, importMode), onSuccess: (data) => { setPreview(data); refresh(); } });

  async function loadFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setImportPayload(JSON.parse(await file.text()));
    setPreview(null);
  }

  if (snapshot.isLoading) return <LoadingState label="Loading production snapshot" />;
  if (snapshot.error) return <ErrorState error={snapshot.error} />;
  const data = snapshot.data;
  if (!data) return <ErrorState error={new Error('Snapshot unavailable')} />;

  return (
    <div className="page-stack production-page">
      <section className="page-header production-hero product-page-header">
        <div><span className="eyebrow">Production Safety</span><h1>Check, backup, update, verify.</h1><p>Operational controls for factory deployments: configuration exports, import previews, update mode, pre/post update checks and rollback guidance.</p></div>
        <div className="product-header-actions"><StatusBadge status={data.production_mode ? 'warning' : 'ok'} label={data.app_env} /><StatusBadge status={data.update_mode.enabled ? 'warning' : 'ok'} label={data.update_mode.enabled ? 'update mode' : 'normal'} /></div>
      </section>

      {data.warnings.length > 0 && <section className="panel warning-panel"><div className="panel-toolbar"><h2>Warnings</h2><span>{data.warnings.length}</span></div>{data.warnings.map((item) => <p key={item} className="error-text">{item}</p>)}</section>}

      <section className="metric-grid production-metrics">
        <article className="metric-card"><span>DB revision</span><strong>{data.database_revision ?? 'unknown'}</strong><small>head {data.migration_head}</small></article>
        <article className="metric-card"><span>Connectors</span><strong>{data.counts.connectors ?? 0}</strong><small>{data.counts.endpoints ?? 0} endpoints</small></article>
        <article className="metric-card"><span>Queue</span><strong>{(data.queue.waiting ?? 0) + (data.queue.retry_waiting ?? 0)}</strong><small>{data.queue.processing ?? 0} processing · {data.dlq_count} DLQ</small></article>
        <article className="metric-card"><span>Last backup</span><strong>{data.last_backup_at ? new Date(data.last_backup_at).toLocaleString() : 'none'}</strong><small>{data.packages.length} packages</small></article>
        <article className="metric-card"><span>Current environment</span><strong>{String(data.current_environment?.code ?? 'not set')}</strong><small>{String(data.current_environment?.environment_type ?? 'select before apply')}</small></article>
        <article className="metric-card"><span>Pending change sets</span><strong>{data.pending_change_sets}</strong><small>must be reviewed before update</small></article>
        <article className="metric-card"><span>Last applied</span><strong>{String(data.last_applied_change_set?.name ?? 'none')}</strong><small>{String(data.last_applied_change_set?.applied_at ?? 'no promotion yet')}</small></article>
      </section>

      <section className="production-grid">
        <article className="panel">
          <div className="panel-toolbar"><h2>Release doctor</h2><StatusBadge status={doctor.data?.status === 'ok' ? 'ok' : doctor.data?.status === 'error' ? 'failed' : 'warning'} label={doctor.data?.status ?? 'loading'} /></div>
          <div className="compact-run-list">{doctor.data?.checks.slice(0, 8).map((check) => <div className={`check-row-card ${check.status}`} key={check.name}><strong>{check.name}</strong><span>{check.message ?? check.status}</span></div>)}</div>
          <p className="microcopy">CLI: make doctor · Full gate: make release-check</p>
        </article>
        <article className="panel">
          <div className="panel-toolbar"><h2>First-run checklist</h2><StatusBadge status={checklist.data?.complete ? 'ok' : 'warning'} label={checklist.data?.complete ? 'complete' : 'open'} /></div>
          <div className="compact-run-list">{checklist.data?.items.map((item) => <div className={`check-row-card ${item.status === 'action_required' ? 'error' : item.status === 'ok' ? 'ok' : 'warning'}`} key={item.code}><strong>{item.title}</strong><span>{item.status.replace('_', ' ')}</span></div>)}</div>
        </article>
      </section>

      <section className="production-grid">
        <article className="panel">
          <div className="panel-toolbar"><h2>Backups</h2><button className="primary-button" onClick={() => exportConfig.mutate()} disabled={exportConfig.isPending}>Create config export</button></div>
          <p className="microcopy">Exports mask passwords and tokens. After import, re-enter secret values.</p>
          {exportConfig.data && <a className="primary-link" href={`${API_BASE_URL}${exportConfig.data.download_url}`}>Download {exportConfig.data.file_name}</a>}
          <div className="compact-run-list">{exportsQuery.data?.slice(0, 8).map((item) => <div className="success-note" key={item.id}><strong>{item.backup_type} · {item.status}</strong><span>{new Date(item.created_at).toLocaleString()} · {item.size_bytes ?? 0} bytes</span>{item.status === 'success' && <a className="primary-link" href={`${API_BASE_URL}/api/production/exports/${item.id}/download`}>Download</a>}</div>)}</div>
        </article>

        <article className="panel">
          <div className="panel-toolbar"><h2>Update Safety</h2></div>
          <div className="action-row wrap-actions"><button className="ghost-button" onClick={() => preCheck.mutate()}>Pre-update check</button><button className="ghost-button" onClick={() => postCheck.mutate()}>Post-update check</button>{data.update_mode.enabled ? <button className="primary-button" onClick={() => disableMode.mutate()}>Disable update mode</button> : <button className="primary-button" onClick={() => enableMode.mutate()}>Enable update mode</button>}</div>
          {checkResult && <CheckResult result={checkResult} />}
        </article>
      </section>

      <section className="production-grid">
        <article className="panel">
          <div className="panel-toolbar"><h2>Import config</h2><select value={importMode} onChange={(event) => setImportMode(event.target.value)}><option value="create_only">create_only</option><option value="upsert">upsert</option></select></div>
          <input type="file" accept="application/json" onChange={loadFile} />
          <div className="action-row wrap-actions"><button className="ghost-button" disabled={!importPayload} onClick={() => previewImport.mutate()}>Preview import</button><button className="primary-button" disabled={!importPayload || !preview?.valid} onClick={() => applyImport.mutate()}>Apply import</button></div>
          {preview && <pre className="json-panel">{asJson(preview)}</pre>}
        </article>
        <JsonBlock title="System snapshot" value={data} />
      </section>
    </div>
  );
}

function CheckResult({ result }: { result: UpdateCheck }) {
  return <div className="check-list"><StatusBadge status={result.safe_to_update ? 'ok' : 'warning'} label={result.safe_to_update ? 'safe' : 'actions required'} />{result.checks.map((check) => <div key={check.name} className={`check-row-card ${check.status}`}><strong>{check.name}</strong><span>{check.message ?? check.status}</span></div>)}{result.required_actions.length > 0 && <div className="error-state compact">Required: {result.required_actions.join(', ')}</div>}</div>;
}
