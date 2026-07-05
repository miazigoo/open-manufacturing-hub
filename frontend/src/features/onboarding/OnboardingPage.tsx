import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { onboardingApi } from '../../api/onboarding';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { useI18n } from '../../i18n/useI18n';
import { ExampleRunnerButton } from './ExampleRunnerButton';
import { OnboardingChecklist } from './OnboardingChecklist';
import { onboardingCopy } from './copy';

export function OnboardingPage() {
  const queryClient = useQueryClient();
  const { language } = useI18n();
  const copy = onboardingCopy[language];
  const state = useQuery({ queryKey: ['onboarding-state'], queryFn: onboardingApi.state });
  const reset = useMutation({ mutationFn: () => onboardingApi.reset(), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['onboarding-state'] }) });
  if (state.isLoading) return <LoadingState label="Loading onboarding" />;
  if (state.error) return <ErrorState error={state.error} />;
  const progress = state.data ? Math.round((state.data.completed_count / Math.max(1, state.data.total_count)) * 100) : 0;
  return (
    <div className="page-stack onboarding-page">
      <section className="hero-panel onboarding-hero product-page-header">
        <div>
          <span className="eyebrow">{copy.onboarding}</span>
          <h1>{copy.welcome}</h1>
          <p>{copy.subtitle}</p>
          <div className="hero-meta"><Link className="primary-button" to="/onboarding/first-integration">{copy.openWizard}</Link><button className="ghost-button" onClick={() => reset.mutate()} disabled={reset.isPending}>{copy.reset}</button></div>
        </div>
        <div className="onboarding-score"><strong>{progress}%</strong><span>{copy.progress}</span></div>
      </section>
      <section className="onboarding-grid">
        <section className="panel">
          <div className="panel-toolbar"><h2>{copy.recommended}</h2><span className="microcopy">{state.data?.completed_count}/{state.data?.total_count}</span></div>
          <OnboardingChecklist items={state.data?.items ?? []} />
        </section>
        <aside className="panel onboarding-sidecar">
          <span className="eyebrow">Examples</span>
          <h2>Run safe examples</h2>
          <p>Examples create real OMH events and open timeline without touching external systems.</p>
          <ExampleRunnerButton exampleId="onec_odata_lookup" />
          <ExampleRunnerButton exampleId="onec_post_to_api" />
          <ExampleRunnerButton exampleId="xml_raw_bridge" />
          <ExampleRunnerButton exampleId="printer_print_batch" />
        </aside>
      </section>
    </div>
  );
}
