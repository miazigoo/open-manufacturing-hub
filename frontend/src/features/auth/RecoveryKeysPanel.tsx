import { useT } from '../../i18n/useI18n';

export function RecoveryKeysPanel({ keys }: { keys: string[] }) {
  const t = useT();
  if (!keys.length) return null;
  return (
    <div className="recovery-key-panel">
      <div>
        <span className="eyebrow">{t('auth.recoveryKeys')}</span>
        <h3>{t('auth.saveRecoveryKeys')}</h3>
        <p>{t('auth.recoveryKeysDetail')}</p>
      </div>
      <div className="recovery-key-grid">
        {keys.map((key) => <code key={key}>{key}</code>)}
      </div>
    </div>
  );
}
