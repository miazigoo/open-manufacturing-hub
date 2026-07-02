import { FormEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { maintenanceApi } from '../api/maintenance';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { useT } from '../i18n/I18nProvider';

function localInputDate(offsetHours: number) {
  const date = new Date(Date.now() + offsetHours * 60 * 60 * 1000);
  return date.toISOString().slice(0, 16);
}

export function MaintenancePage() {
  const t = useT();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ['maintenance'], queryFn: maintenanceApi.list });
  const [form, setForm] = useState({ component_type: 'connector', component_name: 'Mock WMS', reason: 'Planned WMS update', starts_at: localInputDate(0), ends_at: localInputDate(2), enabled: true });
  const create = useMutation({ mutationFn: maintenanceApi.create, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['maintenance'] }) });
  const remove = useMutation({ mutationFn: maintenanceApi.delete, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['maintenance'] }) });

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate({ ...form, starts_at: new Date(form.starts_at).toISOString(), ends_at: new Date(form.ends_at).toISOString() });
  }

  if (query.isLoading) return <LoadingState label={t('maintenance.loading')} />;
  if (query.error) return <ErrorState error={query.error} />;

  return (
    <div className="page-stack two-column-page">
      <section className="panel form-panel">
        <span className="eyebrow">{t('maintenance.eyebrow')}</span><h1>{t('maintenance.title')}</h1>
        <form onSubmit={submit} className="stack-form">
          <label className="field-label">{t('maintenance.componentType')}<input value={form.component_type} onChange={(event) => setForm({ ...form, component_type: event.target.value })} /></label>
          <label className="field-label">{t('maintenance.componentName')}<input value={form.component_name} onChange={(event) => setForm({ ...form, component_name: event.target.value })} /></label>
          <label className="field-label">{t('maintenance.reason')}<input value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} /></label>
          <label className="field-label">{t('maintenance.starts')}<input type="datetime-local" value={form.starts_at} onChange={(event) => setForm({ ...form, starts_at: event.target.value })} /></label>
          <label className="field-label">{t('maintenance.ends')}<input type="datetime-local" value={form.ends_at} onChange={(event) => setForm({ ...form, ends_at: event.target.value })} /></label>
          <label className="check-row"><input type="checkbox" checked={form.enabled} onChange={(event) => setForm({ ...form, enabled: event.target.checked })} /> {t('maintenance.enabled')}</label>
          <button className="primary-button">{t('maintenance.create')}</button>
        </form>
      </section>
      <section className="panel">
        <div className="panel-toolbar"><h2>{t('maintenance.windows')}</h2></div>
        {query.data?.length ? query.data.map((window) => (
          <article className="maintenance-card" key={window.id}>
            <div><h3>{window.component_name}</h3><p>{window.reason ?? 'Maintenance window'}</p></div>
            <StatusBadge status={window.enabled ? 'maintenance' : 'unknown'} label={window.enabled ? t('maintenance.until', { value: new Date(window.ends_at).toLocaleTimeString() }) : t('connectors.disabled')} />
            <div className="metadata-grid compact-grid"><span>{t('maintenance.starts')}<strong>{new Date(window.starts_at).toLocaleString()}</strong></span><span>{t('maintenance.ends')}<strong>{new Date(window.ends_at).toLocaleString()}</strong></span></div>
            <p className="microcopy">{t('maintenance.effect')}</p>
            <button className="ghost-button danger" onClick={() => remove.mutate(window.id)}>{t('connectors.delete')}</button>
          </article>
        )) : <EmptyState title={t('maintenance.noWindows')} detail={t('maintenance.noWindowsDetail')} />}
      </section>
    </div>
  );
}
