import { FormEvent, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { resolversApi } from '../api/resolvers';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

function parseObject(value: string, label: string): Record<string, unknown> {
  const parsed = JSON.parse(value || '{}') as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error(`${label} must be a JSON object`);
  return parsed as Record<string, unknown>;
}

export function ResolverDetailsPage() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const resolver = useQuery({ queryKey: ['resolver-v2', id], queryFn: () => resolversApi.get(id!), enabled: Boolean(id) });
  const [input, setInput] = useState(asJson({ inn: '1234567890' }));
  const [error, setError] = useState<string | null>(null);
  const resolve = useMutation({ mutationFn: () => resolversApi.resolve(id!, parseObject(input, 'Resolver input')) });
  const clear = useMutation({ mutationFn: () => resolversApi.clearCache(id!), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['resolver-cache'] }) });
  if (resolver.isLoading) return <LoadingState label="Loading resolver" />;
  if (resolver.error) return <ErrorState error={resolver.error} />;
  if (!resolver.data) return <ErrorState error={new Error('Resolver not found')} />;
  const item = resolver.data;
  function run(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try { resolve.mutate(); } catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid JSON'); }
  }
  return (
    <div className="page-stack enterprise-runtime-page">
      <section className="page-header enterprise-hero"><span className="eyebrow">Resolver Details</span><h1>{item.name}</h1><p><code>{item.resolver_code}</code> resolves {item.object_type} through {item.strategy}.</p><div className="hero-meta"><StatusBadge status={item.enabled ? 'ok' : 'warning'} label={item.enabled ? 'enabled' : 'disabled'} /><Link className="primary-link" to="/resolvers">Back to resolvers</Link><Link className="primary-link" to={`/resolvers/cache?resolver_code=${encodeURIComponent(item.resolver_code)}`}>Open cache</Link></div></section>
      <section className="runtime-grid">
        <form className="panel stack-form runtime-control-card" onSubmit={run}><span className="eyebrow">Test bench</span><h2>Resolve now</h2><label className="field-label">Input JSON<textarea value={input} onChange={(event) => setInput(event.target.value)} /></label><div className="action-row wrap-actions"><button className="primary-button" disabled={resolve.isPending}>Resolve</button><button className="ghost-button" type="button" onClick={() => clear.mutate()} disabled={clear.isPending}>Clear cache</button></div>{error && <div className="error-state compact">{error}</div>}{resolve.error instanceof Error && <div className="error-state compact">{resolve.error.message}</div>}{clear.data && <div className="success-note">Cache cleared<span>{clear.data.deleted} entries</span></div>}</form>
        <section className="page-stack"><JsonBlock title="Definition" value={item} searchable={false} />{resolve.data && <JsonBlock title="Resolve result" value={resolve.data} searchable={false} />}</section>
      </section>
    </div>
  );
}
