import { FormEvent, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { onecScenariosApi, OneCScenarioPreset, ShipmentFactTestPayload } from '../api/onecScenarios';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';

const defaultItems = [{ sku: 'ABC123', qty: 5 }];

export function OneCScenariosPage() {
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

  if (presets.isLoading) return <LoadingState label="Loading 1C scenarios" />;
  if (presets.error) return <ErrorState error={presets.error} />;

  return (
    <div className="page-stack onec-scenario-page">
      <section className="page-header onec-hero">
        <span className="eyebrow">1C Scenario Builder</span>
        <h1>Bidirectional 1C integration, visible end to end.</h1>
        <p>Install forward OData polling and reverse HTTP service updates. Every request, response, business error and replay stays in the event timeline.</p>
        <div className="hero-meta"><Link className="primary-link" to="/polling">Open Polling Jobs</Link><Link className="ghost-link" to="/mappings">Review Mappings</Link><Link className="ghost-link" to="/incidents">Incidents</Link></div>
      </section>

      <section className="scenario-grid scenario-grid-wide">
        <div className="scenario-list">
          {forwardPreset ? <ScenarioCard preset={forwardPreset} orbit={['1C', 'OMH', 'WMS']} actionLabel="Install Demo" pending={installForward.isPending} onInstall={() => installForward.mutate()} /> : null}
          {reversePreset ? <ScenarioCard preset={reversePreset} orbit={['WMS', 'OMH', '1C']} actionLabel="Install Bidirectional Demo" pending={installBidirectional.isPending} onInstall={() => installBidirectional.mutate()} /> : null}
          {!forwardPreset && !reversePreset && <EmptyState title="No scenario presets" detail="Backend did not return 1C scenario presets." />}
        </div>

        <aside className="panel scenario-sidecar">
          <h2>Test Shipment Fact</h2>
          <p>Use order `1532` for success, `404` for business error, and `500` for technical 1C failure.</p>
          <form className="stack-form" onSubmit={submitTest}>
            <div className="metadata-grid compact-grid no-margin">
              <label className="field-label">Order ID<input value={form.order_id} onChange={(event) => setForm({ ...form, order_id: event.target.value, shipment_id: `WMS-SHIP-${event.target.value}` })} /></label>
              <label className="field-label">Shipment ID<input value={form.shipment_id} onChange={(event) => setForm({ ...form, shipment_id: event.target.value })} /></label>
              <label className="field-label">Status<input value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })} /></label>
            </div>
            <label className="field-label">Warehouse ID<input value={form.warehouse_id} onChange={(event) => setForm({ ...form, warehouse_id: event.target.value })} /></label>
            <label className="field-label">Items JSON<textarea value={form.items} onChange={(event) => setForm({ ...form, items: event.target.value })} spellCheck={false} /></label>
            {formError && <div className="error-state compact">{formError}</div>}
            {testShipmentFact.error instanceof Error && <div className="error-state compact">{testShipmentFact.error.message}</div>}
            <button className="primary-button" disabled={testShipmentFact.isPending}>Test Shipment Fact</button>
          </form>
          {testShipmentFact.data && <div className="success-note">Created event: {testShipmentFact.data.event_id} <Link className="primary-link" to={`/events/${testShipmentFact.data.event_id}`}>Open Timeline</Link></div>}
          <JsonBlock title="Latest install / test result" value={testShipmentFact.data ?? installBidirectional.data ?? installForward.data ?? { hint: 'Install a scenario or run a test.' }} searchable={false} />
        </aside>
      </section>
    </div>
  );
}

function ScenarioCard({ preset, orbit, actionLabel, pending, onInstall }: { preset: OneCScenarioPreset; orbit: string[]; actionLabel: string; pending: boolean; onInstall: () => void }) {
  return (
    <article className="scenario-card" key={preset.key}>
      <div className="scenario-orbit">{orbit.map((label) => <span key={label}>{label}</span>)}</div>
      <div className="scenario-body">
        <span className="eyebrow">{preset.source_resource}</span>
        <h2>{preset.name}</h2>
        <p>{preset.description}</p>
        <div className="metadata-grid compact-grid">
          <span>Event<strong>{preset.event_type}</strong></span>
          <span>Entity<strong>{preset.entity_type}</strong></span>
          <span>Mappings<strong>{preset.mappings.length}</strong></span>
        </div>
        <div className="workflow-steps">{preset.mappings.map((mapping) => <span key={mapping}>{mapping}</span>)}</div>
        <div className="action-row">
          <button className="primary-button" onClick={onInstall} disabled={pending}>{actionLabel}</button>
          <Link className="ghost-button" to="/connectors">Connectors</Link>
          <Link className="ghost-button" to="/workflows">Workflows</Link>
        </div>
      </div>
    </article>
  );
}
