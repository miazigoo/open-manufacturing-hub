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
import { useT } from '../i18n/I18nProvider';
import { formatDateTime, formatDuration } from '../utils';

const defaultQuery = { '$select': 'Ref_Key,Number,Date,Партнер_Key,Склад_Key,Комментарий,Товары', '$orderby': 'Date asc' };

export function PollingJobsPage() {
  const t = useT();
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
  const create = useMutation({ mutationFn: pollingApi.create, onSuccess: (job) => { refresh(); setSelectedId(job.id); setMessage(t('polling.created')); } });
  const remove = useMutation({ mutationFn: pollingApi.delete, onSuccess: () => { refresh(); setSelectedId(null); } });
  const enable = useMutation({ mutationFn: pollingApi.enable, onSuccess: refresh });
  const disable = useMutation({ mutationFn: pollingApi.disable, onSuccess: refresh });
  const runOnce = useMutation({ mutationFn: pollingApi.runOnce, onSuccess: (run) => { refresh(); setMessage(t('polling.runFinished', { created: run.events_created, skipped: run.items_skipped })); } });

  function submit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    setMessage(null);
    try {
      const sourceId = form.source_connector_id || onecConnectors[0]?.id;
      if (!sourceId) throw new Error(t('polling.createFirst'));
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
  if (jobs.isLoading || connectors.isLoading) return <LoadingState label={t('polling.loading')} />;
  if (error) return <ErrorState error={error} />;

  return (
    <div className="page-stack polling-page">
      <section className="page-header polling-hero">
        <span className="eyebrow">{t('polling.eyebrow')}</span>
        <h1>{t('polling.title')}</h1>
        <p>{t('polling.subtitle')}</p>
      </section>

      <section className="two-column-page page-stack">
        <form className="panel stack-form" onSubmit={submit}>
          <div className="panel-toolbar"><h2>{t('polling.createJob')}</h2><span className="microcopy">{t('polling.runOnceFirst')}</span></div>
          <label className="field-label">{t('connectors.name')}<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
          <label className="field-label">{t('polling.onecConnector')}<select value={form.source_connector_id} onChange={(event) => setForm({ ...form, source_connector_id: event.target.value })}><option value="">{t('polling.autoSelect')}</option>{onecConnectors.map((connector) => <option key={connector.id} value={connector.id}>{connector.name}</option>)}</select></label>
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">{t('polling.resource')}<input value={form.resource} onChange={(event) => setForm({ ...form, resource: event.target.value })} /></label>
            <label className="field-label">{t('common.target')}<input value={form.target_system} onChange={(event) => setForm({ ...form, target_system: event.target.value })} /></label>
            <label className="field-label">{t('polling.interval')}<input type="number" value={form.interval_seconds} onChange={(event) => setForm({ ...form, interval_seconds: Number(event.target.value) })} /></label>
          </div>
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">{t('polling.event')}<input value={form.event_type} onChange={(event) => setForm({ ...form, event_type: event.target.value })} /></label>
            <label className="field-label">{t('polling.entity')}<input value={form.entity_type} onChange={(event) => setForm({ ...form, entity_type: event.target.value })} /></label>
            <label className="field-label">{t('polling.cursor')}<select value={form.cursor_type} onChange={(event) => setForm({ ...form, cursor_type: event.target.value as PollingCursorType })}><option value="none">none</option><option value="updated_at">updated_at</option><option value="skip">skip</option><option value="custom">custom</option></select></label>
          </div>
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">{t('polling.entityIdField')}<input value={form.entity_id_field} onChange={(event) => setForm({ ...form, entity_id_field: event.target.value })} /></label>
            <label className="field-label">{t('polling.correlationField')}<input value={form.correlation_id_field} onChange={(event) => setForm({ ...form, correlation_id_field: event.target.value })} /></label>
            <label className="field-label">{t('polling.updatedField')}<input value={form.updated_at_field} onChange={(event) => setForm({ ...form, updated_at_field: event.target.value })} /></label>
          </div>
          <label className="field-label">{t('polling.odataQuery')}<textarea value={form.query_json} onChange={(event) => setForm({ ...form, query_json: event.target.value })} spellCheck={false} /></label>
          {formError && <div className="error-state compact">{formError}</div>}
          {create.error instanceof Error && <div className="error-state compact">{create.error.message}</div>}
          {message && <div className="success-note">{message}</div>}
          <button className="primary-button" disabled={create.isPending}>{t('polling.createJob')}</button>
        </form>

        <section className="panel">
          <div className="panel-toolbar"><h2>{t('polling.jobs')}</h2><span className="microcopy">{t('connectors.configured', { count: jobs.data?.length ?? 0 })}</span></div>
          {jobs.data?.length ? jobs.data.map((job) => (
            <article className={`polling-card ${selected?.id === job.id ? 'active' : ''}`} key={job.id} onClick={() => setSelectedId(job.id)}>
              <div className="connector-card-top">
                <div><h3>{job.name}</h3><p>{job.resource} → {job.target_system ?? t('common.unassigned')} · {t('polling.everySeconds', { count: job.interval_seconds })}</p></div>
                <StatusBadge status={job.status} />
              </div>
              <div className="metadata-grid compact-grid">
                <span>{t('polling.lastRun')}<strong>{formatDateTime(job.last_run_at)}</strong></span>
                <span>{t('polling.nextRun')}<strong>{formatDateTime(job.next_run_at)}</strong></span>
                <span>{t('polling.cursor')}<strong>{job.cursor_value ?? t('common.empty')}</strong></span>
              </div>
              {job.last_error && <div className="error-state compact">{job.last_error}</div>}
              <div className="action-row" onClick={(event) => event.stopPropagation()}>
                <button className="ghost-button" onClick={() => runOnce.mutate(job.id)} disabled={runOnce.isPending}>{t('polling.runOnce')}</button>
                <button className="ghost-button" onClick={() => job.enabled ? disable.mutate(job.id) : enable.mutate(job.id)}>{job.enabled ? t('connectors.disable') : t('connectors.enable')}</button>
                <button className="ghost-button danger" onClick={() => remove.mutate(job.id)}>{t('connectors.delete')}</button>
              </div>
            </article>
          )) : <EmptyState title={t('polling.noJobs')} detail={t('polling.noJobsDetail')} />}
        </section>
      </section>

      <section className="mapping-bottom-grid">
        <div className="panel"><JsonBlock title={t('polling.selectedQuery')} value={selected?.query_json ?? { hint: t('polling.selectJob') }} searchable={false} /></div>
        <div className="panel">
          <div className="panel-toolbar"><h2>{t('polling.recentRuns')}</h2><span className="microcopy">{t('polling.records', { count: runs.data?.length ?? 0 })}</span></div>
          {runs.data?.length ? <div className="run-list compact-run-list">{runs.data.slice(0, 8).map((run) => <div className="run-card" key={run.id}><div className="run-header"><strong>{formatDateTime(run.started_at)}</strong><StatusBadge status={run.status} compact /></div><span className="muted">{t('polling.runSummary', { created: run.events_created, skipped: run.items_skipped, duration: formatDuration(run.started_at, run.finished_at) })}</span>{run.error_message && <small className="error-text">{run.error_message}</small>}</div>)}</div> : <EmptyState title={t('polling.noRuns')} detail={t('polling.noRunsDetail')} />}
        </div>
        <div className="panel"><JsonBlock title={t('polling.latestDetails')} value={runs.data?.[0]?.details_json ?? { hint: t('polling.detailsHint') }} searchable={false} /></div>
      </section>
    </div>
  );
}
