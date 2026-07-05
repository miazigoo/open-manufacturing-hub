import { FormEvent, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { asJson } from '../api/client';
import { mappingsApi } from '../api/mappings';
import { WorkflowPayload, workflowsApi } from '../api/workflows';
import { CodeEditor } from '../components/CodeEditor';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { useT } from '../i18n/useI18n';
import { formatDateTime } from '../utils';

const defaultSteps = [
  { name: 'receive' },
  { name: 'maintenance_guard' },
  { name: 'normalize' },
  { name: 'validate' },
  { name: 'map_payload' },
  { name: 'call_connector' },
  { name: 'handle_response' },
  { name: 'create_incident', on: 'failure' },
  { name: 'send_notifications', on: 'failure' },
];
const defaultValidation = { required_fields: ['id', 'warehouse.id', 'lines'] };
const defaultPayload = { order_id: '1001', warehouse_id: 'MAIN', items: [{ sku: 'ABC123', qty: 5 }] };

export function WorkflowsPage() {
  const t = useT();
  const queryClient = useQueryClient();
  const workflows = useQuery({ queryKey: ['workflows'], queryFn: workflowsApi.list });
  const mappings = useQuery({ queryKey: ['mappings'], queryFn: mappingsApi.list });
  const [form, setForm] = useState({ name: 'Sales orders ERP to WMS', event_type: 'SalesOrderCreated', source_system: 'Mock ERP', target_system: 'Mock WMS', entity_type: 'SalesOrder', source_mapping_version_id: '', target_mapping_version_id: '', steps_json: asJson(defaultSteps), validation_json: asJson(defaultValidation), dry_run_payload: asJson(defaultPayload) });
  const [message, setMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [dryRun, setDryRun] = useState<unknown>(null);

  const versions = useMemo(() => (mappings.data ?? []).flatMap((mapping) => mapping.versions.map((version) => ({ ...version, label: `${mapping.name} v${version.version}` }))), [mappings.data]);
  const create = useMutation({ mutationFn: workflowsApi.create, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['workflows'] }); setMessage(t('workflows.created')); } });
  const enable = useMutation({ mutationFn: workflowsApi.enable, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workflows'] }) });
  const disable = useMutation({ mutationFn: workflowsApi.disable, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workflows'] }) });
  const remove = useMutation({ mutationFn: workflowsApi.delete, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workflows'] }) });
  const dryRunMutation = useMutation({ mutationFn: (payload: { id: string; body: Record<string, unknown>; source: string | null; target: string | null; entity: string | null }) => workflowsApi.test(payload.id, payload.body, payload.source, payload.target, payload.entity), onSuccess: (data) => { setDryRun(data); setMessage(`Dry-run ${data.status}`); } });

  function submit(event: FormEvent) {
    event.preventDefault();
    setFormError(null); setMessage(null);
    try {
      const payload: WorkflowPayload = {
        name: form.name,
        event_type: form.event_type,
        source_system: form.source_system || null,
        target_system: form.target_system || null,
        entity_type: form.entity_type || null,
        steps_json: JSON.parse(form.steps_json) as Array<string | Record<string, unknown>>,
        validation_json: JSON.parse(form.validation_json) as Record<string, unknown>,
        source_mapping_version_id: form.source_mapping_version_id || null,
        target_mapping_version_id: form.target_mapping_version_id || null,
      };
      create.mutate(payload);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Invalid JSON');
    }
  }

  function runDryRun(workflowId: string) {
    try {
      dryRunMutation.mutate({ id: workflowId, body: JSON.parse(form.dry_run_payload) as Record<string, unknown>, source: form.source_system || null, target: form.target_system || null, entity: form.entity_type || null });
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Invalid JSON');
    }
  }

  const error = workflows.error ?? mappings.error;
  if (workflows.isLoading || mappings.isLoading) return <LoadingState label={t('workflows.loading')} />;
  if (error) return <ErrorState error={error} />;

  return (
    <div className="page-stack two-column-page workflow-page">
      <section className="panel form-panel">
        <span className="eyebrow">{t('workflows.eyebrow')}</span>
        <h1>{t('workflows.title')}</h1>
        <form className="stack-form" onSubmit={submit}>
          <label className="field-label">{t('workflows.name')}<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
          <label className="field-label">{t('workflows.eventType')}<input value={form.event_type} onChange={(event) => setForm({ ...form, event_type: event.target.value })} /></label>
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">{t('workflows.sourceSystem')}<input value={form.source_system} onChange={(event) => setForm({ ...form, source_system: event.target.value })} /></label>
            <label className="field-label">{t('workflows.targetSystem')}<input value={form.target_system} onChange={(event) => setForm({ ...form, target_system: event.target.value })} /></label>
            <label className="field-label">{t('workflows.entityType')}<input value={form.entity_type} onChange={(event) => setForm({ ...form, entity_type: event.target.value })} /></label>
          </div>
          <label className="field-label">{t('workflows.sourceMapping')}<select value={form.source_mapping_version_id} onChange={(event) => setForm({ ...form, source_mapping_version_id: event.target.value })}><option value="">{t('common.none')}</option>{versions.map((version) => <option key={version.id} value={version.id}>{version.label}</option>)}</select></label>
          <label className="field-label">{t('workflows.targetMapping')}<select value={form.target_mapping_version_id} onChange={(event) => setForm({ ...form, target_mapping_version_id: event.target.value })}><option value="">{t('common.none')}</option>{versions.map((version) => <option key={version.id} value={version.id}>{version.label}</option>)}</select></label>
          <label className="field-label">{t('workflows.stepsJson')}<CodeEditor value={form.steps_json} onChange={(value) => setForm({ ...form, steps_json: value })} language="json" minRows={10} /></label>
          <label className="field-label">{t('workflows.validationJson')}<CodeEditor value={form.validation_json} onChange={(value) => setForm({ ...form, validation_json: value })} language="json" minRows={6} /></label>
          <label className="field-label">{t('workflows.dryRunPayload')}<CodeEditor value={form.dry_run_payload} onChange={(value) => setForm({ ...form, dry_run_payload: value })} language="json" minRows={7} /></label>
          {formError && <div className="error-state compact">{formError}</div>}
          {message && <div className="success-note">{message}</div>}
          <button className="primary-button" disabled={create.isPending}>{t('workflows.create')}</button>
        </form>
      </section>
      <section className="panel">
        <div className="panel-toolbar"><h2>{t('workflows.routes')}</h2><span className="microcopy">{t('connectors.configured', { count: workflows.data?.length ?? 0 })}</span></div>
        {workflows.data?.length ? workflows.data.map((workflow) => (
          <article className="workflow-card" key={workflow.id}>
            <div className="workflow-card-top">
              <div><h3>{workflow.name}</h3><p>{workflow.source_system ?? '*'} to {workflow.target_system ?? '*'} · {workflow.event_type ?? '*'} · v{workflow.version}</p></div>
              <StatusBadge status={workflow.enabled ? 'ok' : 'unknown'} label={workflow.enabled ? t('connectors.enabled') : t('connectors.disabled')} />
            </div>
            <div className="workflow-steps">{workflow.steps_json.map((step, index) => { const config = typeof step === 'string' ? { name: step } : step; const name = String(config.name ?? 'unknown'); const condition = config.on ? ` · ${String(config.on)}` : ''; return <span key={`${name}-${index}`}>{name}{condition}</span>; })}</div>
            <div className="metadata-grid compact-grid">
              <span>{t('workflows.sourceMapping')}<strong>{workflow.source_mapping_version ? `v${workflow.source_mapping_version.version}` : t('timeline.legacyPipeline')}</strong></span>
              <span>{t('workflows.targetMapping')}<strong>{workflow.target_mapping_version ? `v${workflow.target_mapping_version.version}` : t('timeline.legacyPipeline')}</strong></span>
              <span>{t('common.updated')}<strong>{formatDateTime(workflow.updated_at)}</strong></span>
            </div>
            <div className="action-row">
              <Link className="primary-link" to={`/pipelines/${workflow.id}/edit`}>Edit pipeline</Link>
              <button className="ghost-button" onClick={() => runDryRun(workflow.id)}>{t('workflows.dryRun')}</button>
              <button className="ghost-button" onClick={() => workflow.enabled ? disable.mutate(workflow.id) : enable.mutate(workflow.id)}>{workflow.enabled ? t('connectors.disable') : t('connectors.enable')}</button>
              <button className="ghost-button danger" onClick={() => remove.mutate(workflow.id)}>{t('connectors.delete')}</button>
            </div>
          </article>
        )) : <EmptyState title={t('workflows.noWorkflows')} detail={t('workflows.noWorkflowsDetail')} />}
      </section>
      <section className="panel full-span"><JsonBlock title={t('workflows.lastDryRun')} value={(dryRun as Record<string, unknown> | null) ?? { hint: t('workflows.lastDryRunHint') }} searchable={false} /></section>
    </div>
  );
}
