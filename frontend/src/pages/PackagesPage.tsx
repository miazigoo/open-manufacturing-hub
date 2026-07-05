import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { packagesApi, type PackageAvailable } from '../api/packages';
import { CopyButton } from '../components/product/CopyButton';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { useT } from '../i18n/useI18n';

export function PackagesPage() {
  const t = useT();
  const queryClient = useQueryClient();
  const packages = useQuery({ queryKey: ['packages-installed'], queryFn: packagesApi.installed });
  const available = useQuery({ queryKey: ['packages-available'], queryFn: packagesApi.available });
  const compatibility = useQuery({ queryKey: ['packages-compatibility'], queryFn: packagesApi.compatibilityReport });
  const exportConfig = useMutation({ mutationFn: packagesApi.exportConfig });
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['packages-installed'] });
    queryClient.invalidateQueries({ queryKey: ['packages-available'] });
    queryClient.invalidateQueries({ queryKey: ['packages-navigation'] });
    queryClient.invalidateQueries({ queryKey: ['packages-compatibility'] });
    queryClient.invalidateQueries({ queryKey: ['plugin-store-catalog'] });
  };
  const install = useMutation({ mutationFn: (packageId: string) => packagesApi.install(packageId, false), onSuccess: refresh });
  const enable = useMutation({ mutationFn: packagesApi.enable, onSuccess: refresh });
  const disable = useMutation({ mutationFn: packagesApi.disable, onSuccess: refresh });
  const demo = useMutation({ mutationFn: packagesApi.installDemoData, onSuccess: refresh });

  if (packages.isLoading || available.isLoading) return <LoadingState label={t('packages.loading')} />;
  if (packages.error) return <ErrorState error={packages.error} />;

  return (
    <div className="page-stack packages-page">
      <section className="page-header packages-hero product-page-header">
        <div>
          <span className="eyebrow">{t('packages.eyebrow')}</span>
          <h1>{t('packages.title')}</h1>
          <p>{t('packages.subtitle')}</p>
        </div>
        <div className="product-header-actions"><Link className="primary-button" to="/plugin-store">{t('packages.openPluginStore')}</Link><button className="ghost-button" onClick={() => exportConfig.mutate()}>{t('packages.exportConfig')}</button></div>
      </section>

      <section className="panel table-panel">
        <div className="panel-toolbar"><h2>{t('packages.installed')}</h2><span className="microcopy">{packages.data?.length ?? 0}</span></div>
        {(packages.data ?? []).length === 0 ? <EmptyState title={t('packages.noneInstalled')} detail={t('packages.noneInstalledDetail')} /> : <table><thead><tr><th>{t('common.labels.name')}</th><th>{t('common.labels.version')}</th><th>{t('common.labels.status')}</th><th>{t('common.labels.official')}</th><th>{t('common.labels.actions')}</th></tr></thead><tbody>{packages.data?.map((item) => <tr key={item.package_id}><td><strong>{item.name}</strong><small>{item.package_id}</small>{item.last_error && <small className="error-text">{item.last_error}</small>}</td><td>{item.version}</td><td><StatusBadge status={item.enabled ? 'enabled' : 'disabled'} compact /></td><td>{item.official ? t('common.labels.official') : t('common.labels.community')}</td><td><div className="action-row wrap-actions"><Link className="primary-link" to={`/packages/${item.package_id}`}>{t('common.buttons.open')}</Link>{item.enabled ? <button className="ghost-button" onClick={() => disable.mutate(item.package_id)}>{t('packages.disable')}</button> : <button className="ghost-button" onClick={() => enable.mutate(item.package_id)}>{t('packages.enable')}</button>}<button className="ghost-button" onClick={() => demo.mutate(item.package_id)}>{t('packages.installDemoData')}</button></div></td></tr>)}</tbody></table>}
      </section>

      <section className="panel table-panel">
        <div className="panel-toolbar"><h2>{t('packages.compatibility')}</h2><span className="microcopy">Core {compatibility.data?.core_version ?? t('common.labels.unknown')}</span></div>
        <table><thead><tr><th>{t('packages.package')}</th><th>{t('packages.state')}</th><th>{t('packages.compatibility')}</th><th>{t('packages.notes')}</th></tr></thead><tbody>{(compatibility.data?.packages ?? []).map((item) => <tr key={item.package_id}><td><strong>{item.name}</strong><small>{item.package_id}</small></td><td><StatusBadge status={item.status} compact /></td><td><StatusBadge status={item.compatible ? 'ok' : 'failed'} label={item.compatible ? t('common.labels.ready') : t('packages.blocked')} compact />{item.upgrade_available && <small>{t('packages.upgradeAvailable')}</small>}</td><td>{[...item.errors, ...item.warnings].length ? <small>{[...item.errors, ...item.warnings].join('; ')}</small> : <small>{t('common.labels.ready')}</small>}</td></tr>)}</tbody></table>
      </section>

      <section className="card-grid package-card-grid">
        {(available.data ?? []).map((item) => <PackageCard key={item.manifest.package_id} item={item} installing={install.isPending} onInstall={() => install.mutate(item.manifest.package_id)} />)}
      </section>

      {exportConfig.data && <JsonBlock title={t('packages.copyConfigTitle')} value={exportConfig.data} />}
      {[install.error, enable.error, disable.error, demo.error, exportConfig.error].find(Boolean) instanceof Error && <div className="error-state compact">{(([install.error, enable.error, disable.error, demo.error, exportConfig.error].find(Boolean)) as Error).message}</div>}
    </div>
  );
}

function PackageCard({ item, installing, onInstall }: { item: PackageAvailable; installing: boolean; onInstall: () => void }) {
  const t = useT();
  const manifest = item.manifest;
  const status = item.installed ? item.status ?? 'installed' : manifest.status;
  const canInstall = !item.installed && manifest.installable && item.compatible;
  const capabilities = (manifest.capabilities ?? []).length ? manifest.capabilities : manifest.planned_capabilities ?? [];
  return (
    <article className={`panel package-card lifecycle-${status}`}>
      <div className="panel-toolbar"><div><span className="eyebrow">{manifest.category}</span><h2>{manifest.name}</h2></div><StatusBadge status={status} /></div>
      <p>{manifest.description}</p>
      <div className="package-id-row"><code>{manifest.package_id}</code><CopyButton value={manifest.package_id} label={t('packages.copyId')} copiedLabel={t('packages.copied')} /></div>
      <div className="component-strip package-capabilities">{capabilities.slice(0, 6).map((capability) => <span key={capability}>{capability}</span>)}</div>
      {manifest.expected_date && <span className="microcopy">{t('packages.expected')}: {manifest.expected_date} · {t('common.labels.version')} {manifest.expected_version ?? manifest.version}</span>}
      {(manifest.reason_unavailable || item.dependency_warnings.length > 0) && <div className="empty-state compact package-reason">{manifest.reason_unavailable ?? item.dependency_warnings.join('; ')}</div>}
      <div className="action-row wrap-actions"><Link className="primary-link" to={`/packages/${manifest.package_id}`}>{t('packages.details')}</Link>{canInstall && <button className="primary-button" onClick={onInstall} disabled={installing}>{t('packages.install')}</button>}{!canInstall && !item.installed && <button className="ghost-button" type="button" disabled>{manifest.installable ? t('packages.blocked') : t('packages.notInstallable')}</button>}{!item.compatible && <span className="error-text">{t('statuses.incompatible')}</span>}{item.upgrade_available && <span className="microcopy">{t('packages.upgradeAvailable')}</span>}</div>
    </article>
  );
}
