import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { packagesApi } from '../api/packages';
import { CopyButton } from '../components/product/CopyButton';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

export function PackageDetailsPage() {
  const { packageId } = useParams();
  const queryClient = useQueryClient();
  const details = useQuery({ queryKey: ['package-details', packageId], queryFn: () => packagesApi.details(packageId!), enabled: Boolean(packageId) });
  const docs = useQuery({ queryKey: ['package-docs', packageId], queryFn: () => packagesApi.docs(packageId!), enabled: Boolean(packageId) });
  const capabilities = useQuery({ queryKey: ['package-capabilities', packageId], queryFn: () => packagesApi.capabilities(packageId!), enabled: Boolean(packageId) });
  const upgrade = useQuery({ queryKey: ['package-upgrade', packageId], queryFn: () => packagesApi.checkUpgrade(packageId!), enabled: Boolean(packageId) });
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['package-details', packageId] });
    queryClient.invalidateQueries({ queryKey: ['packages-installed'] });
    queryClient.invalidateQueries({ queryKey: ['packages-available'] });
    queryClient.invalidateQueries({ queryKey: ['packages-navigation'] });
    queryClient.invalidateQueries({ queryKey: ['package-capabilities', packageId] });
    queryClient.invalidateQueries({ queryKey: ['package-upgrade', packageId] });
    queryClient.invalidateQueries({ queryKey: ['plugin-store-catalog'] });
  };
  const install = useMutation({ mutationFn: () => packagesApi.install(packageId!, false), onSuccess: refresh });
  const installDemo = useMutation({ mutationFn: () => packagesApi.install(packageId!, true), onSuccess: refresh });
  const enable = useMutation({ mutationFn: () => packagesApi.enable(packageId!), onSuccess: refresh });
  const disable = useMutation({ mutationFn: () => packagesApi.disable(packageId!), onSuccess: refresh });
  const markUpgraded = useMutation({ mutationFn: () => packagesApi.markUpgraded(packageId!), onSuccess: refresh });

  if (details.isLoading) return <LoadingState label="Loading package details" />;
  if (details.error) return <ErrorState error={details.error} />;
  if (!details.data) return <ErrorState error={new Error('Package not found')} />;
  const manifest = details.data.manifest;
  const status = details.data.installed ? details.data.status ?? 'installed' : manifest.status;
  const canInstall = !details.data.installed && manifest.installable && details.data.compatible;
  const planned = (manifest.planned_capabilities ?? []).length ? manifest.planned_capabilities : manifest.capabilities ?? [];

  return (
    <div className="page-stack packages-page">
      <section className="page-header packages-hero product-page-header">
        <div>
          <span className="eyebrow">{manifest.category}</span>
          <h1>{manifest.name}</h1>
          <p>{manifest.description}</p>
          <div className="hero-meta"><StatusBadge status={status} />{upgrade.data?.upgrade_available && <StatusBadge status="warning" label="upgrade available" />}<span className="microcopy">{manifest.publisher} · {manifest.version}</span></div>
        </div>
        <div className="product-header-actions"><Link className="primary-link" to="/packages">Back to packages</Link></div>
      </section>

      <section className="panel package-lifecycle-panel">
        <div className="panel-toolbar"><div><span className="eyebrow">Lifecycle</span><h2>Installability and package identity</h2></div><StatusBadge status={status} /></div>
        <div className="metadata-grid compact-grid no-margin">
          <span>Package ID<strong>{manifest.package_id}</strong></span>
          <span>Installable<strong>{manifest.installable ? 'yes' : 'no'}</strong></span>
          <span>Expected version<strong>{manifest.expected_version ?? manifest.version}</strong></span>
          <span>Expected date<strong>{manifest.expected_date ?? 'released'}</strong></span>
        </div>
        <div className="package-id-row"><code>{manifest.package_id}</code><CopyButton value={manifest.package_id} label="Copy package ID" copiedLabel="Copied" /></div>
        {manifest.reason_unavailable && <div className="empty-state compact package-reason">{manifest.reason_unavailable}</div>}
        <div className="action-row wrap-actions">{canInstall && <button className="primary-button" onClick={() => install.mutate()}>Install</button>}{canInstall && <button className="ghost-button" onClick={() => installDemo.mutate()}>Install with demo data</button>}{!details.data.installed && !canInstall && <button className="ghost-button" type="button" disabled>{manifest.installable ? 'Blocked by compatibility' : 'Not installable yet'}</button>}{details.data.installed && (details.data.enabled ? <button className="ghost-button" onClick={() => disable.mutate()}>Disable package</button> : <button className="primary-button" onClick={() => enable.mutate()}>Enable package</button>)}{upgrade.data?.upgrade_available && <button className="ghost-button" onClick={() => markUpgraded.mutate()}>Mark upgraded</button>}</div>
        {!details.data.compatible && <div className="error-state compact">{[...details.data.compatibility_errors, ...details.data.dependency_errors].join('; ')}</div>}
        {details.data.dependency_warnings.length > 0 && <div className="empty-state compact">{details.data.dependency_warnings.join('; ')}</div>}
      </section>

      <section className="panel">
        <div className="panel-toolbar"><h2>{manifest.installable ? 'Capabilities' : 'Planned capabilities'}</h2><span className="microcopy">{planned.length}</span></div>
        {planned.length ? <div className="component-strip package-capabilities">{planned.map((capability) => <span key={capability}>{capability}</span>)}</div> : <EmptyState title="No capabilities published" detail="This package has not exposed its manifest capabilities yet." />}
      </section>

      <section className="package-detail-grid">
        <JsonBlock title="Manifest" value={manifest} />
        <section className="panel docs-panel"><div className="panel-toolbar"><h2>Docs</h2></div><pre className="doc-block">{docs.data?.readme ?? 'No docs loaded'}</pre>{docs.data?.quick_start && <pre className="doc-block">{docs.data.quick_start}</pre>}</section>
      </section>
      <section className="panel table-panel">
        <div className="panel-toolbar"><h2>Runtime capabilities</h2><span className="microcopy">{capabilities.data?.length ?? 0}</span></div>
        {(capabilities.data ?? []).length ? <table><thead><tr><th>Type</th><th>Code</th><th>Status</th><th>Owner</th></tr></thead><tbody>{(capabilities.data ?? []).map((item) => <tr key={`${item.capability_type}:${item.capability_code}`}><td>{item.capability_type}</td><td><strong>{item.capability_code}</strong></td><td><StatusBadge status={item.enabled ? 'enabled' : 'disabled'} compact /></td><td>{item.package_id}</td></tr>)}</tbody></table> : <EmptyState title="No runtime capabilities" detail="Capabilities appear here after installation or when a package exposes backend/frontend extension points." />}
      </section>
      {[install.error, installDemo.error, enable.error, disable.error, markUpgraded.error].find(Boolean) instanceof Error && <div className="error-state compact">{(([install.error, installDemo.error, enable.error, disable.error, markUpgraded.error].find(Boolean)) as Error).message}</div>}
    </div>
  );
}
