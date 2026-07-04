import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { enterpriseRuntimeApi } from '../api/enterpriseRuntime';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

type RuntimeView = 'queue' | 'dlq' | 'monitor' | 'objects' | 'resolvers' | 'transforms' | 'rules';

const titles: Record<RuntimeView, { eyebrow: string; title: string; subtitle: string }> = {
  queue: { eyebrow: 'Enterprise Runtime', title: 'Integration Queue', subtitle: 'Prioritized operational queue with retry, worker and timeline visibility.' },
  dlq: { eyebrow: 'Enterprise Runtime', title: 'Dead Letter Queue', subtitle: 'Recover failed transactions without losing artifacts or timeline evidence.' },
  monitor: { eyebrow: 'Enterprise Runtime', title: 'Transaction Monitor', subtitle: 'Live queue posture across waiting, processing, retry, DLQ and completed work.' },
  objects: { eyebrow: 'Enterprise Runtime', title: 'Canonical Business Objects', subtitle: 'Shared object vocabulary for mappings, rules and resolver targets.' },
  resolvers: { eyebrow: 'Enterprise Runtime', title: 'Resolver Engine', subtitle: 'Resolve customers, products, warehouses, orders and printers through cache/OData/REST.' },
  transforms: { eyebrow: 'Enterprise Runtime', title: 'Transformation Library', subtitle: 'Reusable transforms for mappings and operational data shaping.' },
  rules: { eyebrow: 'Enterprise Runtime', title: 'Business Rules Engine', subtitle: 'Configurable IF/SWITCH/SET/STOP/FAIL rules for runtime decisions.' },
};

export function EnterpriseRuntimePage({ view }: { view: RuntimeView }) {
  const queryClient = useQueryClient();
  const [result, setResult] = useState<unknown>(null);
  const install = useMutation({ mutationFn: enterpriseRuntimeApi.installPresets, onSuccess: (data) => { setResult(data); refreshAll(); } });
  function refreshAll() {
    ['runtime-queue', 'runtime-dlq', 'runtime-monitor', 'runtime-objects', 'runtime-resolvers', 'runtime-transforms', 'runtime-rules', 'runtime-cache'].forEach((key) => queryClient.invalidateQueries({ queryKey: [key] }));
  }
  const meta = titles[view];
  return (
    <div className="page-stack enterprise-runtime-page">
      <section className="page-header enterprise-hero">
        <span className="eyebrow">{meta.eyebrow}</span>
        <h1>{meta.title}</h1>
        <p>{meta.subtitle}</p>
        <div className="hero-meta"><button className="primary-button" onClick={() => install.mutate()} disabled={install.isPending}>Install enterprise presets</button><span className="microcopy">Queue · DLQ · Resolvers · Rules · Cache</span></div>
        {install.error instanceof Error && <div className="error-state compact">{install.error.message}</div>}
      </section>
      {view === 'queue' && <QueuePanel onResult={setResult} />}
      {view === 'dlq' && <DlqPanel onResult={setResult} />}
      {view === 'monitor' && <MonitorPanel />}
      {view === 'objects' && <ObjectsPanel onResult={setResult} />}
      {view === 'resolvers' && <ResolversPanel onResult={setResult} />}
      {view === 'transforms' && <TransformsPanel onResult={setResult} />}
      {view === 'rules' && <RulesPanel onResult={setResult} />}
      {result !== null && <JsonBlock title="Runtime result" value={(result as Record<string, unknown>) ?? {}} searchable={false} />}
    </div>
  );
}

function QueuePanel({ onResult }: { onResult: (value: unknown) => void }) {
  const queryClient = useQueryClient();
  const queue = useQuery({ queryKey: ['runtime-queue'], queryFn: enterpriseRuntimeApi.queue });
  const [form, setForm] = useState({ business_object: 'SalesOrder', operation: 'ship', priority: '50', payload_json: asJson({ order_id: 'SO-1001', warehouse_id: 'MAIN' }) });
  const [error, setError] = useState<string | null>(null);
  const create = useMutation({ mutationFn: enterpriseRuntimeApi.createQueue, onSuccess: (data) => { onResult(data); queryClient.invalidateQueries({ queryKey: ['runtime-queue'] }); } });
  const processing = useMutation({ mutationFn: enterpriseRuntimeApi.markProcessing, onSuccess: (data) => { onResult(data); queryClient.invalidateQueries({ queryKey: ['runtime-queue'] }); } });
  const dlq = useMutation({ mutationFn: (id: string) => enterpriseRuntimeApi.moveToDlq(id, 'Manual operator escalation'), onSuccess: (data) => { onResult(data); queryClient.invalidateQueries({ queryKey: ['runtime-queue'] }); queryClient.invalidateQueries({ queryKey: ['runtime-dlq'] }); } });
  if (queue.isLoading) return <LoadingState label="Loading queue" />;
  if (queue.error) return <ErrorState error={queue.error} />;
  function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try { create.mutate({ business_object: form.business_object, operation: form.operation, priority: Number(form.priority) || 100, payload_json: JSON.parse(form.payload_json) }); }
    catch { setError('Payload JSON is invalid.'); }
  }
  return <section className="runtime-grid"><form className="panel stack-form" onSubmit={submit}><h2>Create queue message</h2><label className="field-label">Business object<input value={form.business_object} onChange={(event) => setForm({ ...form, business_object: event.target.value })} /></label><label className="field-label">Operation<input value={form.operation} onChange={(event) => setForm({ ...form, operation: event.target.value })} /></label><label className="field-label">Priority<input value={form.priority} onChange={(event) => setForm({ ...form, priority: event.target.value })} /></label><label className="field-label">Payload JSON<textarea value={form.payload_json} onChange={(event) => setForm({ ...form, payload_json: event.target.value })} /></label>{error && <div className="error-state compact">{error}</div>}{create.error instanceof Error && <div className="error-state compact">{create.error.message}</div>}<button className="primary-button" disabled={create.isPending}>Create message</button></form><section className="table-panel"><table><thead><tr><th>Object</th><th>Status</th><th>Attempts</th><th>Timeline</th><th>Actions</th></tr></thead><tbody>{(queue.data ?? []).map((item) => <tr key={item.id}><td><strong>{item.business_object}</strong><small>{item.operation} · p{item.priority}</small></td><td><StatusBadge status={item.status === 'completed' ? 'ok' : item.status === 'dlq' || item.status === 'failed' ? 'error' : 'processing'} label={item.status} /></td><td>{item.attempts}/{item.max_attempts}</td><td>{item.timeline_link ? <Link className="primary-link" to={item.timeline_link}>Timeline</Link> : '—'}</td><td><div className="action-row"><button className="ghost-button" onClick={() => processing.mutate(item.id)}>Processing</button><button className="ghost-button danger" onClick={() => dlq.mutate(item.id)}>Move DLQ</button></div></td></tr>)}</tbody></table></section></section>;
}

function DlqPanel({ onResult }: { onResult: (value: unknown) => void }) {
  const queryClient = useQueryClient();
  const dlq = useQuery({ queryKey: ['runtime-dlq'], queryFn: enterpriseRuntimeApi.dlq });
  const retry = useMutation({ mutationFn: enterpriseRuntimeApi.retryDlq, onSuccess: (data) => { onResult(data); queryClient.invalidateQueries({ queryKey: ['runtime-dlq'] }); queryClient.invalidateQueries({ queryKey: ['runtime-queue'] }); } });
  const archive = useMutation({ mutationFn: enterpriseRuntimeApi.archiveDlq, onSuccess: (data) => { onResult(data); queryClient.invalidateQueries({ queryKey: ['runtime-dlq'] }); } });
  if (dlq.isLoading) return <LoadingState label="Loading DLQ" />;
  if (dlq.error) return <ErrorState error={dlq.error} />;
  return <section className="table-panel"><table><thead><tr><th>Object</th><th>Reason</th><th>Timeline</th><th>Actions</th></tr></thead><tbody>{(dlq.data ?? []).map((item) => <tr key={item.id}><td><strong>{item.business_object}</strong><small>{item.operation}</small></td><td>{item.reason}</td><td>{item.timeline_link ? <Link className="primary-link" to={item.timeline_link}>Timeline</Link> : '—'}</td><td><div className="action-row"><button className="ghost-button" onClick={() => retry.mutate(item.id)}>Retry / Restore</button><button className="ghost-button danger" onClick={() => archive.mutate(item.id)}>Archive</button></div></td></tr>)}</tbody></table></section>;
}

function MonitorPanel() {
  const monitor = useQuery({ queryKey: ['runtime-monitor'], queryFn: enterpriseRuntimeApi.monitor, refetchInterval: 10000 });
  if (monitor.isLoading) return <LoadingState label="Loading transaction monitor" />;
  if (monitor.error) return <ErrorState error={monitor.error} />;
  const entries = Object.entries(monitor.data ?? {});
  return <section className="metric-grid runtime-metrics">{entries.map(([key, value]) => <article className={`metric-card ${key === 'dlq' || key === 'failed' ? 'bad' : key === 'retry_waiting' ? 'warn' : 'info'}`} key={key}><span>{key}</span><strong>{value}</strong></article>)}</section>;
}

function ObjectsPanel({ onResult }: { onResult: (value: unknown) => void }) {
  const objects = useQuery({ queryKey: ['runtime-objects'], queryFn: enterpriseRuntimeApi.canonicalObjects });
  if (objects.isLoading) return <LoadingState label="Loading business objects" />;
  if (objects.error) return <ErrorState error={objects.error} />;
  return <section className="card-grid">{(objects.data ?? []).map((item) => <article className="panel" key={item.id}><span className="eyebrow">Canonical</span><h2>{item.name}</h2><p>{item.description}</p><JsonBlock title="Schema" value={item.schema_json} searchable={false} /></article>)}</section>;
}

function ResolversPanel({ onResult }: { onResult: (value: unknown) => void }) {
  const resolvers = useQuery({ queryKey: ['runtime-resolvers'], queryFn: enterpriseRuntimeApi.resolvers });
  const [payload, setPayload] = useState('{"warehouse_id":"MAIN"}');
  const resolve = useMutation({ mutationFn: (id: string) => enterpriseRuntimeApi.resolve(id, JSON.parse(payload)), onSuccess: onResult });
  if (resolvers.isLoading) return <LoadingState label="Loading resolvers" />;
  if (resolvers.error) return <ErrorState error={resolvers.error} />;
  return <section className="runtime-grid"><section className="panel stack-form"><h2>Resolve input</h2><textarea value={payload} onChange={(event) => setPayload(event.target.value)} />{resolve.error instanceof Error && <div className="error-state compact">{resolve.error.message}</div>}</section><section className="card-grid">{(resolvers.data ?? []).map((item) => <article className="panel" key={item.id}><span className="eyebrow">{item.resolver_type}</span><h2>{item.name}</h2><p>{item.business_object}</p><button className="primary-button" onClick={() => resolve.mutate(item.id)}>Resolve</button><JsonBlock title="Config" value={item.config_json} searchable={false} /></article>)}</section></section>;
}

function TransformsPanel({ onResult }: { onResult: (value: unknown) => void }) {
  const transforms = useQuery({ queryKey: ['runtime-transforms'], queryFn: enterpriseRuntimeApi.transforms });
  const [value, setValue] = useState('  hello OMH  ');
  const apply = useMutation({ mutationFn: (name: string) => enterpriseRuntimeApi.applyTransform({ name, value, params: { old: 'OMH', new: 'Enterprise Runtime', separator: ' ' } }), onSuccess: onResult });
  if (transforms.isLoading) return <LoadingState label="Loading transforms" />;
  if (transforms.error) return <ErrorState error={transforms.error} />;
  return <section className="page-stack"><section className="panel"><label className="field-label">Input<input value={value} onChange={(event) => setValue(event.target.value)} /></label></section><section className="card-grid">{(transforms.data ?? []).map((item) => <article className="panel" key={item.name}><h2>{item.name}</h2><p>{item.description}</p><button className="ghost-button" onClick={() => apply.mutate(item.name)}>Apply</button></article>)}</section></section>;
}

function RulesPanel({ onResult }: { onResult: (value: unknown) => void }) {
  const rules = useQuery({ queryKey: ['runtime-rules'], queryFn: enterpriseRuntimeApi.businessRules });
  const [payload, setPayload] = useState('{"status":"cancelled","order_id":"SO-1001"}');
  const run = useMutation({ mutationFn: (id: string) => enterpriseRuntimeApi.runBusinessRule(id, JSON.parse(payload)), onSuccess: onResult });
  if (rules.isLoading) return <LoadingState label="Loading business rules" />;
  if (rules.error) return <ErrorState error={rules.error} />;
  return <section className="runtime-grid"><section className="panel stack-form"><h2>Rule payload</h2><textarea value={payload} onChange={(event) => setPayload(event.target.value)} />{run.error instanceof Error && <div className="error-state compact">{run.error.message}</div>}</section><section className="card-grid">{(rules.data ?? []).map((item) => <article className="panel" key={item.id}><span className="eyebrow">{item.status}</span><h2>{item.name}</h2><p>{item.business_object ?? 'Any object'} · {item.operation ?? 'Any operation'}</p><button className="primary-button" onClick={() => run.mutate(item.id)}>Run rule</button><JsonBlock title="Rules" value={item.rules_json} searchable={false} /></article>)}</section></section>;
}

export const IntegrationQueuePage = () => <EnterpriseRuntimePage view="queue" />;
export const DeadLetterQueuePage = () => <EnterpriseRuntimePage view="dlq" />;
export const TransactionMonitorPage = () => <EnterpriseRuntimePage view="monitor" />;
export const BusinessObjectsPage = () => <EnterpriseRuntimePage view="objects" />;
export const ResolversPage = () => <EnterpriseRuntimePage view="resolvers" />;
export const TransformationLibraryPage = () => <EnterpriseRuntimePage view="transforms" />;
export const BusinessRulesPage = () => <EnterpriseRuntimePage view="rules" />;
