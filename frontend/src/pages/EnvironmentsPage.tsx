import { FormEvent, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { environmentsApi, EnvironmentProfile, EnvironmentType } from '../api/environments';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

const environmentTypes: EnvironmentType[] = ['development', 'test', 'staging', 'production', 'custom'];

function parseValue(value: string): unknown {
  if (!value.trim()) return null;
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

export function EnvironmentsPage() {
  const queryClient = useQueryClient();
  const environments = useQuery({ queryKey: ['environments'], queryFn: environmentsApi.list });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = useMemo(() => (environments.data ?? []).find((item) => item.id === selectedId) ?? environments.data?.[0] ?? null, [environments.data, selectedId]);
  const [form, setForm] = useState({ name: 'Production', code: 'prod', environment_type: 'production' as EnvironmentType, base_url: 'https://factory.example.local', description: 'Live factory profile', is_current: false });
  const [variable, setVariable] = useState({ key: 'ONEC_BASE_URL', value: '"https://onec.example.local/odata/standard.odata"', secret_ref: '', description: 'Resolved during promotion apply' });
  const [error, setError] = useState<string | null>(null);

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['environments'] });
  const create = useMutation({ mutationFn: environmentsApi.create, onSuccess: (data) => { setSelectedId(data.id); refresh(); } });
  const setCurrent = useMutation({ mutationFn: environmentsApi.setCurrent, onSuccess: refresh });
  const remove = useMutation({ mutationFn: environmentsApi.remove, onSuccess: () => { setSelectedId(null); refresh(); } });
  const upsertVariable = useMutation({ mutationFn: (payload: { environmentId: string; key: string; value_json?: unknown; secret_ref?: string | null; description?: string | null }) => environmentsApi.upsertVariable(payload.environmentId, payload), onSuccess: refresh });
  const deleteVariable = useMutation({ mutationFn: (payload: { environmentId: string; key: string }) => environmentsApi.deleteVariable(payload.environmentId, payload.key), onSuccess: refresh });

  if (environments.isLoading) return <LoadingState label="Loading environments" />;
  if (environments.error) return <ErrorState error={environments.error} />;

  function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    create.mutate({ ...form, variables: [] });
  }

  function saveVariable(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setError(null);
    try {
      upsertVariable.mutate({ environmentId: selected.id, key: variable.key, value_json: variable.secret_ref ? null : parseValue(variable.value), secret_ref: variable.secret_ref || null, description: variable.description });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid variable value');
    }
  }

  const mutationError = [create, setCurrent, remove, upsertVariable, deleteVariable].find((item) => item.error)?.error;

  return (
    <div className="page-stack promotion-page">
      <section className="page-header promotion-hero">
        <div>
          <span className="eyebrow">Environment Profiles</span>
          <h1>Separate dev, test and production safely.</h1>
          <p>Profiles hold target-specific variables and secret references. Change sets resolve these values only when applying into the current environment.</p>
        </div>
        <div className="product-header-actions"><StatusBadge status={selected?.environment_type ?? 'unknown'} label={selected ? `${selected.code} current=${selected.is_current ? 'yes' : 'no'}` : 'not configured'} /></div>
      </section>

      <section className="promotion-grid">
        <aside className="panel promotion-list-panel">
          <div className="panel-toolbar"><h2>Profiles</h2><span className="microcopy">{environments.data?.length ?? 0}</span></div>
          {(environments.data ?? []).length === 0 ? <EmptyState title="No environments" detail="Create at least dev and production profiles before promoting configuration." /> : (
            <div className="promotion-list">
              {(environments.data ?? []).map((item) => <EnvironmentCard key={item.id} item={item} active={selected?.id === item.id} onClick={() => setSelectedId(item.id)} />)}
            </div>
          )}
        </aside>

        <section className="panel stack-form">
          <div className="panel-toolbar"><div><span className="eyebrow">Create Profile</span><h2>Environment identity</h2></div></div>
          <form className="stack-form" onSubmit={submit}>
            <div className="metadata-grid compact-grid no-margin">
              <label className="field-label">Name<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
              <label className="field-label">Code<input value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value })} /></label>
              <label className="field-label">Type<select value={form.environment_type} onChange={(event) => setForm({ ...form, environment_type: event.target.value as EnvironmentType })}>{environmentTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select></label>
            </div>
            <label className="field-label">Base URL<input value={form.base_url} onChange={(event) => setForm({ ...form, base_url: event.target.value })} /></label>
            <label className="field-label">Description<textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
            <label className="inline-check"><input type="checkbox" checked={form.is_current} onChange={(event) => setForm({ ...form, is_current: event.target.checked })} /> Set as current environment</label>
            <button className="primary-button" disabled={create.isPending}>Create profile</button>
          </form>
          {(error || mutationError instanceof Error) && <div className="error-state compact">{error || (mutationError as Error).message}</div>}
        </section>
      </section>

      {selected && (
        <section className="promotion-grid">
          <section className="panel">
            <div className="panel-toolbar"><div><span className="eyebrow">Current Selection</span><h2>{selected.name}</h2></div><StatusBadge status={selected.is_current ? 'ok' : 'disabled'} label={selected.is_current ? 'current' : selected.environment_type} /></div>
            <div className="metadata-grid compact-grid">
              <span>Code<strong>{selected.code}</strong></span>
              <span>Type<strong>{selected.environment_type}</strong></span>
              <span>Base URL<strong>{selected.base_url ?? 'not set'}</strong></span>
            </div>
            <div className="action-row wrap-actions">
              {!selected.is_current && <button className="primary-button" onClick={() => setCurrent.mutate(selected.id)} disabled={setCurrent.isPending}>Set current</button>}
              <button className="ghost-button danger" onClick={() => remove.mutate(selected.id)} disabled={selected.is_current || remove.isPending}>Delete profile</button>
            </div>
            <p className="microcopy">Current profile controls import/apply resolution. Production profiles should be selected only when you are ready to promote.</p>
          </section>

          <section className="panel stack-form">
            <div className="panel-toolbar"><div><span className="eyebrow">Variables</span><h2>Target-specific values</h2></div></div>
            <form className="stack-form" onSubmit={saveVariable}>
              <div className="metadata-grid compact-grid no-margin">
                <label className="field-label">Key<input value={variable.key} onChange={(event) => setVariable({ ...variable, key: event.target.value })} /></label>
                <label className="field-label">Secret ref<input value={variable.secret_ref} onChange={(event) => setVariable({ ...variable, secret_ref: event.target.value })} placeholder="optional secret name" /></label>
              </div>
              <label className="field-label">Value JSON or plain text<textarea value={variable.value} onChange={(event) => setVariable({ ...variable, value: event.target.value })} disabled={Boolean(variable.secret_ref)} /></label>
              <label className="field-label">Description<input value={variable.description} onChange={(event) => setVariable({ ...variable, description: event.target.value })} /></label>
              <button className="primary-button" disabled={upsertVariable.isPending}>Save variable</button>
            </form>
            <div className="compact-run-list">
              {selected.variables.map((item) => (
                <div className="success-note promotion-variable-row" key={item.id}>
                  <strong>{item.key}</strong>
                  <span>{item.secret_ref ? `secret:${item.secret_ref}` : asJson(item.value_json)}</span>
                  <button className="ghost-button danger" onClick={() => deleteVariable.mutate({ environmentId: selected.id, key: item.key })}>Delete</button>
                </div>
              ))}
            </div>
          </section>
        </section>
      )}

      {selected && <JsonBlock title="Selected profile JSON" value={selected} />}
    </div>
  );
}

function EnvironmentCard({ item, active, onClick }: { item: EnvironmentProfile; active: boolean; onClick: () => void }) {
  return (
    <button className={`promotion-card ${active ? 'active' : ''}`} onClick={onClick}>
      <span><strong>{item.name}</strong><small>{item.code} · {item.environment_type}</small></span>
      <StatusBadge status={item.is_current ? 'ok' : 'disabled'} label={item.is_current ? 'current' : `${item.variables.length} vars`} compact />
    </button>
  );
}
