import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { authApi, AUTH_STATE_QUERY_KEY } from '../../api/auth';
import { useT } from '../../i18n/useI18n';
import { useAuth } from './AuthGate';

export function UserMenu() {
  const t = useT();
  const auth = useAuth();
  const queryClient = useQueryClient();
  const user = auth?.data?.user;
  const logout = useMutation({
    mutationFn: authApi.logout,
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: AUTH_STATE_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: ['ui-navigation'] });
    },
  });

  if (!user) return null;
  return (
    <div className="user-menu">
      <span>{user.display_name || user.username}</span>
      <Link className="primary-link" to="/change-password">{t('auth.passwordMenu')}</Link>
      <Link className="primary-link" to="/users">{t('nav.users')}</Link>
      <button className="ghost-button" onClick={() => logout.mutate()} disabled={logout.isPending}>{t('auth.logout')}</button>
    </div>
  );
}
