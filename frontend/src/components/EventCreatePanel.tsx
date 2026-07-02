import { FormEvent, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { eventsApi, EventCreatePayload } from '../api/events';
import { asJson } from '../api/client';
import { useT } from '../i18n/I18nProvider';

const successPreset: EventCreatePayload = {
  correlation_id: 'corr_success_demo',
  source_system: 'Mock ERP',
  target_system: 'Mock WMS',
  event_type: 'SalesOrderCreated',
  entity_type: 'SalesOrder',
  entity_id: '1532',
  payload: { order_id: '1532', warehouse_id: 'MAIN', items: [{ sku: 'ABC123', qty: 5 }] },
};

const failurePreset: EventCreatePayload = {
  ...successPreset,
  correlation_id: 'corr_failure_demo',
  entity_id: '1533',
  payload: { order_id: '1533', warehouse_id: '005', items: [{ sku: 'ABC123', qty: 5 }] },
};

function toForm(payload: EventCreatePayload) {
  return {
    correlation_id: payload.correlation_id ?? '',
    source_system: payload.source_system,
    target_system: payload.target_system ?? '',
    event_type: payload.event_type,
    entity_type: payload.entity_type ?? '',
    entity_id: payload.entity_id ?? '',
    payload: asJson(payload.payload),
  };
}

export function EventCreatePanel() {
  const t = useT();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form, setForm] = useState(toForm(failurePreset));
  const [error, setError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: eventsApi.create,
    onSuccess: (event) => {
      queryClient.invalidateQueries({ queryKey: ['events'] });
      navigate(`/events/${event.id}`);
    },
  });

  function applyPreset(type: 'success' | 'failure') {
    setError(null);
    setForm(toForm(type === 'success' ? successPreset : failurePreset));
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      mutation.mutate({
        correlation_id: form.correlation_id || null,
        source_system: form.source_system,
        target_system: form.target_system || null,
        event_type: form.event_type,
        entity_type: form.entity_type || null,
        entity_id: form.entity_id || null,
        payload: JSON.parse(form.payload) as Record<string, unknown>,
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t('eventCreate.invalidJson'));
    }
  }

  return (
    <section className="panel create-event-panel">
      <div className="panel-toolbar">
        <div>
          <span className="eyebrow">{t('eventCreate.eyebrow')}</span>
          <h2>{t('eventCreate.title')}</h2>
        </div>
        <div className="toolbar-actions">
          <button className="ghost-button" type="button" onClick={() => applyPreset('failure')}>{t('eventCreate.failurePreset')}</button>
          <button className="ghost-button" type="button" onClick={() => applyPreset('success')}>{t('eventCreate.successPreset')}</button>
        </div>
      </div>
      <form className="create-event-grid" onSubmit={submit}>
        <label className="field-label">{t('events.eventType')}<input value={form.event_type} onChange={(event) => setForm({ ...form, event_type: event.target.value })} /></label>
        <label className="field-label">{t('eventCreate.entityId')}<input value={form.entity_id} onChange={(event) => setForm({ ...form, entity_id: event.target.value })} /></label>
        <label className="field-label">{t('common.source')}<input value={form.source_system} onChange={(event) => setForm({ ...form, source_system: event.target.value })} /></label>
        <label className="field-label">{t('common.target')}<input value={form.target_system} onChange={(event) => setForm({ ...form, target_system: event.target.value })} /></label>
        <label className="field-label wide-field">{t('events.correlationId')}<input value={form.correlation_id} onChange={(event) => setForm({ ...form, correlation_id: event.target.value })} /></label>
        <label className="field-label wide-field">{t('eventCreate.payloadJson')}<textarea value={form.payload} onChange={(event) => setForm({ ...form, payload: event.target.value })} spellCheck={false} /></label>
        {error && <div className="error-state compact wide-field">{error}</div>}
        {mutation.error instanceof Error && <div className="error-state compact wide-field">{mutation.error.message}</div>}
        <button className="primary-button wide-field" disabled={mutation.isPending}>{t('eventCreate.submit')}</button>
      </form>
    </section>
  );
}
