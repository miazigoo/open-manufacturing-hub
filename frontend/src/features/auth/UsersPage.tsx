import { FormEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { authApi, type UserCreated } from '../../api/auth';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { StatusBadge } from '../../components/StatusBadge';
import { RecoveryKeysPanel } from './RecoveryKeysPanel';

export function UsersPage() {
  const queryClient = useQueryClient();
  const users = useQuery({ queryKey: ['auth-users'], queryFn: authApi.users });
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [keys, setKeys] = useState<UserCreated | null>(null);
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['auth-users'] });
  const create = useMutation({
    mutationFn: () => authApi.createUser({ username, display_name: displayName || null, password }),
    onSuccess: (data) => {
      setKeys(data);
      setUsername('');
      setDisplayName('');
      setPassword('');
      refresh();
    },
  });
  const enable = useMutation({ mutationFn: authApi.enableUser, onSuccess: refresh });
  const disable = useMutation({ mutationFn: authApi.disableUser, onSuccess: refresh });
  const resetKeys = useMutation({
    mutationFn: authApi.resetRecoveryKeys,
    onSuccess: (data, userId) => {
      const user = users.data?.find((item) => item.id === userId);
      setKeys({ id: userId, username: user?.username ?? 'user', display_name: user?.display_name ?? null, recovery_keys: data.recovery_keys });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }

  if (users.isLoading) return <LoadingState label="Loading users" />;
  if (users.error) return <ErrorState error={users.error} />;

  return (
    <div className="page-stack auth-admin-page">
      <section className="page-header auth-admin-hero product-page-header">
        <div>
          <span className="eyebrow">Security</span>
          <h1>Local users</h1>
          <p>Any enabled user can sign in and work with the full OMH web UI. Roles are intentionally not part of v1.</p>
        </div>
      </section>
      <section className="auth-admin-grid">
        <form className="panel auth-create-panel" onSubmit={submit}>
          <div className="panel-toolbar"><h2>Create user</h2><span className="microcopy">5 recovery keys</span></div>
          <label>Username<input value={username} onChange={(event) => setUsername(event.target.value)} required /></label>
          <label>Display name<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
          <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
          <button className="primary-button" disabled={create.isPending}>Create user</button>
          {create.error instanceof Error && <div className="error-state compact">{create.error.message}</div>}
        </form>
        <RecoveryKeysPanel keys={keys?.recovery_keys ?? []} />
      </section>
      <section className="panel table-panel">
        <div className="panel-toolbar"><h2>Users</h2><span className="microcopy">{users.data?.length ?? 0}</span></div>
        {(users.data ?? []).length === 0 ? <EmptyState title="No users" detail="Create the first account." /> : <table><thead><tr><th>User</th><th>Status</th><th>Last login</th><th>Actions</th></tr></thead><tbody>{users.data?.map((user) => <tr key={user.id}><td><strong>{user.display_name || user.username}</strong><small>{user.username}</small></td><td><StatusBadge status={user.enabled ? 'ok' : 'cancelled'} label={user.enabled ? 'enabled' : 'disabled'} compact /></td><td>{user.last_login_at ? new Date(user.last_login_at).toLocaleString() : 'never'}</td><td><div className="action-row wrap-actions">{user.enabled ? <button className="ghost-button" onClick={() => disable.mutate(user.id)}>Disable</button> : <button className="primary-button" onClick={() => enable.mutate(user.id)}>Enable</button>}<button className="ghost-button" onClick={() => resetKeys.mutate(user.id)}>Reset recovery keys</button></div></td></tr>)}</tbody></table>}
      </section>
      {[enable.error, disable.error, resetKeys.error].find(Boolean) instanceof Error && <div className="error-state compact">{(([enable.error, disable.error, resetKeys.error].find(Boolean)) as Error).message}</div>}
    </div>
  );
}
