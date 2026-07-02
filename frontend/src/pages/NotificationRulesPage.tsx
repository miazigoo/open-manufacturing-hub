import { FormEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { NotificationRulePayload, TriggerType, notificationsApi } from '../api/notifications';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

const triggerTypes: TriggerType[] = ['event_failed', 'incident_created', 'incident_updated', 'health_down', 'queue_threshold', 'daily_report'];

export function NotificationRulesPage() {
  const queryClient = useQueryClient();
  const rules = useQuery({ queryKey: ['notification-rules'], queryFn: notificationsApi.rules });
  const deliveries = useQuery({ queryKey: ['notification-deliveries'], queryFn: notificationsApi.deliveries });
  const [form, setForm] = useState({ name: '', trigger_type: 'incident_created' as TriggerType, cooldown_seconds: 600, filters: '{\n  "target_system": "Mock WMS",\n  "severity": "error"\n}', channels: '[\n  { "type": "email_stub", "to": "dev@example.com" }\n]' });
  const [formError, setFormError] = useState<string | null>(null);

  const createRule = useMutation({ mutationFn: notificationsApi.createRule, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['notification-rules'] }); setForm((current) => ({ ...current, name: '' })); } });
  const deleteRule = useMutation({ mutationFn: notificationsApi.deleteRule, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notification-rules'] }) });
  const testRule = useMutation({ mutationFn: notificationsApi.testRule, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notification-deliveries'] }) });

  function submit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    try {
      const payload: NotificationRulePayload = {
        name: form.name,
        trigger_type: form.trigger_type,
        cooldown_seconds: Number(form.cooldown_seconds),
        filters: JSON.parse(form.filters) as Record<string, unknown>,
        channels: JSON.parse(form.channels) as Array<Record<string, unknown>>,
        enabled: true,
      };
      createRule.mutate(payload);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Invalid JSON');
    }
  }

  const error = rules.error ?? deliveries.error;
  if (rules.isLoading || deliveries.isLoading) return <LoadingState label="Loading notification rules" />;
  if (error) return <ErrorState error={error} />;

  return (
    <div className="page-stack two-column-page">
      <section className="panel form-panel">
        <div className="panel-toolbar"><div><span className="eyebrow">Notifications</span><h1>Create alert rule</h1></div></div>
        <form onSubmit={submit} className="stack-form">
          <label className="field-label">Name<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required /></label>
          <label className="field-label">Trigger<select value={form.trigger_type} onChange={(event) => setForm({ ...form, trigger_type: event.target.value as TriggerType })}>{triggerTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select></label>
          <label className="field-label">Cooldown seconds<input type="number" value={form.cooldown_seconds} onChange={(event) => setForm({ ...form, cooldown_seconds: Number(event.target.value) })} /></label>
          <label className="field-label">Filters JSON<textarea value={form.filters} onChange={(event) => setForm({ ...form, filters: event.target.value })} spellCheck={false} /></label>
          <label className="field-label">Channels JSON<textarea value={form.channels} onChange={(event) => setForm({ ...form, channels: event.target.value })} spellCheck={false} /></label>
          {formError && <div className="error-state compact">{formError}</div>}
          <button className="primary-button" type="submit" disabled={createRule.isPending}>Create rule</button>
        </form>
      </section>
      <section className="panel">
        <div className="panel-toolbar"><h2>Rules</h2></div>
        {rules.data?.length ? rules.data.map((rule) => (
          <article className="rule-card" key={rule.id}>
            <div><h3>{rule.name}</h3><span className="microcopy">{rule.trigger_type} · cooldown {rule.cooldown_seconds}s</span></div>
            <StatusBadge status={rule.enabled ? 'ok' : 'unknown'} label={rule.enabled ? 'enabled' : 'disabled'} />
            <JsonBlock value={{ filters: rule.filters_json, channels: rule.channels_json }} searchable={false} />
            <div className="action-row"><button className="ghost-button" onClick={() => testRule.mutate(rule.id)}>Test</button><button className="ghost-button danger" onClick={() => deleteRule.mutate(rule.id)}>Delete</button></div>
          </article>
        )) : <EmptyState title="No notification rules configured" detail="Create a rule to turn incidents and health events into delivery logs." />}
      </section>
      <section className="panel full-span">
        <div className="panel-toolbar"><h2>Delivery log</h2></div>
        {deliveries.data?.length ? <div className="component-list">{deliveries.data.map((delivery) => <div key={delivery.id}><strong>{delivery.target_channel}</strong><span>{delivery.target_address}</span><StatusBadge status={delivery.status} /></div>)}</div> : <EmptyState title="No deliveries yet" detail="Test a rule or trigger an incident to create delivery entries." />}
      </section>
    </div>
  );
}
