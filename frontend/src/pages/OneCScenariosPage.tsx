import { FormEvent, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { onecScenariosApi, OneCScenarioPreset, ShipmentFactTestPayload } from '../api/onecScenarios';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { useT } from '../i18n/useI18n';

const defaultItems = [{ sku: 'ABC123', qty: 5 }];

export function OneCScenariosPage() {
  const t = useT();
  const queryClient = useQueryClient();
  const presets = useQuery({ queryKey: ['onec-scenarios'], queryFn: onecScenariosApi.presets });
  const [form, setForm] = useState({ order_id: '1532', shipment_id: 'WMS-SHIP-1532', status: 'shipped', warehouse_id: 'MAIN', items: asJson(defaultItems) });
  const [formError, setFormError] = useState<string | null>(null);

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['connectors'] });
    queryClient.invalidateQueries({ queryKey: ['mappings'] });
    queryClient.invalidateQueries({ queryKey: ['workflows'] });
    queryClient.invalidateQueries({ queryKey: ['polling-jobs'] });
    queryClient.invalidateQueries({ queryKey: ['events'] });
    queryClient.invalidateQueries({ queryKey: ['incidents'] });
  };
  const installForward = useMutation({ mutationFn: onecScenariosApi.installSalesOrderDemo, onSuccess: refresh });
  const installBidirectional = useMutation({ mutationFn: onecScenariosApi.installBidirectionalDemo, onSuccess: refresh });
  const testShipmentFact = useMutation({ mutationFn: onecScenariosApi.testShipmentFact, onSuccess: refresh });

  const forwardPreset = useMemo(() => presets.data?.find((preset) => preset.key === 'onec_sales_order_to_mock_wms'), [presets.data]);
  const reversePreset = useMemo(() => presets.data?.find((preset) => preset.key === 'mock_wms_shipment_fact_to_onec'), [presets.data]);

  function submitTest(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    try {
      const payload: ShipmentFactTestPayload = {
        order_id: form.order_id,
        shipment_id: form.shipment_id,
        status: form.status,
        warehouse_id: form.warehouse_id,
        items: JSON.parse(form.items) as Array<Record<string, unknown>>,
      };
      testShipmentFact.mutate(payload);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Invalid items JSON');
    }
  }

  if (presets.isLoading) return <LoadingState label={t('onec.loading')} />;
  if (presets.error) return <ErrorState error={presets.error} />;

  return (
    <div className="page-stack onec-scenario-page">
      <section className="page-header onec-hero">
        <span className="eyebrow">{t('onec.eyebrow')}</span>
        <h1>{t('onec.title')}</h1>
        <p>{t('onec.subtitle')}</p>
        <div className="hero-meta"><Link className="primary-link" to="/polling">{t('onec.openPolling')}</Link><Link className="ghost-link" to="/mappings">{t('onec.reviewMappings')}</Link><Link className="ghost-link" to="/incidents">{t('nav.incidents')}</Link></div>
      </section>

      <section className="scenario-grid scenario-grid-wide">
        <div className="scenario-list">
          {forwardPreset ? <ScenarioCard preset={forwardPreset} orbit={['1C', 'OMH', 'WMS']} actionLabel={t('onec.installDemo')} pending={installForward.isPending} onInstall={() => installForward.mutate()} /> : null}
          {reversePreset ? <ScenarioCard preset={reversePreset} orbit={['WMS', 'OMH', '1C']} actionLabel={t('onec.installBidirectional')} pending={installBidirectional.isPending} onInstall={() => installBidirectional.mutate()} /> : null}
          {!forwardPreset && !reversePreset && <EmptyState title={t('onec.noPresets')} detail={t('onec.noPresetsDetail')} />}
        </div>

        <aside className="panel scenario-sidecar">
          <h2>{t('onec.testFact')}</h2>
          <p>{t('onec.testHint')}</p>
          <form className="stack-form" onSubmit={submitTest}>
            <div className="metadata-grid compact-grid no-margin">
              <label className="field-label">{t('onec.orderId')}<input value={form.order_id} onChange={(event) => setForm({ ...form, order_id: event.target.value, shipment_id: `WMS-SHIP-${event.target.value}` })} /></label>
              <label className="field-label">{t('onec.shipmentId')}<input value={form.shipment_id} onChange={(event) => setForm({ ...form, shipment_id: event.target.value })} /></label>
              <label className="field-label">{t('common.status')}<input value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })} /></label>
            </div>
            <label className="field-label">{t('onec.warehouseId')}<input value={form.warehouse_id} onChange={(event) => setForm({ ...form, warehouse_id: event.target.value })} /></label>
            <label className="field-label">{t('onec.itemsJson')}<textarea value={form.items} onChange={(event) => setForm({ ...form, items: event.target.value })} spellCheck={false} /></label>
            {formError && <div className="error-state compact">{formError}</div>}
            {testShipmentFact.error instanceof Error && <div className="error-state compact">{testShipmentFact.error.message}</div>}
            <button className="primary-button" disabled={testShipmentFact.isPending}>{t('onec.testFact')}</button>
          </form>
          {testShipmentFact.data && <div className="success-note">{t('onec.createdEvent', { id: testShipmentFact.data.event_id })} <Link className="primary-link" to={`/events/${testShipmentFact.data.event_id}`}>{t('onec.openTimeline')}</Link></div>}
          <JsonBlock title={t('onec.latestResult')} value={testShipmentFact.data ?? installBidirectional.data ?? installForward.data ?? { hint: t('onec.resultHint') }} searchable={false} />
        </aside>
      </section>
    </div>
  );
}

function ScenarioCard({ preset, orbit, actionLabel, pending, onInstall }: { preset: OneCScenarioPreset; orbit: string[]; actionLabel: string; pending: boolean; onInstall: () => void }) {
  const t = useT();
  return (
    <article className="scenario-card" key={preset.key}>
      <div className="scenario-orbit">{orbit.map((label) => <span key={label}>{label}</span>)}</div>
      <div className="scenario-body">
        <span className="eyebrow">{preset.source_resource}</span>
        <h2>{preset.name}</h2>
        <p>{preset.description}</p>
        <div className="metadata-grid compact-grid">
          <span>{t('events.eventType')}<strong>{preset.event_type}</strong></span>
          <span>{t('common.entity')}<strong>{preset.entity_type}</strong></span>
          <span>{t('nav.mappings')}<strong>{preset.mappings.length}</strong></span>
        </div>
        <div className="workflow-steps">{preset.mappings.map((mapping) => <span key={mapping}>{mapping}</span>)}</div>
        <div className="action-row">
          <button className="primary-button" onClick={onInstall} disabled={pending}>{actionLabel}</button>
          <Link className="ghost-button" to="/connectors">{t('nav.connectors')}</Link>
          <Link className="ghost-button" to="/workflows">{t('nav.workflows')}</Link>
        </div>
      </div>
    </article>
  );
}
