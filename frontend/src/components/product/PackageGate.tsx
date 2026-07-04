import type { ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { packagesApi } from '../../api/packages';
import { ErrorState } from '../ErrorState';
import { LoadingState } from '../LoadingState';
import { SectionCard } from './SectionCard';

interface PackageGateProps {
  packageId: string;
  children: ReactNode;
}

export function PackageGate({ packageId, children }: PackageGateProps) {
  const queryClient = useQueryClient();
  const details = useQuery({ queryKey: ['package-details', packageId], queryFn: () => packagesApi.details(packageId), retry: false });
  const install = useMutation({ mutationFn: () => packagesApi.install(packageId, true), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['package-details', packageId] }) });
  const enable = useMutation({ mutationFn: () => packagesApi.enable(packageId), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['package-details', packageId] }) });

  if (details.isLoading) return <LoadingState label="Checking package state" />;
  if (details.error) return <ErrorState error={details.error} />;
  if (!details.data) return <ErrorState error={new Error(`Package ${packageId} not found`)} />;
  if (details.data.installed && details.data.enabled) return <>{children}</>;

  const action = details.data.installed
    ? <button className="primary-button" onClick={() => enable.mutate()} disabled={enable.isPending}>Enable package</button>
    : <button className="primary-button" onClick={() => install.mutate()} disabled={install.isPending}>Install package</button>;

  return (
    <div className="page-stack package-gate-page">
      <section className="page-header enterprise-hero">
        <span className="eyebrow">Package Gate</span>
        <h1>{details.data.manifest.name}</h1>
        <p>{details.data.manifest.description}</p>
        <div className="hero-meta">{action}</div>
      </section>
      <SectionCard title="Activation required" description="Install and enable the package to open this workspace.">
        <div className="package-gate-panel">
          <p>This page needs the package to be installed and enabled. The gate prevents half-working screens and stale routes.</p>
          {(install.error || enable.error) && <div className="error-state compact">{((install.error ?? enable.error) as Error).message}</div>}
        </div>
      </SectionCard>
    </div>
  );
}
