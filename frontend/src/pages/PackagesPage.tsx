import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { asJson } from '../api/client';
import { packagesApi } from '../api/packages';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

export function PackagesPage() {
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
  const enable = useMutation({ mutationFn: packagesApi.enable, onSuccess: refresh });
  const disable = useMutation({ mutationFn: packagesApi.disable, onSuccess: refresh });
  const demo = useMutation({ mutationFn: packagesApi.installDemoData, onSuccess: refresh });

  if (packages.isLoading || available.isLoading) return <LoadingState label="Loading integration packages" />;
  if (packages.error) return <ErrorState error={packages.error} />;

  return (
    <div className="page-stack packages-page">
      <section className="page-header packages-hero">
        <span className="eyebrow">Integration Packages</span>
        <h1>Package runtime boundary</h1>
        <p>Installed packages provide ecosystem-specific connectors, presets, pages and docs without hardcoding client logic into OMH Core.</p>
        <div className="hero-meta"><Link className="primary-button" to="/plugin-store">Open Plugin Store</Link><button className="ghost-button" onClick={() => exportConfig.mutate()}>Export package config</button></div>
      </section>

      <section className="panel table-panel">
        <div className="panel-toolbar"><h2>Installed packages</h2><span className="microcopy">{packages.data?.length ?? 0}</span></div>
        {(packages.data ?? []).length === 0 ? <EmptyState title="No packages installed" detail="Install official packages from Plugin Store." /> : <table><thead><tr><th>Name</th><th>Version</th><th>Status</th><th>Official</th><th>Actions</th></tr></thead><tbody>{packages.data?.map((item) => <tr key={item.package_id}><td><strong>{item.name}</strong><small>{item.package_id}</small>{item.last_error && <small className="error-text">{item.last_error}</small>}</td><td>{item.version}</td><td><StatusBadge status={item.enabled ? 'ok' : 'cancelled'} label={item.status} compact /></td><td>{item.official ? 'Official' : 'Community'}</td><td><div className="action-row wrap-actions"><Link className="primary-link" to={`/packages/${item.package_id}`}>Open</Link>{item.enabled ? <button className="ghost-button" onClick={() => disable.mutate(item.package_id)}>Disable</button> : <button className="ghost-button" onClick={() => enable.mutate(item.package_id)}>Enable</button>}<button className="ghost-button" onClick={() => demo.mutate(item.package_id)}>Install demo data</button></div></td></tr>)}</tbody></table>}
      </section>

      <section className="panel table-panel">
        <div className="panel-toolbar"><h2>Compatibility report</h2><span className="microcopy">Core {compatibility.data?.core_version ?? 'unknown'}</span></div>
        <table><thead><tr><th>Package</th><th>State</th><th>Compatibility</th><th>Notes</th></tr></thead><tbody>{(compatibility.data?.packages ?? []).map((item) => <tr key={item.package_id}><td><strong>{item.name}</strong><small>{item.package_id}</small></td><td><StatusBadge status={item.enabled ? 'ok' : item.installed ? 'warning' : 'pending'} label={item.status} compact /></td><td><StatusBadge status={item.compatible ? 'ok' : 'failed'} label={item.compatible ? 'compatible' : 'blocked'} compact />{item.upgrade_available && <small>Upgrade available</small>}</td><td>{[...item.errors, ...item.warnings].length ? <small>{[...item.errors, ...item.warnings].join('; ')}</small> : <small>Ready</small>}</td></tr>)}</tbody></table>
      </section>

      <section className="card-grid package-card-grid">
        {(available.data ?? []).map((item) => <article key={item.manifest.package_id} className="panel package-card"><div className="panel-toolbar"><div><span className="eyebrow">{item.manifest.category}</span><h2>{item.manifest.name}</h2></div><StatusBadge status={item.enabled ? 'ok' : item.installed ? 'warning' : 'pending'} label={item.installed ? item.status ?? 'installed' : 'available'} /></div><p>{item.manifest.description}</p><div className="component-strip">{item.manifest.capabilities.slice(0, 6).map((capability) => <span key={capability}>{capability}</span>)}</div><div className="action-row"><Link className="primary-link" to={`/packages/${item.manifest.package_id}`}>Details</Link>{!item.compatible && <span className="error-text">Incompatible</span>}{item.upgrade_available && <span className="microcopy">Upgrade available</span>}</div></article>)}
      </section>

      {exportConfig.data && <JsonBlock title="Package config export" value={exportConfig.data} />}
      {[enable.error, disable.error, demo.error, exportConfig.error].find(Boolean) instanceof Error && <div className="error-state compact">{(([enable.error, disable.error, demo.error, exportConfig.error].find(Boolean)) as Error).message}</div>}
    </div>
  );
}
