import { FormEvent, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { configVersionsApi } from '../api/configVersions';
import { MappingPayload, mappingsApi } from '../api/mappings';
import { CodeEditor } from '../components/CodeEditor';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { VersionHistoryPanel } from '../features/configVersions';
import { useT } from '../i18n/useI18n';
import { formatDateTime } from '../utils';

const defaultRules = [
  { source: 'order_id', target: 'id', transform: 'str' },
  { source: 'warehouse_id', target: 'warehouse.id', transform: 'str' },
  { source: 'items', target: 'lines', type: 'array', items: [{ source: 'sku', target: 'sku' }, { source: 'qty', target: 'quantity' }] },
  { constant: 'SalesOrder', target: 'entity' },
];
const defaultSourceSchema = { order_id: 'string', warehouse_id: 'string', items: [{ sku: 'string', qty: 'number' }] };
const defaultTargetSchema = { id: 'string', warehouse: { id: 'string' }, lines: [{ sku: 'string', quantity: 'number' }] };
const defaultSample = { order_id: '1532', warehouse_id: 'MAIN', items: [{ sku: 'ABC123', qty: 5 }] };

export function MappingEditorPage() {
  const t = useT();
  const queryClient = useQueryClient();
  const mappings = useQuery({ queryKey: ['mappings'], queryFn: mappingsApi.list });
  const presets = useQuery({ queryKey: ['mapping-presets'], queryFn: mappingsApi.presets });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = useMemo(() => (mappings.data ?? []).find((mapping) => mapping.id === selectedId) ?? mappings.data?.[0], [mappings.data, selectedId]);
  const latestVersion = selected?.versions.at(-1);
  const [form, setForm] = useState({
    name: 'ERP SalesOrder to Canonical',
    source_entity: 'SalesOrder',
    target_entity: 'SalesOrder',
    rules_json: asJson(defaultRules),
    source_schema_json: asJson(defaultSourceSchema),
    target_schema_json: asJson(defaultTargetSchema),
    sample_payload: asJson(defaultSample),
  });
  const [message, setMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);
  const [diff, setDiff] = useState<unknown>(null);

  const create = useMutation({ mutationFn: mappingsApi.create, onSuccess: (mapping) => { queryClient.invalidateQueries({ queryKey: ['mappings'] }); setSelectedId(mapping.id); setMessage(t('mappings.created')); } });
  const createVersion = useMutation({ mutationFn: (payload: { id: string; rules: Array<Record<string, unknown>>; sourceSchema: Record<string, unknown>; targetSchema: Record<string, unknown> }) => mappingsApi.createVersion(payload.id, { rules_json: payload.rules, source_schema_json: payload.sourceSchema, target_schema_json: payload.targetSchema, notes: 'Created from editor' }), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['mappings'] }); setMessage(t('mappings.versionCreated')); } });
  const saveDraft = useMutation({
    mutationFn: (payload: { id: string; rules: Array<Record<string, unknown>>; sourceSchema: Record<string, unknown>; targetSchema: Record<string, unknown> }) => configVersionsApi.createDraft('mapping', payload.id, {
      config_json: {
        name: selected!.name,
        description: selected!.description,
        source_entity: selected!.source_entity,
        target_entity: selected!.target_entity,
        version_payload: {
          rules_json: payload.rules,
          source_schema_json: payload.sourceSchema,
          target_schema_json: payload.targetSchema,
          notes: 'Published through config versioning',
        },
      },
      comment: 'Draft saved from mapping editor',
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config-versions', 'mapping', selected?.id] });
      setMessage('Draft saved. Publish it from release control.');
    },
  });
  const clone = useMutation({ mutationFn: (payload: { id: string; version: number }) => mappingsApi.cloneVersion(payload.id, payload.version), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['mappings'] }); setMessage(t('mappings.cloned')); } });
  const validate = useMutation({ mutationFn: (payload: { rules: Array<Record<string, unknown>>; sample: Record<string, unknown> }) => mappingsApi.validate(payload.rules, payload.sample), onSuccess: (data) => { setPreview(data.preview); setMessage(data.valid ? t('mappings.valid') : t('mappings.invalid', { errors: data.errors.join(', ') })); } });
  const execute = useMutation({ mutationFn: (payload: { id: string; version: number; sample: Record<string, unknown> }) => mappingsApi.execute(payload.id, payload.version, payload.sample), onSuccess: (data) => setPreview(data.output) });
  const compare = useMutation({ mutationFn: (payload: { id: string; left: number; right: number }) => mappingsApi.compare(payload.id, payload.left, payload.right), onSuccess: setDiff });
  const remove = useMutation({ mutationFn: mappingsApi.delete, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['mappings'] }); setSelectedId(null); } });
  const installPresets = useMutation({ mutationFn: mappingsApi.installPresets, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['mappings'] }); setMessage(t('mappings.installed')); } });

  function parsed() {
    return {
      rules: JSON.parse(form.rules_json) as Array<Record<string, unknown>>,
      sourceSchema: JSON.parse(form.source_schema_json) as Record<string, unknown>,
      targetSchema: JSON.parse(form.target_schema_json) as Record<string, unknown>,
      sample: JSON.parse(form.sample_payload) as Record<string, unknown>,
    };
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    setFormError(null); setMessage(null); setPreview(null);
    try {
      const data = parsed();
      const payload: MappingPayload = { name: form.name, source_entity: form.source_entity, target_entity: form.target_entity, initial_version: { rules_json: data.rules, source_schema_json: data.sourceSchema, target_schema_json: data.targetSchema } };
      create.mutate(payload);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Invalid JSON');
    }
  }

  function validateCurrent() {
    try { const data = parsed(); validate.mutate({ rules: data.rules, sample: data.sample }); } catch (error) { setFormError(error instanceof Error ? error.message : 'Invalid JSON'); }
  }

  function versionCurrent() {
    if (!selected) return;
    try { const data = parsed(); createVersion.mutate({ id: selected.id, rules: data.rules, sourceSchema: data.sourceSchema, targetSchema: data.targetSchema }); } catch (error) { setFormError(error instanceof Error ? error.message : 'Invalid JSON'); }
  }

  function draftCurrent() {
    if (!selected) return;
    try { const data = parsed(); saveDraft.mutate({ id: selected.id, rules: data.rules, sourceSchema: data.sourceSchema, targetSchema: data.targetSchema }); } catch (error) { setFormError(error instanceof Error ? error.message : 'Invalid JSON'); }
  }

  const error = mappings.error ?? presets.error;
  if (mappings.isLoading || presets.isLoading) return <LoadingState label={t('mappings.loading')} />;
  if (error) return <ErrorState error={error} />;

  return (
    <div className="page-stack mapping-page">
      <section className="page-header mapping-hero">
        <span className="eyebrow">{t('mappings.eyebrow')}</span>
        <h1>{t('mappings.title')}</h1>
        <p>{t('mappings.subtitle')}</p>
        <div className="hero-meta"><button className="primary-button" onClick={() => installPresets.mutate()} disabled={installPresets.isPending}>{t('mappings.installPresets')}</button><span>{t('mappings.presetsAvailable', { count: presets.data?.length ?? 0 })}</span></div>
      </section>
      <section className="mapping-editor-grid">
        <aside className="panel mapping-list-panel">
          <div className="panel-toolbar"><h2>{t('nav.mappings')}</h2><span className="microcopy">{t('mappings.definitions', { count: mappings.data?.length ?? 0 })}</span></div>
          {mappings.data?.length ? mappings.data.map((mapping) => (
            <button key={mapping.id} className={`mapping-list-item ${selected?.id === mapping.id ? 'active' : ''}`} onClick={() => setSelectedId(mapping.id)}>
              <strong>{mapping.name}</strong><span>{mapping.source_entity ?? t('common.source')} → {mapping.target_entity ?? t('common.target')} · v{mapping.versions.at(-1)?.version ?? 0}</span>
            </button>
          )) : <EmptyState title={t('mappings.noMappings')} detail={t('mappings.noMappingsDetail')} />}
        </aside>
        <form className="panel mapping-editor-panel" onSubmit={submit}>
          <div className="panel-toolbar"><h2>{t('mappings.editor')}</h2><div className="action-row"><button type="button" className="ghost-button" onClick={validateCurrent}>{t('mappings.validate')}</button><button type="button" className="ghost-button" disabled={!selected || saveDraft.isPending} onClick={draftCurrent}>Save Draft</button><button type="button" className="ghost-button" disabled={!selected} onClick={versionCurrent}>{t('mappings.createVersion')}</button><button className="primary-button">{t('mappings.createMapping')}</button></div></div>
          <div className="mapping-triptych">
            <label className="field-label">{t('mappings.sourceSchema')}<CodeEditor value={form.source_schema_json} onChange={(value) => setForm({ ...form, source_schema_json: value })} language="json" minRows={10} /></label>
            <label className="field-label">{t('mappings.rulesJson')}<CodeEditor value={form.rules_json} onChange={(value) => setForm({ ...form, rules_json: value })} language="json" minRows={10} /></label>
            <label className="field-label">{t('mappings.targetSchema')}<CodeEditor value={form.target_schema_json} onChange={(value) => setForm({ ...form, target_schema_json: value })} language="json" minRows={10} /></label>
          </div>
          <div className="metadata-grid compact-grid">
            <label className="field-label">{t('connectors.name')}<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
            <label className="field-label">{t('mappings.sourceEntity')}<input value={form.source_entity} onChange={(event) => setForm({ ...form, source_entity: event.target.value })} /></label>
            <label className="field-label">{t('mappings.targetEntity')}<input value={form.target_entity} onChange={(event) => setForm({ ...form, target_entity: event.target.value })} /></label>
          </div>
          <label className="field-label">{t('mappings.samplePayload')}<CodeEditor value={form.sample_payload} onChange={(value) => setForm({ ...form, sample_payload: value })} language="json" minRows={8} /></label>
          {formError && <div className="error-state compact">{formError}</div>}
          {message && <div className="success-note">{message}</div>}
        </form>
      </section>
      <section className="mapping-bottom-grid">
        <div className="panel">
          <div className="panel-toolbar"><h2>{t('mappings.selected')}</h2>{selected && <button className="ghost-button danger" onClick={() => remove.mutate(selected.id)}>{t('connectors.delete')}</button>}</div>
          {selected ? <div className="version-strip">{selected.versions.map((version) => <button key={version.id} className="version-chip" onClick={() => setForm({ ...form, rules_json: asJson(version.rules_json), source_schema_json: asJson(version.source_schema_json), target_schema_json: asJson(version.target_schema_json) })}>{selected.name} v{version.version}<span>{formatDateTime(version.created_at)}</span></button>)}</div> : <EmptyState title={t('mappings.noSelected')} detail={t('mappings.noSelectedDetail')} />}
          {selected && latestVersion && <div className="action-row"><button className="ghost-button" onClick={() => clone.mutate({ id: selected.id, version: latestVersion.version })}>{t('mappings.cloneLatest')}</button>{selected.versions.length > 1 && <button className="ghost-button" onClick={() => compare.mutate({ id: selected.id, left: selected.versions[0].version, right: latestVersion.version })}>{t('mappings.compare')}</button>}<button className="ghost-button" onClick={() => { try { execute.mutate({ id: selected.id, version: latestVersion.version, sample: parsed().sample }); } catch (error) { setFormError(error instanceof Error ? error.message : 'Invalid JSON'); } }}>{t('mappings.executeLatest')}</button></div>}
        </div>
        <div className="panel"><JsonBlock title={t('mappings.preview')} value={preview ?? { hint: t('mappings.previewHint') }} searchable={false} /></div>
        <div className="panel"><JsonBlock title={t('mappings.versionDiff')} value={(diff as Record<string, unknown> | null) ?? { hint: t('mappings.diffHint') }} searchable={false} /></div>
      </section>
      {selected && <VersionHistoryPanel objectType="mapping" objectId={selected.id} compact onChanged={() => queryClient.invalidateQueries({ queryKey: ['mappings'] })} />}
    </div>
  );
}
