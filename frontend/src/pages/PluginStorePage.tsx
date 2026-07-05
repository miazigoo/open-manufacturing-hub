import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { packagesApi, pluginStoreApi, type PluginStoreItem } from '../api/packages';
import { CopyButton } from '../components/product/CopyButton';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { useT } from '../i18n/useI18n';

export function PluginStorePage() {
  const t = useT();
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

  if (catalog.isLoading || categories.isLoading) return <LoadingState label={t('packages.storeLoading')} />;
  if (catalog.error) return <ErrorState error={catalog.error} />;

  return (
    <div className="page-stack plugin-store-page">
      <section className="page-header plugin-store-hero product-page-header">
        <div>
          <span className="eyebrow">{t('nav.pluginStore')}</span>
          <h1>{t('packages.storeTitle')}</h1>
          <p>{t('packages.storeSubtitle')}</p>
        </div>
        <div className="product-header-actions"><Link className="primary-button" to="/packages">{t('packages.installed')}</Link><span className="microcopy">{t('packages.localCatalog')}</span></div>
      </section>

      <section className="panel plugin-store-toolbar">
        <label className="field-label">{t('packages.search')}<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t('packages.searchPlaceholder')} /></label>
        <div className="segmented-control package-category-control"><button className={filter === 'all' ? 'active' : ''} onClick={() => setFilter('all')}>{t('packages.all')}</button>{categories.data?.map((category) => <button key={category.category} className={filter === category.category ? 'active' : ''} onClick={() => setFilter(category.category)}>{category.category} ({category.count})</button>)}</div>
      </section>

      {filtered.length ? <section className="plugin-card-grid">{filtered.map((item) => <PluginCard key={item.package_id} item={item} busy={install.isPending || enable.isPending || disable.isPending} onInstall={() => install.mutate(item.package_id)} onEnable={() => enable.mutate(item.package_id)} onDisable={() => disable.mutate(item.package_id)} />)}</section> : <EmptyState title={t('packages.noMatches')} detail={t('packages.noMatchesDetail')} />}
      {[install.error, enable.error, disable.error].find(Boolean) instanceof Error && <div className="error-state compact">{(([install.error, enable.error, disable.error].find(Boolean)) as Error).message}</div>}
    </div>
  );
}

function PluginCard({ item, busy, onInstall, onEnable, onDisable }: { item: PluginStoreItem; busy: boolean; onInstall: () => void; onEnable: () => void; onDisable: () => void }) {
  const t = useT();
  const status = item.installed ? item.status : item.status || 'available';
  const canInstall = !item.installed && Boolean(item.installable);
  return (
    <article className={`panel plugin-card lifecycle-${status}`}>
      <div className="panel-toolbar">
        <div><span className="eyebrow">{item.official ? t('common.labels.official') : t('packages.roadmap')}</span><h2>{item.name}</h2></div>
        <StatusBadge status={status} />
      </div>
      <p>{item.description}</p>
      <div className="metadata-grid compact-grid no-margin">
        <span>{t('common.labels.version')}<strong>{item.version}</strong></span>
        <span>{t('common.labels.category')}<strong>{item.category}</strong></span>
        <span>{t('packages.install')}<strong>{item.installable ? t('statuses.available') : t('packages.locked')}</strong></span>
        {item.expected_date && <span>{t('packages.expected')}<strong>{item.expected_date}</strong></span>}
      </div>
      <div className="package-id-row"><code>{item.package_id}</code><CopyButton value={item.package_id} label={t('packages.copyId')} copiedLabel={t('packages.copied')} /></div>
      <CapabilityStrip values={item.planned_capabilities ?? []} fallback={t('packages.noCapabilities')} />
      {item.reason_unavailable && <div className="empty-state compact package-reason">{item.reason_unavailable}</div>}
      <div className="action-row wrap-actions">
        <Link className="primary-link" to={`/packages/${item.package_id}`}>{item.installed && item.enabled ? t('packages.open') : t('packages.details')}</Link>
        {item.installed && item.enabled && <button className="ghost-button" onClick={onDisable} disabled={busy}>{t('packages.disable')}</button>}
        {item.installed && !item.enabled && <button className="primary-button" onClick={onEnable} disabled={busy}>{t('packages.enable')}</button>}
        {item.installed && <Link className="primary-link" to={`/packages/${item.package_id}`}>{t('packages.docs')}</Link>}
        {canInstall && <button className="primary-button" onClick={onInstall} disabled={busy}>{t('packages.install')}</button>}
        {!item.installed && !item.installable && <button className="ghost-button" type="button" disabled>{actionLabel(item.status, t)}</button>}
      </div>
    </article>
  );
}

function CapabilityStrip({ values, fallback }: { values: string[]; fallback: string }) {
  if (!values?.length) return <span className="microcopy">{fallback}</span>;
  return <div className="component-strip package-capabilities">{values.slice(0, 6).map((capability) => <span key={capability}>{capability}</span>)}</div>;
}

function actionLabel(status: string, t: (key: string) => string) {
  if (status === 'coming_soon') return t('statuses.coming_soon');
  if (status === 'in_development') return t('statuses.in_development');
  if (status === 'incompatible') return t('statuses.incompatible');
  return t('packages.notInstallable');
}
