import { FormEvent, useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { authApi, AUTH_STATE_QUERY_KEY } from '../../api/auth';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';

export function AuthSettingsPage() {
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ['auth-settings'], queryFn: authApi.settings });
  const [enabled, setEnabled] = useState(true);
  const [protectApi, setProtectApi] = useState(true);
  const [protectUi, setProtectUi] = useState(true);
  const [ttl, setTtl] = useState(30);
  const [cookieName, setCookieName] = useState('omh_session');
  const save = useMutation({
    mutationFn: () => authApi.updateSettings({ enabled, protect_api: protectApi, protect_ui: protectUi, session_ttl_days: ttl, cookie_name: cookieName }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth-settings'] });
      queryClient.invalidateQueries({ queryKey: AUTH_STATE_QUERY_KEY });
    },
  });

  useEffect(() => {
    if (!settings.data) return;
    setEnabled(settings.data.enabled);
    setProtectApi(settings.data.protect_api);
    setProtectUi(settings.data.protect_ui);
    setTtl(settings.data.session_ttl_days);
    setCookieName(settings.data.cookie_name);
  }, [settings.data]);

  function submit(event: FormEvent) {
    event.preventDefault();
    save.mutate();
  }

  if (settings.isLoading) return <LoadingState label="Loading auth settings" />;
  if (settings.error) return <ErrorState error={settings.error} />;

  return (
    <div className="page-stack auth-admin-page">
      <section className="page-header auth-admin-hero product-page-header">
        <div>
          <span className="eyebrow">Security package</span>
          <h1>Auth settings</h1>
          <p>These settings protect the web UI and configuration API. Integration inbound endpoints keep their own endpoint auth.</p>
        </div>
      </section>
      <form className="panel auth-settings-panel" onSubmit={submit}>
        <label className="toggle-row"><input type="checkbox" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} /><span><strong>Enable auth package enforcement</strong><small>When off, OMH behaves as before.</small></span></label>
        <label className="toggle-row"><input type="checkbox" checked={protectUi} onChange={(event) => setProtectUi(event.target.checked)} /><span><strong>Require login for UI</strong><small>Frontend startup shows login/bootstrap pages.</small></span></label>
        <label className="toggle-row"><input type="checkbox" checked={protectApi} onChange={(event) => setProtectApi(event.target.checked)} /><span><strong>Protect configuration API</strong><small>Does not protect /api/bus/in/* and webhook endpoints.</small></span></label>
        <div className="form-grid form-grid-2">
          <label>Session TTL days<input type="number" min="1" value={ttl} onChange={(event) => setTtl(Number(event.target.value))} /></label>
          <label>Cookie name<input value={cookieName} onChange={(event) => setCookieName(event.target.value)} /></label>
        </div>
        <button className="primary-button" disabled={save.isPending}>Save settings</button>
        {save.error instanceof Error && <div className="error-state compact">{save.error.message}</div>}
      </form>
    </div>
  );
}
