import { request } from './client';

export interface AuthUser {
  id: string;
  username: string;
  display_name: string | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
  password_changed_at: string | null;
}

export interface AuthSession {
  id: string;
  user_id: string;
  created_at: string;
  expires_at: string;
  last_seen_at: string | null;
  revoked_at: string | null;
  user_agent: string | null;
  ip_address: string | null;
}

export interface AuthSettings {
  enabled: boolean;
  protect_api: boolean;
  protect_ui: boolean;
  session_ttl_days: number;
  cookie_name: string;
}

export interface AuthState {
  auth_available: boolean;
  auth_enabled: boolean;
  requires_login: boolean;
  bootstrap_required: boolean;
  user: AuthUser | null;
}

export interface UserCreated {
  id: string;
  username: string;
  display_name: string | null;
  recovery_keys: string[];
}

export interface UserCreatePayload {
  username: string;
  display_name?: string | null;
  password: string;
}

export interface UserPatchPayload {
  username?: string;
  display_name?: string | null;
  enabled?: boolean;
}

export const AUTH_STATE_QUERY_KEY = ['auth-state'] as const;

export const authApi = {
  state: () => request<AuthState>('/api/auth/state'),
  bootstrap: (payload: UserCreatePayload) => request<UserCreated>('/api/auth/bootstrap', { method: 'POST', body: JSON.stringify(payload) }),
  login: (payload: { username: string; password: string }) => request<AuthUser>('/api/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  logout: () => request<void>('/api/auth/logout', { method: 'POST' }),
  recoverPassword: (payload: { username: string; recovery_key: string; new_password: string }) => request<void>('/api/auth/recover-password', { method: 'POST', body: JSON.stringify(payload) }),
  me: () => request<AuthUser>('/api/auth/me'),
  changePassword: (payload: { current_password: string; new_password: string }) => request<void>('/api/auth/change-password', { method: 'POST', body: JSON.stringify(payload) }),
  users: () => request<AuthUser[]>('/api/auth/users'),
  createUser: (payload: UserCreatePayload) => request<UserCreated>('/api/auth/users', { method: 'POST', body: JSON.stringify(payload) }),
  patchUser: (userId: string, payload: UserPatchPayload) => request<AuthUser>(`/api/auth/users/${userId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  enableUser: (userId: string) => request<AuthUser>(`/api/auth/users/${userId}/enable`, { method: 'POST' }),
  disableUser: (userId: string) => request<AuthUser>(`/api/auth/users/${userId}/disable`, { method: 'POST' }),
  resetRecoveryKeys: (userId: string) => request<{ recovery_keys: string[] }>(`/api/auth/users/${userId}/reset-recovery-keys`, { method: 'POST' }),
  sessions: () => request<AuthSession[]>('/api/auth/sessions'),
  revokeSession: (sessionId: string) => request<void>(`/api/auth/sessions/${sessionId}/revoke`, { method: 'POST' }),
  settings: () => request<AuthSettings>('/api/auth/settings'),
  updateSettings: (payload: Partial<AuthSettings>) => request<AuthSettings>('/api/auth/settings', { method: 'PATCH', body: JSON.stringify(payload) }),
};
