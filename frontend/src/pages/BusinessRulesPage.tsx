import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { businessRulesApi } from '../api/businessRules';
import { CodeEditor } from '../components/CodeEditor';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

const defaultRules = { mode: 'first_match', rules: [{ name: 'DNP pool', if: { path: 'request.body.pool_type', operator: 'eq', value: 'DNP' }, then: [{ action: 'set_target_system', value: 'DNP Service' }] }] };

function parseObject(value: string, label: string): Record<string, unknown> {
  const parsed = JSON.parse(value || '{}') as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error(`${label} must be a JSON object`);
  return parsed as Record<string, unknown>;
}

export function BusinessRulesPage() {
  const queryClient = useQueryClient();
  const rules = useQuery({ queryKey: ['business-rule-sets'], queryFn: businessRulesApi.list });
  const [form, setForm] = useState({ name: 'Pool routing rules', description: 'Route by pool type', rules_json: asJson(defaultRules) });
  const [formError, setFormError] = useState<string | null>(null);
  const create = useMutation({ mutationFn: () => businessRulesApi.create({ name: form.name, description: form.description, scope: 'global', enabled: true, rules_json: parseObject(form.rules_json, 'Rules JSON') }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['business-rule-sets'] }) });
  const install = useMutation({ mutationFn: businessRulesApi.installPresets, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['business-rule-sets'] }) });
  if (rules.isLoading) return <LoadingState label="Loading business rules" />;
  if (rules.error) return <ErrorState error={rules.error} />;
  function submit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    try { create.mutate(); } catch (caught) { setFormError(caught instanceof Error ? caught.message : 'Invalid JSON'); }
  }
  const rows = rules.data ?? [];
  return <div className="page-stack enterprise-runtime-page"><section className="page-header enterprise-hero"><span className="eyebrow">Business Rules Engine</span><h1>Rule Sets</h1><p>Safe configurable IF/THEN logic for routing, variables, payload updates, stop/fail/retry decisions.</p><div className="hero-meta"><button className="primary-button" onClick={() => install.mutate()} disabled={install.isPending}>Install presets</button><span className="microcopy">{rows.length} rule sets</span></div></section><section className="runtime-grid"><form className="panel stack-form runtime-control-card" onSubmit={submit}><span className="eyebrow">Create rule set</span><h2>Advanced JSON editor</h2><label className="field-label">Name<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label><label className="field-label">Description<input value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label><label className="field-label">Rules JSON<CodeEditor value={form.rules_json} onChange={(value) => setForm({ ...form, rules_json: value })} language="json" minRows={10} /></label><button className="primary-button" disabled={create.isPending}>Save rule set</button>{formError && <div className="error-state compact">{formError}</div>}{create.error instanceof Error && <div className="error-state compact">{create.error.message}</div>}</form>{rows.length === 0 ? <EmptyState title="No business rules" detail="Install presets or create a rule set." /> : <section className="card-grid runtime-card-grid">{rows.map((item) => <article className="panel runtime-card" key={item.id}><div className="panel-toolbar"><span className="eyebrow">{item.scope}</span><StatusBadge status={item.enabled ? 'ok' : 'warning'} label={item.enabled ? 'enabled' : 'disabled'} /></div><h2>{item.name}</h2><p>{item.description}</p><Link className="primary-link" to={`/business-rules/${item.id}`}>Open editor</Link><JsonBlock title="Rules" value={item.rules_json} searchable={false} /></article>)}</section>}</section></div>;
}
