import { FormEvent, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi, AUTH_STATE_QUERY_KEY } from '../../api/auth';

export function ChangePasswordPage() {
  const queryClient = useQueryClient();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const change = useMutation({
    mutationFn: () => authApi.changePassword({ current_password: currentPassword, new_password: newPassword }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: AUTH_STATE_QUERY_KEY }),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    change.mutate();
  }

  return (
    <div className="page-stack auth-admin-page">
      <section className="page-header auth-admin-hero">
        <span className="eyebrow">Account</span>
        <h1>Change password</h1>
        <p>Weak passwords are allowed by product decision. Existing sessions are revoked after password change.</p>
      </section>
      <form className="panel auth-create-panel" onSubmit={submit}>
        <label>Current password<input type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></label>
        <label>New password<input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required /></label>
        <button className="primary-button" disabled={change.isPending}>Change password</button>
        {change.error instanceof Error && <div className="error-state compact">{change.error.message}</div>}
      </form>
    </div>
  );
}
