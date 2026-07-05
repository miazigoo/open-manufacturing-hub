import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { onboardingApi } from '../../api/onboarding';
import { useI18n } from '../../i18n/useI18n';
import { onboardingCopy } from './copy';

export function OnboardingCard() {
  const { language } = useI18n();
  const copy = onboardingCopy[language];
  const state = useQuery({ queryKey: ['onboarding-state'], queryFn: onboardingApi.state });
  if (state.isLoading || state.error || state.data?.setup_done) return null;
  const total = state.data?.total_count ?? 0;
  const done = state.data?.completed_count ?? 0;
  return (
    <section className="panel onboarding-card">
      <div>
        <span className="eyebrow">{copy.onboarding}</span>
        <h2>{copy.cardTitle}</h2>
        <p>{copy.cardText}</p>
      </div>
      <div className="onboarding-progress"><strong>{done}/{total}</strong><span>{copy.progress}</span></div>
      <div className="action-row"><Link className="primary-button" to="/onboarding">{copy.open}</Link><Link className="ghost-button" to="/onboarding/first-integration">{copy.openWizard}</Link></div>
    </section>
  );
}
