import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { packagesApi, pluginStoreApi } from '../api/packages';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

export function PluginStorePage() {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState('all');
  const catalog = useQuery({ queryKey: ['plugin-store-catalog'], queryFn: pluginStoreApi.catalog });
  const categories = useQuery({ queryKey: ['plugin-store-categories'], queryFn: pluginStoreApi.categories });
  const install = useMutation({ mutationFn: (packageId: string) => packagesApi.install(packageId, false), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['plugin-store-catalog'] }); queryClient.invalidateQueries({ queryKey: ['packages-installed'] }); queryClient.invalidateQueries({ queryKey: ['packages-navigation'] }); } });
  const filtered = useMemo(() => (catalog.data ?? []).filter((item) => filter === 'all' || item.category === filter), [catalog.data, filter]);

  if (catalog.isLoading || categories.isLoading) return <LoadingState label="Loading plugin store" />;
  if (catalog.error) return <ErrorState error={catalog.error} />;

  return (
    <div className="page-stack plugin-store-page">
      <section className="page-header plugin-store-hero">
        <span className="eyebrow">Plugin Store Foundation</span>
        <h1>Local package catalog</h1>
        <p>Official and community package slots for ecosystem-specific integrations. Remote marketplace, signatures and downloads come later.</p>
        <div className="hero-meta"><Link className="primary-button" to="/packages">Installed packages</Link><span className="microcopy">Local catalog only</span></div>
      </section>
      <section className="panel"><div className="segmented-control package-category-control"><button className={filter === 'all' ? 'active' : ''} onClick={() => setFilter('all')}>All</button>{categories.data?.map((category) => <button key={category.category} className={filter === category.category ? 'active' : ''} onClick={() => setFilter(category.category)}>{category.category} ({category.count})</button>)}</div></section>
      <section className="plugin-card-grid">{filtered.map((item) => <article key={item.package_id} className="panel plugin-card"><div className="panel-toolbar"><div><span className="eyebrow">{item.official ? 'Official' : 'Community'}</span><h2>{item.name}</h2></div><StatusBadge status={item.enabled ? 'ok' : item.installed ? 'warning' : 'pending'} label={item.installed ? (item.enabled ? 'enabled' : 'installed') : 'not installed'} /></div><p>{item.description}</p><div className="metadata-grid compact-grid no-margin"><span>Version<strong>{item.version}</strong></span><span>Category<strong>{item.category}</strong></span><span>Package<strong>{item.package_id}</strong></span></div><div className="action-row wrap-actions"><Link className="primary-link" to={`/packages/${item.package_id}`}>Open</Link>{!item.installed && item.official && <button className="primary-button" onClick={() => install.mutate(item.package_id)} disabled={install.isPending}>Install</button>}{!item.official && <span className="microcopy">Placeholder</span>}</div></article>)}</section>
      {install.error instanceof Error && <div className="error-state compact">{install.error.message}</div>}
    </div>
  );
}
