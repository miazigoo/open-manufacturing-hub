import { FormEvent, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { MappingPayload, mappingsApi } from '../api/mappings';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
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

  const create = useMutation({ mutationFn: mappingsApi.create, onSuccess: (mapping) => { queryClient.invalidateQueries({ queryKey: ['mappings'] }); setSelectedId(mapping.id); setMessage('Mapping created'); } });
  const createVersion = useMutation({ mutationFn: (payload: { id: string; rules: Array<Record<string, unknown>>; sourceSchema: Record<string, unknown>; targetSchema: Record<string, unknown> }) => mappingsApi.createVersion(payload.id, { rules_json: payload.rules, source_schema_json: payload.sourceSchema, target_schema_json: payload.targetSchema, notes: 'Created from editor' }), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['mappings'] }); setMessage('New immutable version created'); } });
  const clone = useMutation({ mutationFn: (payload: { id: string; version: number }) => mappingsApi.cloneVersion(payload.id, payload.version), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['mappings'] }); setMessage('Version cloned'); } });
  const validate = useMutation({ mutationFn: (payload: { rules: Array<Record<string, unknown>>; sample: Record<string, unknown> }) => mappingsApi.validate(payload.rules, payload.sample), onSuccess: (data) => { setPreview(data.preview); setMessage(data.valid ? 'Mapping valid' : `Invalid: ${data.errors.join(', ')}`); } });
  const execute = useMutation({ mutationFn: (payload: { id: string; version: number; sample: Record<string, unknown> }) => mappingsApi.execute(payload.id, payload.version, payload.sample), onSuccess: (data) => setPreview(data.output) });
  const compare = useMutation({ mutationFn: (payload: { id: string; left: number; right: number }) => mappingsApi.compare(payload.id, payload.left, payload.right), onSuccess: setDiff });
  const remove = useMutation({ mutationFn: mappingsApi.delete, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['mappings'] }); setSelectedId(null); } });
  const installPresets = useMutation({ mutationFn: mappingsApi.installPresets, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['mappings'] }); setMessage('Mapping presets installed'); } });

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

  const error = mappings.error ?? presets.error;
  if (mappings.isLoading || presets.isLoading) return <LoadingState label="Loading mappings" />;
  if (error) return <ErrorState error={error} />;

  return (
    <div className="page-stack mapping-page">
      <section className="page-header mapping-hero">
        <span className="eyebrow">Mapping Engine</span>
        <h1>Versioned transformations without connector lock-in.</h1>
        <p>Define ERP to canonical and canonical to target mappings. Versions are immutable, so every run can be traced back to the exact rules used.</p>
        <div className="hero-meta"><button className="primary-button" onClick={() => installPresets.mutate()} disabled={installPresets.isPending}>Install presets</button><span>{presets.data?.length ?? 0} packaged mappings available</span></div>
      </section>
      <section className="mapping-editor-grid">
        <aside className="panel mapping-list-panel">
          <div className="panel-toolbar"><h2>Mappings</h2><span className="microcopy">{mappings.data?.length ?? 0} definitions</span></div>
          {mappings.data?.length ? mappings.data.map((mapping) => (
            <button key={mapping.id} className={`mapping-list-item ${selected?.id === mapping.id ? 'active' : ''}`} onClick={() => setSelectedId(mapping.id)}>
              <strong>{mapping.name}</strong><span>{mapping.source_entity ?? 'source'} to {mapping.target_entity ?? 'target'} · v{mapping.versions.at(-1)?.version ?? 0}</span>
            </button>
          )) : <EmptyState title="No mappings" detail="Create the first ERP to canonical mapping." />}
        </aside>
        <form className="panel mapping-editor-panel" onSubmit={submit}>
          <div className="panel-toolbar"><h2>Mapping Editor</h2><div className="action-row"><button type="button" className="ghost-button" onClick={validateCurrent}>Validate</button><button type="button" className="ghost-button" disabled={!selected} onClick={versionCurrent}>Create version</button><button className="primary-button">Create mapping</button></div></div>
          <div className="mapping-triptych">
            <label className="field-label">Source schema<textarea value={form.source_schema_json} onChange={(event) => setForm({ ...form, source_schema_json: event.target.value })} spellCheck={false} /></label>
            <label className="field-label">Rules JSON<textarea value={form.rules_json} onChange={(event) => setForm({ ...form, rules_json: event.target.value })} spellCheck={false} /></label>
            <label className="field-label">Target schema<textarea value={form.target_schema_json} onChange={(event) => setForm({ ...form, target_schema_json: event.target.value })} spellCheck={false} /></label>
          </div>
          <div className="metadata-grid compact-grid">
            <label className="field-label">Name<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
            <label className="field-label">Source entity<input value={form.source_entity} onChange={(event) => setForm({ ...form, source_entity: event.target.value })} /></label>
            <label className="field-label">Target entity<input value={form.target_entity} onChange={(event) => setForm({ ...form, target_entity: event.target.value })} /></label>
          </div>
          <label className="field-label">Sample payload<textarea value={form.sample_payload} onChange={(event) => setForm({ ...form, sample_payload: event.target.value })} spellCheck={false} /></label>
          {formError && <div className="error-state compact">{formError}</div>}
          {message && <div className="success-note">{message}</div>}
        </form>
      </section>
      <section className="mapping-bottom-grid">
        <div className="panel">
          <div className="panel-toolbar"><h2>Selected mapping</h2>{selected && <button className="ghost-button danger" onClick={() => remove.mutate(selected.id)}>Delete</button>}</div>
          {selected ? <div className="version-strip">{selected.versions.map((version) => <button key={version.id} className="version-chip" onClick={() => setForm({ ...form, rules_json: asJson(version.rules_json), source_schema_json: asJson(version.source_schema_json), target_schema_json: asJson(version.target_schema_json) })}>{selected.name} v{version.version}<span>{formatDateTime(version.created_at)}</span></button>)}</div> : <EmptyState title="No mapping selected" detail="Pick a mapping to inspect versions." />}
          {selected && latestVersion && <div className="action-row"><button className="ghost-button" onClick={() => clone.mutate({ id: selected.id, version: latestVersion.version })}>Clone latest</button>{selected.versions.length > 1 && <button className="ghost-button" onClick={() => compare.mutate({ id: selected.id, left: selected.versions[0].version, right: latestVersion.version })}>Compare first/latest</button>}<button className="ghost-button" onClick={() => { try { execute.mutate({ id: selected.id, version: latestVersion.version, sample: parsed().sample }); } catch (error) { setFormError(error instanceof Error ? error.message : 'Invalid JSON'); } }}>Execute latest</button></div>}
        </div>
        <div className="panel"><JsonBlock title="Preview" value={preview ?? { hint: 'Validate or execute a mapping to see output.' }} searchable={false} /></div>
        <div className="panel"><JsonBlock title="Version diff" value={(diff as Record<string, unknown> | null) ?? { hint: 'Compare first and latest versions.' }} searchable={false} /></div>
      </section>
    </div>
  );
}
