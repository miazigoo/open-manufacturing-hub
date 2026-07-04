import { FormEvent, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi, AUTH_STATE_QUERY_KEY, type UserCreated } from '../../api/auth';
import { RecoveryKeysPanel } from './RecoveryKeysPanel';

export function BootstrapPage() {
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
          <span className="eyebrow">OMH Auth Package</span>
          <h1>First user created</h1>
          <p>User <strong>{created.username}</strong> can now sign in and create other users.</p>
          <RecoveryKeysPanel keys={created.recovery_keys} />
          <button className="primary-button" onClick={() => queryClient.invalidateQueries({ queryKey: AUTH_STATE_QUERY_KEY })}>Continue to login</button>
        </section>
      </main>
    );
  }

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <span className="eyebrow">OMH Auth Package</span>
        <h1>Bootstrap access</h1>
        <p>No users exist yet. Create the first local account once; public registration is disabled after this step.</p>
        <form className="auth-form" onSubmit={submit}>
          <label>Username<input value={username} onChange={(event) => setUsername(event.target.value)} required autoFocus /></label>
          <label>Display name<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
          <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
          <button className="primary-button" disabled={bootstrap.isPending}>Create first user</button>
        </form>
        {bootstrap.error instanceof Error && <div className="error-state compact">{bootstrap.error.message}</div>}
      </section>
    </main>
  );
}
