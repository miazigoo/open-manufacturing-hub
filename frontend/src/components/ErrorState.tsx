import { useT } from '../i18n/useI18n';

export function ErrorState({ error }: { error: unknown }) {
  const t = useT();
  const message = error instanceof Error ? error.message : t('common.unknownError');
  return (
    <div className="error-state">
      <strong>{t('common.requestFailed')}</strong>
      <span>{message}</span>
    </div>
  );
}
