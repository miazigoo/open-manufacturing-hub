import { FormEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { NotificationRulePayload, TriggerType, notificationsApi } from '../api/notifications';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { useT } from '../i18n/useI18n';

const triggerTypes: TriggerType[] = ['event_failed', 'incident_created', 'incident_updated', 'health_down', 'queue_threshold', 'queue_item_dlq', 'queue_backlog_threshold', 'worker_stuck', 'retry_exhausted', 'daily_report'];

export function NotificationRulesPage() {
  const t = useT();
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
  if (rules.isLoading || deliveries.isLoading) return <LoadingState label={t('notifications.loading')} />;
  if (error) return <ErrorState error={error} />;

  return (
    <div className="page-stack notification-page">
      <section className="panel form-panel notification-create-panel">
        <div className="panel-toolbar"><div><span className="eyebrow">{t('notifications.eyebrow')}</span><h1>{t('notifications.title')}</h1></div></div>
        <form onSubmit={submit} className="stack-form">
          <label className="field-label">{t('connectors.name')}<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required /></label>
          <label className="field-label">{t('notifications.trigger')}<select value={form.trigger_type} onChange={(event) => setForm({ ...form, trigger_type: event.target.value as TriggerType })}>{triggerTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select></label>
          <label className="field-label">{t('notifications.cooldown')}<input type="number" value={form.cooldown_seconds} onChange={(event) => setForm({ ...form, cooldown_seconds: Number(event.target.value) })} /></label>
          <label className="field-label">{t('notifications.filtersJson')}<textarea value={form.filters} onChange={(event) => setForm({ ...form, filters: event.target.value })} spellCheck={false} /></label>
          <label className="field-label">{t('notifications.channelsJson')}<textarea value={form.channels} onChange={(event) => setForm({ ...form, channels: event.target.value })} spellCheck={false} /></label>
          {formError && <div className="error-state compact">{formError}</div>}
          <button className="primary-button" type="submit" disabled={createRule.isPending}>{t('notifications.create')}</button>
        </form>
      </section>
      <section className="panel notification-rules-panel">
        <div className="panel-toolbar"><h2>{t('notifications.rules')}</h2></div>
        {rules.data?.length ? rules.data.map((rule) => (
          <article className="rule-card" key={rule.id}>
            <div><h3>{rule.name}</h3><span className="microcopy">{rule.trigger_type} · cooldown {rule.cooldown_seconds}s</span></div>
            <StatusBadge status={rule.enabled ? 'ok' : 'unknown'} label={rule.enabled ? t('connectors.enabled') : t('connectors.disabled')} />
            <JsonBlock value={{ filters: rule.filters_json, channels: rule.channels_json }} searchable={false} />
            <div className="action-row"><button className="ghost-button" onClick={() => testRule.mutate(rule.id)}>{t('notifications.test')}</button><button className="ghost-button danger" onClick={() => deleteRule.mutate(rule.id)}>{t('connectors.delete')}</button></div>
          </article>
        )) : <EmptyState title={t('notifications.noRules')} detail={t('notifications.noRulesDetail')} />}
      </section>
      <section className="panel notification-delivery-panel">
        <div className="panel-toolbar"><h2>{t('notifications.deliveryLog')}</h2></div>
        {deliveries.data?.length ? <div className="component-list notification-delivery-list">{deliveries.data.map((delivery) => <div key={delivery.id}><strong>{delivery.target_channel}</strong><span>{delivery.target_address}</span><StatusBadge status={delivery.status} /></div>)}</div> : <EmptyState title={t('notifications.noDeliveries')} detail={t('notifications.noDeliveriesDetail')} />}
      </section>
    </div>
  );
}
