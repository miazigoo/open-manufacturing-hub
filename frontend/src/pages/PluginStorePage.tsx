import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { packagesApi, pluginStoreApi, type PluginStoreItem } from '../api/packages';
import { CopyButton } from '../components/product/CopyButton';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

export function PluginStorePage() {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState('all');
  const [query, setQuery] = useState('');
  const catalog = useQuery({ queryKey: ['plugin-store-catalog'], queryFn: pluginStoreApi.catalog });
  const categories = useQuery({ queryKey: ['plugin-store-categories'], queryFn: pluginStoreApi.categories });
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['plugin-store-catalog'] });
    queryClient.invalidateQueries({ queryKey: ['packages-installed'] });
    queryClient.invalidateQueries({ queryKey: ['packages-available'] });
    queryClient.invalidateQueries({ queryKey: ['packages-navigation'] });
    queryClient.invalidateQueries({ queryKey: ['ui-navigation'] });
  };
  const install = useMutation({ mutationFn: (packageId: string) => packagesApi.install(packageId, false), onSuccess: refresh });
  const enable = useMutation({ mutationFn: (packageId: string) => packagesApi.enable(packageId), onSuccess: refresh });
  const disable = useMutation({ mutationFn: (packageId: string) => packagesApi.disable(packageId), onSuccess: refresh });
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return (catalog.data ?? []).filter((item) => {
      const categoryMatches = filter === 'all' || item.category === filter;
      const queryMatches = !needle || [item.name, item.package_id, item.description, item.category, item.status].join(' ').toLowerCase().includes(needle);
      return categoryMatches && queryMatches;
    });
  }, [catalog.data, filter, query]);

  if (catalog.isLoading || categories.isLoading) return <LoadingState label="Loading plugin store" />;
  if (catalog.error) return <ErrorState error={catalog.error} />;

  return (
    <div className="page-stack plugin-store-page">
      <section className="page-header plugin-store-hero product-page-header">
        <div>
          <span className="eyebrow">Plugin Store</span>
          <h1>Package catalog with honest lifecycle states.</h1>
          <p>Install released official packages, inspect upcoming adapters and copy package IDs without guessing what is production-ready.</p>
        </div>
        <div className="product-header-actions"><Link className="primary-button" to="/packages">Installed packages</Link><span className="microcopy">Local catalog</span></div>
      </section>

      <section className="panel plugin-store-toolbar">
        <label className="field-label">Search packages<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="1C, SAP, MQTT, security..." /></label>
        <div className="segmented-control package-category-control"><button className={filter === 'all' ? 'active' : ''} onClick={() => setFilter('all')}>All</button>{categories.data?.map((category) => <button key={category.category} className={filter === category.category ? 'active' : ''} onClick={() => setFilter(category.category)}>{category.category} ({category.count})</button>)}</div>
      </section>

      {filtered.length ? <section className="plugin-card-grid">{filtered.map((item) => <PluginCard key={item.package_id} item={item} busy={install.isPending || enable.isPending || disable.isPending} onInstall={() => install.mutate(item.package_id)} onEnable={() => enable.mutate(item.package_id)} onDisable={() => disable.mutate(item.package_id)} />)}</section> : <EmptyState title="No packages match filters" detail="Clear search or select another category." />}
      {[install.error, enable.error, disable.error].find(Boolean) instanceof Error && <div className="error-state compact">{(([install.error, enable.error, disable.error].find(Boolean)) as Error).message}</div>}
    </div>
  );
}

function PluginCard({ item, busy, onInstall, onEnable, onDisable }: { item: PluginStoreItem; busy: boolean; onInstall: () => void; onEnable: () => void; onDisable: () => void }) {
  const status = item.installed ? item.status : item.status || 'available';
  const canInstall = !item.installed && Boolean(item.installable);
  return (
    <article className={`panel plugin-card lifecycle-${status}`}>
      <div className="panel-toolbar">
        <div><span className="eyebrow">{item.official ? 'Official' : 'Roadmap'}</span><h2>{item.name}</h2></div>
        <StatusBadge status={status} label={item.installed ? item.status : status} />
      </div>
      <p>{item.description}</p>
      <div className="metadata-grid compact-grid no-margin">
        <span>Version<strong>{item.version}</strong></span>
        <span>Category<strong>{item.category}</strong></span>
        <span>Install<strong>{item.installable ? 'available' : 'locked'}</strong></span>
        {item.expected_date && <span>Expected<strong>{item.expected_date}</strong></span>}
      </div>
      <div className="package-id-row"><code>{item.package_id}</code><CopyButton value={item.package_id} label="Copy ID" copiedLabel="Copied" /></div>
      <CapabilityStrip values={item.planned_capabilities ?? []} fallback="No capabilities published yet" />
      {item.reason_unavailable && <div className="empty-state compact package-reason">{item.reason_unavailable}</div>}
      <div className="action-row wrap-actions">
        <Link className="primary-link" to={`/packages/${item.package_id}`}>{item.installed && item.enabled ? 'Open' : 'Details'}</Link>
        {item.installed && item.enabled && <button className="ghost-button" onClick={onDisable} disabled={busy}>Disable</button>}
        {item.installed && !item.enabled && <button className="primary-button" onClick={onEnable} disabled={busy}>Enable</button>}
        {item.installed && <Link className="primary-link" to={`/packages/${item.package_id}`}>Docs</Link>}
        {canInstall && <button className="primary-button" onClick={onInstall} disabled={busy}>Install</button>}
        {!item.installed && !item.installable && <button className="ghost-button" type="button" disabled>{actionLabel(item.status)}</button>}
      </div>
    </article>
  );
}

function CapabilityStrip({ values, fallback }: { values: string[]; fallback: string }) {
  if (!values?.length) return <span className="microcopy">{fallback}</span>;
  return <div className="component-strip package-capabilities">{values.slice(0, 6).map((capability) => <span key={capability}>{capability}</span>)}</div>;
}

function actionLabel(status: string) {
  if (status === 'coming_soon') return 'Coming soon';
  if (status === 'in_development') return 'In development';
  if (status === 'incompatible') return 'Incompatible';
  return 'Not installable';
}
