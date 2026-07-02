import { useT } from '../i18n/I18nProvider';

export function LoadingState({ label }: { label?: string }) {
  const t = useT();
  return (
    <div className="loading-state">
      <span className="loader-line" />
      <span>{label ?? t('common.loading')}</span>
    </div>
  );
}
