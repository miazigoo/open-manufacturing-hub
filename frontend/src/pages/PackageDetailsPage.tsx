import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { packagesApi } from '../api/packages';
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

  return (
    <div className="page-stack packages-page">
      <section className="page-header packages-hero">
        <span className="eyebrow">{manifest.category}</span>
        <h1>{manifest.name}</h1>
        <p>{manifest.description}</p>
        <div className="hero-meta"><StatusBadge status={details.data.enabled ? 'ok' : details.data.installed ? 'warning' : 'pending'} label={details.data.installed ? details.data.status ?? 'installed' : 'available'} /><span className="microcopy">{manifest.publisher} · {manifest.version}</span>{upgrade.data?.upgrade_available && <StatusBadge status="warning" label="upgrade available" />}</div>
      </section>
      <section className="panel">
        <div className="action-row wrap-actions"><Link className="primary-link" to="/packages">Back to packages</Link>{!details.data.installed && <button className="primary-button" onClick={() => install.mutate()}>Install</button>}{!details.data.installed && <button className="ghost-button" onClick={() => installDemo.mutate()}>Install with demo data</button>}{details.data.installed && (details.data.enabled ? <button className="ghost-button" onClick={() => disable.mutate()}>Disable package</button> : <button className="primary-button" onClick={() => enable.mutate()}>Enable package</button>)}{upgrade.data?.upgrade_available && <button className="ghost-button" onClick={() => markUpgraded.mutate()}>Mark upgraded</button>}</div>
        {!details.data.compatible && <div className="error-state compact">{[...details.data.compatibility_errors, ...details.data.dependency_errors].join('; ')}</div>}
        {details.data.dependency_warnings.length > 0 && <div className="empty-state compact">{details.data.dependency_warnings.join('; ')}</div>}
      </section>
      <section className="package-detail-grid">
        <JsonBlock title="Manifest" value={manifest} />
        <section className="panel docs-panel"><div className="panel-toolbar"><h2>Docs</h2></div><pre className="doc-block">{docs.data?.readme ?? 'No docs loaded'}</pre>{docs.data?.quick_start && <pre className="doc-block">{docs.data.quick_start}</pre>}</section>
      </section>
      <section className="panel table-panel">
        <div className="panel-toolbar"><h2>Runtime capabilities</h2><span className="microcopy">{capabilities.data?.length ?? 0}</span></div>
        <table><thead><tr><th>Type</th><th>Code</th><th>Status</th><th>Owner</th></tr></thead><tbody>{(capabilities.data ?? []).map((item) => <tr key={`${item.capability_type}:${item.capability_code}`}><td>{item.capability_type}</td><td><strong>{item.capability_code}</strong></td><td><StatusBadge status={item.enabled ? 'ok' : 'cancelled'} label={item.enabled ? 'enabled' : 'disabled'} compact /></td><td>{item.package_id}</td></tr>)}</tbody></table>
      </section>
      {[install.error, installDemo.error, enable.error, disable.error, markUpgraded.error].find(Boolean) instanceof Error && <div className="error-state compact">{(([install.error, installDemo.error, enable.error, disable.error, markUpgraded.error].find(Boolean)) as Error).message}</div>}
    </div>
  );
}
