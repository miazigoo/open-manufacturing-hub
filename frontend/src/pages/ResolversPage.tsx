import { FormEvent, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { businessObjectsApi } from '../api/businessObjects';
import { resolversApi, type ResolverDefinitionV2 } from '../api/resolvers';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

function parseObject(value: string, label: string): Record<string, unknown> {
  const parsed = JSON.parse(value || '{}') as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error(`${label} must be a JSON object`);
  return parsed as Record<string, unknown>;
}

export function ResolversPage() {
  const queryClient = useQueryClient();
  const resolvers = useQuery({ queryKey: ['resolvers-v2'], queryFn: () => resolversApi.list() });
  const objects = useQuery({ queryKey: ['business-objects'], queryFn: businessObjectsApi.list });
  const [objectFilter, setObjectFilter] = useState('');
  const install = useMutation({ mutationFn: resolversApi.installPresets, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['resolvers-v2'] }) });
  const rows = useMemo(() => (resolvers.data ?? []).filter((item) => !objectFilter || item.object_type === objectFilter), [objectFilter, resolvers.data]);
  const metrics = useMemo(() => ({ enabled: rows.filter((item) => item.enabled).length, cached: rows.filter((item) => item.cache_enabled).length, strategies: new Set(rows.map((item) => item.strategy)).size }), [rows]);
  if (resolvers.isLoading || objects.isLoading) return <LoadingState label="Loading resolvers" />;
  if (resolvers.error) return <ErrorState error={resolvers.error} />;
  if (objects.error) return <ErrorState error={objects.error} />;
  return (
    <div className="page-stack enterprise-runtime-page">
      <section className="page-header enterprise-hero">
        <span className="eyebrow">Resolver Engine v2</span>
        <h1>Business Object Resolvers</h1>
        <p>Reusable business lookups that hide OData/REST details behind stable names like resolve_customer and resolve_product.</p>
        <div className="hero-meta"><button className="primary-button" onClick={() => install.mutate()} disabled={install.isPending}>Install presets</button><Link className="primary-link" to="/resolvers/cache">Resolver cache</Link><span className="microcopy">{rows.length} resolvers</span></div>
        {install.error instanceof Error && <div className="error-state compact">{install.error.message}</div>}
      </section>
      <section className="metric-grid runtime-metrics"><article className="metric-card info"><span>Enabled</span><strong>{metrics.enabled}</strong></article><article className="metric-card info"><span>Cached</span><strong>{metrics.cached}</strong></article><article className="metric-card warn"><span>Strategies</span><strong>{metrics.strategies}</strong></article></section>
      <div className="filter-bar"><label className="field-label">Business object<select value={objectFilter} onChange={(event) => setObjectFilter(event.target.value)}><option value="">All objects</option>{(objects.data ?? []).map((item) => <option key={item.object_type} value={item.object_type}>{item.display_name}</option>)}</select></label></div>
      {rows.length === 0 ? <EmptyState title="No resolvers" detail="Install presets or create resolver definitions through API." /> : <section className="card-grid runtime-card-grid">{rows.map((item) => <ResolverCard key={item.id} item={item} />)}</section>}
    </div>
  );
}

function ResolverCard({ item }: { item: ResolverDefinitionV2 }) {
  const [input, setInput] = useState(asJson(sampleInput(item.object_type)));
  const [formError, setFormError] = useState<string | null>(null);
  const resolve = useMutation({ mutationFn: () => resolversApi.resolve(item.id, parseObject(input, 'Resolver input')) });
  function run(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    try { resolve.mutate(); } catch (error) { setFormError(error instanceof Error ? error.message : 'Invalid input'); }
  }
  return <article className="panel runtime-card stack-form"><div className="panel-toolbar"><div><span className="eyebrow">{item.strategy}</span><h2>{item.name}</h2></div><StatusBadge status={item.enabled ? 'ok' : 'warning'} label={item.enabled ? 'enabled' : 'disabled'} /></div><p>{item.object_type} · <code>{item.resolver_code}</code></p><div className="action-row wrap-actions"><Link className="primary-link" to={`/resolvers/${item.id}`}>Details</Link><Link className="primary-link" to={`/resolvers/cache?resolver_code=${encodeURIComponent(item.resolver_code)}`}>Cache</Link></div><form className="stack-form" onSubmit={run}><label className="field-label">Test input<textarea value={input} onChange={(event) => setInput(event.target.value)} /></label><button className="primary-button" disabled={resolve.isPending}>Resolve</button></form>{formError && <div className="error-state compact">{formError}</div>}{resolve.error instanceof Error && <div className="error-state compact">{resolve.error.message}</div>}{resolve.data && <JsonBlock title="Resolve result" value={resolve.data} searchable={false} />}</article>;
}

function sampleInput(objectType: string): Record<string, unknown> {
  if (objectType === 'Customer') return { inn: '1234567890' };
  if (objectType === 'Product') return { article: 'ABC-123' };
  if (objectType === 'Warehouse') return { code: 'MAIN' };
  if (objectType === 'PrintJob') return { name: 'Zebra-01', site: 'MAIN' };
  return { number: 'SO-1001' };
}
