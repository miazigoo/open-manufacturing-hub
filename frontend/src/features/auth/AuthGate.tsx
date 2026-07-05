import { createContext, type ReactNode, useContext } from 'react';
import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { authApi, AUTH_STATE_QUERY_KEY, type AuthState } from '../../api/auth';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { useT } from '../../i18n/useI18n';
import { BootstrapPage } from './BootstrapPage';
import { LoginPage } from './LoginPage';

const AuthContext = createContext<UseQueryResult<AuthState> | null>(null);

export function AuthGate({ children }: { children: ReactNode }) {
  const t = useT();
  const state = useQuery({ queryKey: AUTH_STATE_QUERY_KEY, queryFn: authApi.state, retry: 1 });

  if (state.isLoading) return <LoadingState label={t('auth.checkingAccess')} />;
  if (state.error) return <ErrorState error={state.error} />;

  const value = state.data;
  const needsLogin = Boolean(value?.auth_available && value.auth_enabled && value.requires_login);

  return (
    <AuthContext.Provider value={state}>
      {!needsLogin || value?.user ? children : value?.bootstrap_required ? <BootstrapPage /> : <LoginPage />}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
