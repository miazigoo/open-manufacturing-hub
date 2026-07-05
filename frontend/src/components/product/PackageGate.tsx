import type { ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { packagesApi } from '../../api/packages';
import { useT } from '../../i18n/useI18n';
import { ErrorState } from '../ErrorState';
import { LoadingState } from '../LoadingState';
import { StatusBadge } from '../StatusBadge';
import { SectionCard } from './SectionCard';

interface PackageGateProps {
  packageId: string;
  children: ReactNode;
}

export function PackageGate({ packageId, children }: PackageGateProps) {
  const t = useT();
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

  if (details.isLoading) return <LoadingState label={t('packages.checkingState')} />;
  if (details.error) return <ErrorState error={details.error} />;
  if (!details.data) return <ErrorState error={new Error(t('packages.notFound', { packageId }))} />;
  if (details.data.installed && details.data.enabled) return <>{children}</>;

  const manifest = details.data.manifest;
  const status = details.data.installed ? 'disabled' : manifest.status;
  const canInstall = !details.data.installed && manifest.installable && details.data.compatible;
  const canEnable = details.data.installed && !details.data.enabled;
  const action = canEnable ? (
    <button className="primary-button" onClick={() => enable.mutate()} disabled={enable.isPending}>{t('packages.enablePackage')}</button>
  ) : canInstall ? (
    <button className="primary-button" onClick={() => install.mutate()} disabled={install.isPending}>{t('packages.installPackage')}</button>
  ) : (
    <button className="ghost-button" type="button" disabled>{lockedActionLabel(status, t)}</button>
  );

  return (
    <div className="page-stack package-gate-page">
      <section className="page-header enterprise-hero">
        <span className="eyebrow">{t('packages.gate')}</span>
        <h1>{manifest.name}</h1>
        <p>{manifest.description}</p>
        <div className="hero-meta"><StatusBadge status={status} />{action}</div>
      </section>
      <SectionCard title={gateTitle(status, details.data.installed, t)} description={gateDescription(status, details.data.installed, t)}>
        <div className="package-gate-panel">
          <p>{manifest.reason_unavailable || t('packages.gateDefaultReason')}</p>
          {!details.data.compatible && <div className="error-state compact">{[...details.data.compatibility_errors, ...details.data.dependency_errors].join('; ')}</div>}
          {(install.error || enable.error) && <div className="error-state compact">{((install.error ?? enable.error) as Error).message}</div>}
        </div>
      </SectionCard>
    </div>
  );
}

function lockedActionLabel(status: string, t: (key: string) => string) {
  if (status === 'coming_soon') return t('statuses.coming_soon');
  if (status === 'in_development') return t('statuses.in_development');
  if (status === 'incompatible') return t('statuses.incompatible');
  return t('packages.notInstallable');
}

function gateTitle(status: string, installed: boolean, t: (key: string) => string) {
  if (installed) return t('packages.gateDisabledTitle');
  if (status === 'coming_soon') return t('packages.gateComingSoonTitle');
  if (status === 'in_development') return t('packages.gateDevelopmentTitle');
  if (status === 'incompatible') return t('packages.gateIncompatibleTitle');
  return t('packages.gateInstallRequiredTitle');
}

function gateDescription(status: string, installed: boolean, t: (key: string) => string) {
  if (installed) return t('packages.gateDisabledDescription');
  if (status === 'coming_soon') return t('packages.gateComingSoonDescription');
  if (status === 'in_development') return t('packages.gateDevelopmentDescription');
  if (status === 'incompatible') return t('packages.gateIncompatibleDescription');
  return t('packages.gateInstallRequiredDescription');
}
