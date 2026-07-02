import { useQuery } from '@tanstack/react-query';
import { executionApi } from '../api/execution';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { useT } from '../i18n/useI18n';

export function ExecutionStepsPage() {
  const t = useT();
  const steps = useQuery({ queryKey: ['execution-steps'], queryFn: executionApi.steps });
  if (steps.isLoading) return <LoadingState label={t('execution.loading')} />;
  if (steps.error) return <ErrorState error={steps.error} />;

  return (
    <div className="page-stack">
      <section className="page-header execution-hero">
        <span className="eyebrow">{t('execution.eyebrow')}</span>
        <h1>{t('execution.title')}</h1>
        <p>{t('execution.subtitle')}</p>
      </section>
      <section className="table-panel">
        <div className="panel-toolbar"><h2>{t('execution.registry')}</h2><span className="microcopy">{t('execution.stepsCount', { count: steps.data?.length ?? 0 })}</span></div>
        <table>
          <thead><tr><th>{t('connectors.name')}</th><th>{t('execution.displayName')}</th><th>{t('execution.runtimeRole')}</th></tr></thead>
          <tbody>
            {(steps.data ?? []).map((step) => (
              <tr key={step.name}>
                <td className="mono">{step.name}</td>
                <td>{step.display_name}</td>
                <td><span className="status-badge info compact">{t('execution.registered')}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
