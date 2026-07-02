import { FormEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { maintenanceApi } from '../api/maintenance';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

function localInputDate(offsetHours: number) {
  const date = new Date(Date.now() + offsetHours * 60 * 60 * 1000);
  return date.toISOString().slice(0, 16);
}

export function MaintenancePage() {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ['maintenance'], queryFn: maintenanceApi.list });
  const [form, setForm] = useState({ component_type: 'connector', component_name: 'Mock WMS', reason: 'Planned WMS update', starts_at: localInputDate(0), ends_at: localInputDate(2), enabled: true });
  const create = useMutation({ mutationFn: maintenanceApi.create, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['maintenance'] }) });
  const remove = useMutation({ mutationFn: maintenanceApi.delete, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['maintenance'] }) });

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate({ ...form, starts_at: new Date(form.starts_at).toISOString(), ends_at: new Date(form.ends_at).toISOString() });
  }

  if (query.isLoading) return <LoadingState label="Loading maintenance windows" />;
  if (query.error) return <ErrorState error={query.error} />;

  return (
    <div className="page-stack two-column-page">
      <section className="panel form-panel">
        <span className="eyebrow">Maintenance Mode</span><h1>Plan downtime without false incidents.</h1>
        <form onSubmit={submit} className="stack-form">
          <label className="field-label">Component type<input value={form.component_type} onChange={(event) => setForm({ ...form, component_type: event.target.value })} /></label>
          <label className="field-label">Component name<input value={form.component_name} onChange={(event) => setForm({ ...form, component_name: event.target.value })} /></label>
          <label className="field-label">Reason<input value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} /></label>
          <label className="field-label">Starts<input type="datetime-local" value={form.starts_at} onChange={(event) => setForm({ ...form, starts_at: event.target.value })} /></label>
          <label className="field-label">Ends<input type="datetime-local" value={form.ends_at} onChange={(event) => setForm({ ...form, ends_at: event.target.value })} /></label>
          <label className="check-row"><input type="checkbox" checked={form.enabled} onChange={(event) => setForm({ ...form, enabled: event.target.checked })} /> Enabled</label>
          <button className="primary-button">Create window</button>
        </form>
      </section>
      <section className="panel">
        <div className="panel-toolbar"><h2>Windows</h2></div>
        {query.data?.length ? query.data.map((window) => (
          <article className="maintenance-card" key={window.id}>
            <div><h3>{window.component_name}</h3><p>{window.reason ?? 'Maintenance window'}</p></div>
            <StatusBadge status={window.enabled ? 'maintenance' : 'unknown'} label={window.enabled ? `until ${new Date(window.ends_at).toLocaleTimeString()}` : 'disabled'} />
            <div className="metadata-grid compact-grid"><span>Starts<strong>{new Date(window.starts_at).toLocaleString()}</strong></span><span>Ends<strong>{new Date(window.ends_at).toLocaleString()}</strong></span></div>
            <p className="microcopy">Events will move to retry_waiting instead of failed while this window is active.</p>
            <button className="ghost-button danger" onClick={() => remove.mutate(window.id)}>Delete</button>
          </article>
        )) : <EmptyState title="No maintenance windows" detail="Create one before planned downtime to suppress false incidents." />}
      </section>
    </div>
  );
}
