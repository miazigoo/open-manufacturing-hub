import { FormEvent, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi, AUTH_STATE_QUERY_KEY } from '../../api/auth';
import { useT } from '../../i18n/useI18n';

export function LoginPage() {
  const t = useT();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<'login' | 'recover'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [recoveryKey, setRecoveryKey] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [recovered, setRecovered] = useState(false);
  const login = useMutation({
    mutationFn: () => authApi.login({ username, password }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: AUTH_STATE_QUERY_KEY }),
  });
  const recover = useMutation({
    mutationFn: () => authApi.recoverPassword({ username, recovery_key: recoveryKey, new_password: newPassword }),
    onSuccess: () => {
      setRecovered(true);
      setMode('login');
      setPassword('');
      setRecoveryKey('');
      setNewPassword('');
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (mode === 'login') login.mutate();
    else recover.mutate();
  }

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <span className="eyebrow">{t('auth.protectedWorkspace')}</span>
        <h1>{mode === 'login' ? t('auth.signIn') : t('auth.resetPassword')}</h1>
        <p>{mode === 'login' ? t('auth.loginDescription') : t('auth.recoverDescription')}</p>
        {recovered && <div className="success-note"><strong>{t('auth.passwordChanged')}</strong><span>{t('auth.signInNewPassword')}</span></div>}
        <form className="auth-form" onSubmit={submit}>
          <label>{t('auth.username')}<input value={username} onChange={(event) => setUsername(event.target.value)} required autoFocus /></label>
          {mode === 'login' ? <label>{t('auth.password')}<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label> : <><label>{t('auth.recoveryKey')}<input value={recoveryKey} onChange={(event) => setRecoveryKey(event.target.value)} required /></label><label>{t('auth.newPassword')}<input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required /></label></>}
          <button className="primary-button" disabled={login.isPending || recover.isPending}>{mode === 'login' ? t('auth.signInAction') : t('auth.resetPasswordAction')}</button>
        </form>
        <button className="primary-link text-button" onClick={() => setMode(mode === 'login' ? 'recover' : 'login')}>{mode === 'login' ? t('auth.forgot') : t('auth.backToSignIn')}</button>
        {[login.error, recover.error].find(Boolean) instanceof Error && <div className="error-state compact">{(([login.error, recover.error].find(Boolean)) as Error).message}</div>}
      </section>
    </main>
  );
}
