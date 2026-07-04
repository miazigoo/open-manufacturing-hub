import { FormEvent, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi, AUTH_STATE_QUERY_KEY } from '../../api/auth';

export function LoginPage() {
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
        <span className="eyebrow">Protected workspace</span>
        <h1>{mode === 'login' ? 'Sign in to OMH' : 'Reset password'}</h1>
        <p>{mode === 'login' ? 'Auth Package is enabled. Local users can access the web UI.' : 'Use one of your one-time recovery keys. After reset, sign in with the new password.'}</p>
        {recovered && <div className="success-note"><strong>Password changed.</strong><span>Sign in with the new password.</span></div>}
        <form className="auth-form" onSubmit={submit}>
          <label>Username<input value={username} onChange={(event) => setUsername(event.target.value)} required autoFocus /></label>
          {mode === 'login' ? <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label> : <><label>Recovery key<input value={recoveryKey} onChange={(event) => setRecoveryKey(event.target.value)} required /></label><label>New password<input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required /></label></>}
          <button className="primary-button" disabled={login.isPending || recover.isPending}>{mode === 'login' ? 'Sign in' : 'Reset password'}</button>
        </form>
        <button className="primary-link text-button" onClick={() => setMode(mode === 'login' ? 'recover' : 'login')}>{mode === 'login' ? 'Forgot password? Use recovery key' : 'Back to sign in'}</button>
        {[login.error, recover.error].find(Boolean) instanceof Error && <div className="error-state compact">{(([login.error, recover.error].find(Boolean)) as Error).message}</div>}
      </section>
    </main>
  );
}
