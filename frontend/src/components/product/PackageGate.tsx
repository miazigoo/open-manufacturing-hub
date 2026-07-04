import type { ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { packagesApi } from '../../api/packages';
import { ErrorState } from '../ErrorState';
import { LoadingState } from '../LoadingState';
import { StatusBadge } from '../StatusBadge';
import { SectionCard } from './SectionCard';

interface PackageGateProps {
  packageId: string;
  children: ReactNode;
}

export function PackageGate({ packageId, children }: PackageGateProps) {
  const queryClient = useQueryClient();
  const details = useQuery({ queryKey: ['package-details', packageId], queryFn: () => packagesApi.details(packageId), retry: false });
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['package-details', packageId] });
    queryClient.invalidateQueries({ queryKey: ['packages-installed'] });
    queryClient.invalidateQueries({ queryKey: ['packages-available'] });
    queryClient.invalidateQueries({ queryKey: ['ui-navigation'] });
    queryClient.invalidateQueries({ queryKey: ['plugin-store-catalog'] });
  };
  const install = useMutation({ mutationFn: () => packagesApi.install(packageId, true), onSuccess: refresh });
  const enable = useMutation({ mutationFn: () => packagesApi.enable(packageId), onSuccess: refresh });

  if (details.isLoading) return <LoadingState label="Checking package state" />;
  if (details.error) return <ErrorState error={details.error} />;
  if (!details.data) return <ErrorState error={new Error(`Package ${packageId} not found`)} />;
  if (details.data.installed && details.data.enabled) return <>{children}</>;

  const manifest = details.data.manifest;
  const status = details.data.installed ? 'disabled' : manifest.status;
  const canInstall = !details.data.installed && manifest.installable && details.data.compatible;
  const canEnable = details.data.installed && !details.data.enabled;
  const action = canEnable ? (
    <button className="primary-button" onClick={() => enable.mutate()} disabled={enable.isPending}>Enable package</button>
  ) : canInstall ? (
    <button className="primary-button" onClick={() => install.mutate()} disabled={install.isPending}>Install package</button>
  ) : (
    <button className="ghost-button" type="button" disabled>{lockedActionLabel(status)}</button>
  );

  return (
    <div className="page-stack package-gate-page">
      <section className="page-header enterprise-hero">
        <span className="eyebrow">Package Gate</span>
        <h1>{manifest.name}</h1>
        <p>{manifest.description}</p>
        <div className="hero-meta"><StatusBadge status={status} />{action}</div>
      </section>
      <SectionCard title={gateTitle(status, details.data.installed)} description={gateDescription(status, details.data.installed)}>
        <div className="package-gate-panel">
          <p>{manifest.reason_unavailable || 'The gate prevents half-working screens and stale routes by checking package lifecycle state before rendering package-specific UI.'}</p>
          {!details.data.compatible && <div className="error-state compact">{[...details.data.compatibility_errors, ...details.data.dependency_errors].join('; ')}</div>}
          {(install.error || enable.error) && <div className="error-state compact">{((install.error ?? enable.error) as Error).message}</div>}
        </div>
      </SectionCard>
    </div>
  );
}

function lockedActionLabel(status: string) {
  if (status === 'coming_soon') return 'Coming Soon';
  if (status === 'in_development') return 'In Development';
  if (status === 'incompatible') return 'Incompatible';
  return 'Not installable';
}

function gateTitle(status: string, installed: boolean) {
  if (installed) return 'Package is installed but disabled';
  if (status === 'coming_soon') return 'Package is coming soon';
  if (status === 'in_development') return 'Package is in development';
  if (status === 'incompatible') return 'Package is incompatible';
  return 'Package installation required';
}

function gateDescription(status: string, installed: boolean) {
  if (installed) return 'Enable the package to open this workspace.';
  if (status === 'coming_soon') return 'This package is visible in the catalog but cannot be installed yet.';
  if (status === 'in_development') return 'This package is under active development and is locked by default.';
  if (status === 'incompatible') return 'This package cannot run on the current OMH Core version.';
  return 'Install and enable the package to open this workspace.';
}
