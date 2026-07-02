import { useT } from '../i18n/useI18n';

export function LoadingState({ label }: { label?: string }) {
  const t = useT();
  return (
    <div className="loading-state">
      <span className="loader-line" />
      <span>{label ?? t('common.loading')}</span>
    </div>
  );
}
