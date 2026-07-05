import { FormEvent, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi, AUTH_STATE_QUERY_KEY, type UserCreated } from '../../api/auth';
import { useT } from '../../i18n/useI18n';
import { RecoveryKeysPanel } from './RecoveryKeysPanel';

export function BootstrapPage() {
  const t = useT();
  const queryClient = useQueryClient();
  const [username, setUsername] = useState('admin');
  const [displayName, setDisplayName] = useState('Administrator');
  const [password, setPassword] = useState('admin');
  const [created, setCreated] = useState<UserCreated | null>(null);
  const bootstrap = useMutation({
    mutationFn: () => authApi.bootstrap({ username, display_name: displayName || null, password }),
    onSuccess: (data) => {
      setCreated(data);
      queryClient.invalidateQueries({ queryKey: AUTH_STATE_QUERY_KEY });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    bootstrap.mutate();
  }

  if (created) {
    return (
      <main className="auth-shell">
        <section className="auth-card wide-auth-card">
          <span className="eyebrow">{t('auth.package')}</span>
          <h1>{t('auth.firstUserCreated')}</h1>
          <p>{t('auth.firstUserCreatedDetail', { username: created.username })}</p>
          <RecoveryKeysPanel keys={created.recovery_keys} />
          <button className="primary-button" onClick={() => queryClient.invalidateQueries({ queryKey: AUTH_STATE_QUERY_KEY })}>{t('auth.continueToLogin')}</button>
        </section>
      </main>
    );
  }

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <span className="eyebrow">{t('auth.package')}</span>
        <h1>{t('auth.bootstrapAccess')}</h1>
        <p>{t('auth.bootstrapDetail')}</p>
        <form className="auth-form" onSubmit={submit}>
          <label>{t('auth.username')}<input value={username} onChange={(event) => setUsername(event.target.value)} required autoFocus /></label>
          <label>{t('auth.displayName')}<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
          <label>{t('auth.password')}<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
          <button className="primary-button" disabled={bootstrap.isPending}>{t('auth.createFirstUser')}</button>
        </form>
        {bootstrap.error instanceof Error && <div className="error-state compact">{bootstrap.error.message}</div>}
      </section>
    </main>
  );
}
