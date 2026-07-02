import { FormEvent, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { connectorsApi } from '../api/connectors';
import { PollingCursorType, PollingJobPayload, pollingApi } from '../api/polling';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { formatDateTime, formatDuration } from '../utils';

const defaultQuery = { '$select': 'Ref_Key,Number,Date,Партнер_Key,Склад_Key,Комментарий,Товары', '$orderby': 'Date asc' };

export function PollingJobsPage() {
  const queryClient = useQueryClient();
  const jobs = useQuery({ queryKey: ['polling-jobs'], queryFn: pollingApi.list });
  const connectors = useQuery({ queryKey: ['connectors'], queryFn: connectorsApi.list });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = useMemo(() => (jobs.data ?? []).find((job) => job.id === selectedId) ?? jobs.data?.[0], [jobs.data, selectedId]);
  const runs = useQuery({ queryKey: ['polling-job-runs', selected?.id], queryFn: () => pollingApi.runs(selected!.id), enabled: Boolean(selected?.id) });
  const onecConnectors = (connectors.data ?? []).filter((connector) => connector.connector_type === 'onec');
  const [form, setForm] = useState({
    name: 'Poll 1C sales orders',
    source_connector_id: '',
    target_system: 'Mock WMS',
    resource: 'Document_ЗаказКлиента',
    query_json: asJson(defaultQuery),
    event_type: 'SalesOrderCreated',
    entity_type: 'SalesOrder',
    entity_id_field: 'Ref_Key',
    correlation_id_field: 'Number',
    updated_at_field: 'Date',
    cursor_type: 'updated_at' as PollingCursorType,
    interval_seconds: 300,
  });
  const [message, setMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['polling-jobs'] });
    queryClient.invalidateQueries({ queryKey: ['polling-job-runs'] });
    queryClient.invalidateQueries({ queryKey: ['events'] });
  };
  const create = useMutation({ mutationFn: pollingApi.create, onSuccess: (job) => { refresh(); setSelectedId(job.id); setMessage('Polling job created'); } });
  const remove = useMutation({ mutationFn: pollingApi.delete, onSuccess: () => { refresh(); setSelectedId(null); } });
  const enable = useMutation({ mutationFn: pollingApi.enable, onSuccess: refresh });
  const disable = useMutation({ mutationFn: pollingApi.disable, onSuccess: refresh });
  const runOnce = useMutation({ mutationFn: pollingApi.runOnce, onSuccess: (run) => { refresh(); setMessage(`Run finished: ${run.events_created} created, ${run.items_skipped} skipped`); } });

  function submit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    setMessage(null);
    try {
      const sourceId = form.source_connector_id || onecConnectors[0]?.id;
      if (!sourceId) throw new Error('Create or install a 1C connector first');
      const payload: PollingJobPayload = {
        ...form,
        source_connector_id: sourceId,
        query_json: JSON.parse(form.query_json) as Record<string, unknown>,
      };
      create.mutate(payload);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Invalid JSON');
    }
  }

  const error = jobs.error ?? connectors.error;
  if (jobs.isLoading || connectors.isLoading) return <LoadingState label="Loading polling jobs" />;
  if (error) return <ErrorState error={error} />;

  return (
    <div className="page-stack polling-page">
      <section className="page-header polling-hero">
        <span className="eyebrow">1C OData Polling</span>
        <h1>Controlled intake for systems that cannot push events.</h1>
        <p>Run jobs manually for verification, track idempotency, and inspect every OData request before scheduling it in production.</p>
      </section>

      <section className="two-column-page page-stack">
        <form className="panel stack-form" onSubmit={submit}>
          <div className="panel-toolbar"><h2>Create polling job</h2><span className="microcopy">run-once first</span></div>
          <label className="field-label">Name<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
          <label className="field-label">1C connector<select value={form.source_connector_id} onChange={(event) => setForm({ ...form, source_connector_id: event.target.value })}><option value="">Auto-select 1C connector</option>{onecConnectors.map((connector) => <option key={connector.id} value={connector.id}>{connector.name}</option>)}</select></label>
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">Resource<input value={form.resource} onChange={(event) => setForm({ ...form, resource: event.target.value })} /></label>
            <label className="field-label">Target<input value={form.target_system} onChange={(event) => setForm({ ...form, target_system: event.target.value })} /></label>
            <label className="field-label">Interval, sec<input type="number" value={form.interval_seconds} onChange={(event) => setForm({ ...form, interval_seconds: Number(event.target.value) })} /></label>
          </div>
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">Event<input value={form.event_type} onChange={(event) => setForm({ ...form, event_type: event.target.value })} /></label>
            <label className="field-label">Entity<input value={form.entity_type} onChange={(event) => setForm({ ...form, entity_type: event.target.value })} /></label>
            <label className="field-label">Cursor<select value={form.cursor_type} onChange={(event) => setForm({ ...form, cursor_type: event.target.value as PollingCursorType })}><option value="none">none</option><option value="updated_at">updated_at</option><option value="skip">skip</option><option value="custom">custom</option></select></label>
          </div>
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">Entity ID field<input value={form.entity_id_field} onChange={(event) => setForm({ ...form, entity_id_field: event.target.value })} /></label>
            <label className="field-label">Correlation field<input value={form.correlation_id_field} onChange={(event) => setForm({ ...form, correlation_id_field: event.target.value })} /></label>
            <label className="field-label">Updated field<input value={form.updated_at_field} onChange={(event) => setForm({ ...form, updated_at_field: event.target.value })} /></label>
          </div>
          <label className="field-label">OData query<textarea value={form.query_json} onChange={(event) => setForm({ ...form, query_json: event.target.value })} spellCheck={false} /></label>
          {formError && <div className="error-state compact">{formError}</div>}
          {create.error instanceof Error && <div className="error-state compact">{create.error.message}</div>}
          {message && <div className="success-note">{message}</div>}
          <button className="primary-button" disabled={create.isPending}>Create job</button>
        </form>

        <section className="panel">
          <div className="panel-toolbar"><h2>Polling jobs</h2><span className="microcopy">{jobs.data?.length ?? 0} configured</span></div>
          {jobs.data?.length ? jobs.data.map((job) => (
            <article className={`polling-card ${selected?.id === job.id ? 'active' : ''}`} key={job.id} onClick={() => setSelectedId(job.id)}>
              <div className="connector-card-top">
                <div><h3>{job.name}</h3><p>{job.resource} to {job.target_system ?? 'unassigned'} · every {job.interval_seconds}s</p></div>
                <StatusBadge status={job.status} />
              </div>
              <div className="metadata-grid compact-grid">
                <span>Last run<strong>{formatDateTime(job.last_run_at)}</strong></span>
                <span>Next run<strong>{formatDateTime(job.next_run_at)}</strong></span>
                <span>Cursor<strong>{job.cursor_value ?? 'empty'}</strong></span>
              </div>
              {job.last_error && <div className="error-state compact">{job.last_error}</div>}
              <div className="action-row" onClick={(event) => event.stopPropagation()}>
                <button className="ghost-button" onClick={() => runOnce.mutate(job.id)} disabled={runOnce.isPending}>Run once</button>
                <button className="ghost-button" onClick={() => job.enabled ? disable.mutate(job.id) : enable.mutate(job.id)}>{job.enabled ? 'Disable' : 'Enable'}</button>
                <button className="ghost-button danger" onClick={() => remove.mutate(job.id)}>Delete</button>
              </div>
            </article>
          )) : <EmptyState title="No polling jobs" detail="Install the 1C demo scenario or create a job manually." />}
        </section>
      </section>

      <section className="mapping-bottom-grid">
        <div className="panel"><JsonBlock title="Selected job query" value={selected?.query_json ?? { hint: 'Select a polling job.' }} searchable={false} /></div>
        <div className="panel">
          <div className="panel-toolbar"><h2>Recent runs</h2><span className="microcopy">{runs.data?.length ?? 0} records</span></div>
          {runs.data?.length ? <div className="run-list compact-run-list">{runs.data.slice(0, 8).map((run) => <div className="run-card" key={run.id}><div className="run-header"><strong>{formatDateTime(run.started_at)}</strong><StatusBadge status={run.status} compact /></div><span className="muted">{run.events_created} created · {run.items_skipped} skipped · {formatDuration(run.started_at, run.finished_at)}</span>{run.error_message && <small className="error-text">{run.error_message}</small>}</div>)}</div> : <EmptyState title="No runs yet" detail="Run the selected job once to create a job-run log." />}
        </div>
        <div className="panel"><JsonBlock title="Latest run details" value={runs.data?.[0]?.details_json ?? { hint: 'Run details will appear here.' }} searchable={false} /></div>
      </section>
    </div>
  );
}
