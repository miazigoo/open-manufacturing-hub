import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { onboardingApi } from '../../api/onboarding';
import { useI18n } from '../../i18n/useI18n';
import { onboardingCopy } from './copy';

export function ExampleRunnerButton({ exampleId }: { exampleId: string }) {
  const queryClient = useQueryClient();
  const { language } = useI18n();
  const copy = onboardingCopy[language];
  const run = useMutation({ mutationFn: () => onboardingApi.runExample(exampleId), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['onboarding-state'] }); queryClient.invalidateQueries({ queryKey: ['events'] }); } });
  return (
    <div className="example-runner">
      <button type="button" className="primary-button" onClick={() => run.mutate()} disabled={run.isPending}>{copy.runExample}</button>
      {run.data && <Link className="primary-link" to={run.data.timeline_url}>Timeline</Link>}
      {run.error instanceof Error && <span className="error-state compact">{run.error.message}</span>}
    </div>
  );
}
