import { useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { resolversApi } from '../api/resolvers';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';

export function ResolverCachePage() {
  const [params, setParams] = useSearchParams();
  const queryClient = useQueryClient();
  const resolverCode = params.get('resolver_code') ?? '';
  const objectType = params.get('object_type') ?? '';
  const cache = useQuery({ queryKey: ['resolver-cache', resolverCode, objectType], queryFn: () => resolversApi.cache({ resolver_code: resolverCode || undefined, object_type: objectType || undefined }) });
  const remove = useMutation({ mutationFn: resolversApi.deleteCacheEntry, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['resolver-cache'] }) });
  const metrics = useMemo(() => ({ entries: cache.data?.length ?? 0, hits: (cache.data ?? []).reduce((sum, item) => sum + item.hit_count, 0), expired: (cache.data ?? []).filter((item) => item.expires_at && new Date(item.expires_at) < new Date()).length }), [cache.data]);
  if (cache.isLoading) return <LoadingState label="Loading resolver cache" />;
  if (cache.error) return <ErrorState error={cache.error} />;
  const rows = cache.data ?? [];
  return (
    <div className="page-stack enterprise-runtime-page">
      <section className="page-header enterprise-hero"><span className="eyebrow">Resolver Cache</span><h1>Resolved Object Cache</h1><p>Inspect cached canonical objects, TTL and hit counters.</p><div className="hero-meta"><Link className="primary-link" to="/resolvers">Back to resolvers</Link><span className="microcopy">{metrics.entries} entries · {metrics.hits} hits · {metrics.expired} expired</span></div></section>
      <div className="filter-bar"><label className="field-label">Resolver code<input value={resolverCode} onChange={(event) => setParams((current) => updateParam(current, 'resolver_code', event.target.value))} /></label><label className="field-label">Object type<input value={objectType} onChange={(event) => setParams((current) => updateParam(current, 'object_type', event.target.value))} /></label></div>
      {remove.error instanceof Error && <div className="error-state compact">{remove.error.message}</div>}
      {rows.length === 0 ? <EmptyState title="Cache is empty" detail="Resolved objects will appear here after resolver execution with cache enabled." /> : <section className="table-panel runtime-table-panel"><div className="panel-toolbar"><h2>Cache entries</h2><span className="microcopy">Latest first</span></div><table><thead><tr><th>Resolver</th><th>Object</th><th>Key</th><th>Hits</th><th>Expires</th><th>Actions</th></tr></thead><tbody>{rows.map((item) => <tr key={item.id}><td><strong>{item.resolver_code}</strong><small>{item.source_system ?? '—'}</small></td><td>{item.object_type}</td><td>{item.cache_key}</td><td>{item.hit_count}</td><td>{item.expires_at ? new Date(item.expires_at).toLocaleString() : 'never'}</td><td><div className="action-row wrap-actions"><button className="ghost-button danger" disabled={remove.isPending} onClick={() => remove.mutate(item.id)}>Delete</button></div></td></tr>)}</tbody></table></section>}
      {rows[0] && <JsonBlock title="Latest resolved object" value={rows[0].resolved_object_json} searchable={false} />}
    </div>
  );
}

function updateParam(current: URLSearchParams, key: string, value: string): URLSearchParams {
  const next = new URLSearchParams(current);
  if (value) next.set(key, value);
  else next.delete(key);
  return next;
}
