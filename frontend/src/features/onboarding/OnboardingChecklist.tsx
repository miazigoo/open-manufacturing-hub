import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { onboardingApi, type OnboardingItem } from '../../api/onboarding';
import { useI18n } from '../../i18n/useI18n';
import { itemCopy, onboardingCopy } from './copy';

export function OnboardingChecklist({ items }: { items: OnboardingItem[] }) {
  const queryClient = useQueryClient();
  const { language } = useI18n();
  const copy = onboardingCopy[language];
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['onboarding-state'] });
  const complete = useMutation({ mutationFn: (key: string) => onboardingApi.complete(key), onSuccess: invalidate });
  const skip = useMutation({ mutationFn: (key: string) => onboardingApi.skip(key), onSuccess: invalidate });

  return (
    <div className="onboarding-checklist">
      {items.map((item, index) => {
        const translated = itemCopy[item.key]?.[language] ?? { title: item.title, description: item.description };
        const done = item.completed || item.skipped;
        return (
          <article key={item.key} className={`onboarding-step-card ${done ? 'done' : ''}`}>
            <span className="step-index">{String(index + 1).padStart(2, '0')}</span>
            <div>
              <h3>{translated.title}</h3>
              <p>{translated.description}</p>
              <div className="action-row">
                {item.route && <Link className="primary-link" to={item.route}>{copy.open}</Link>}
                {item.docs_url && <Link className="ghost-link" to={item.docs_url}>{copy.docs}</Link>}
                <button className="ghost-button" type="button" disabled={complete.isPending || item.completed} onClick={() => complete.mutate(item.key)}>{item.completed ? copy.done : copy.complete}</button>
                <button className="ghost-button" type="button" disabled={skip.isPending || item.skipped} onClick={() => skip.mutate(item.key)}>{item.skipped ? copy.skipped : copy.skip}</button>
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}
