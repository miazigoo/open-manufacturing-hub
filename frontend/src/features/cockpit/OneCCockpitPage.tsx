import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { uiApi } from '../../api/ui';
import { integrationFlowsApi } from '../../api/integrationFlows';
import { packagesApi } from '../../api/packages';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { StatusBadge } from '../../components/StatusBadge';
import { PageHeader } from '../../components/product/PageHeader';
import { SectionCard } from '../../components/product/SectionCard';
import { DataTable } from '../../components/product/DataTable';
import { EndpointUrlBox } from '../../components/product/EndpointUrlBox';
import { CopyButton } from '../../components/product/CopyButton';
import { ResultPanel } from '../../components/product/ResultPanel';
import { TimelineLink } from '../../components/product/TimelineLink';
import { EmptyPanel } from '../../components/product/EmptyPanel';

type Row = Record<string, unknown>;

function text(row: Row, key: string, fallback = ''): string {
  const value = row[key];
  return typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean' ? String(value) : fallback;
}

function bool(row: Row, key: string): boolean {
  return row[key] === true;
}

function metric(metrics: Record<string, number>, key: string): number {
  return Number(metrics[key] ?? 0);
}

export function OneCCockpitPage() {
  const queryClient = useQueryClient();
  const summary = useQuery({ queryKey: ['ui-cockpit-summary'], queryFn: uiApi.cockpitSummary });
  const installPackage = useMutation({ mutationFn: () => packagesApi.install('omh-package-onec', true), onSuccess: () => queryClient.invalidateQueries() });
  const enablePackage = useMutation({ mutationFn: () => packagesApi.enable('omh-package-onec'), onSuccess: () => queryClient.invalidateQueries() });
  const disableFlow = useMutation({ mutationFn: (id: string) => integrationFlowsApi.patch(id, { enabled: false }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['ui-cockpit-summary'] }) });
  const testFlow = useMutation({ mutationFn: (flow: Row) => integrationFlowsApi.test(text(flow, 'id'), { input_mode: 'json', payload_json: { inn: '1234567890', product_code: 'ABC-123', pool_id: 'POOL-001', codes: ['code1'] }, dry_run: false }) });

  if (summary.isLoading) return <LoadingState label="Loading 1C cockpit" />;
  if (summary.error) return <ErrorState error={summary.error} />;
  if (!summary.data) return <ErrorState error={new Error('Cockpit summary is empty')} />;

  const state = summary.data.package_state;
  const packageAction = !state.installed
    ? <button className="primary-button" onClick={() => installPackage.mutate()} disabled={installPackage.isPending}>Install 1C package</button>
    : !state.enabled
      ? <button className="primary-button" onClick={() => enablePackage.mutate()} disabled={enablePackage.isPending}>Enable 1C package</button>
      : <Link className="primary-button" to="/onec-cockpit/new">Create integration</Link>;

  return (
    <div className="page-stack cockpit-page">
      <PageHeader
        eyebrow="1C Integration Cockpit"
        title="Run and build 1C integrations from one product surface."
        description="A focused cockpit for 1C endpoints, OData enrichment, XML routing, generated HTTP examples and timeline-driven diagnostics."
        className="cockpit-hero"
        meta={<><StatusBadge status={state.enabled ? 'ok' : 'warning'} label={state.enabled ? '1C package enabled' : state.action_label} /><span className="microcopy">Package: {state.package_id}</span></>}
        actions={<>{packageAction}<Link className="ghost-button" to="/integration-flows">All flows</Link></>}
      />

      <section className="metric-grid cockpit-metrics">
        <article className="metric-card"><span>Enabled 1C flows</span><strong>{metric(summary.data.metrics, 'enabled_integrations')}</strong></article>
        <article className="metric-card bad"><span>Failed events</span><strong>{metric(summary.data.metrics, 'failed_events')}</strong></article>
        <article className="metric-card warn"><span>Need attention</span><strong>{metric(summary.data.metrics, 'attention_events')}</strong></article>
        <article className="metric-card info"><span>Connectors</span><strong>{metric(summary.data.metrics, 'connectors')}</strong></article>
      </section>

      <section className="cockpit-command-grid">
        <SectionCard eyebrow="Fast Start" title="Common 1C routes" description="Start from a business scenario, then refine matchers, OData lookups and target payloads in the wizard.">
          <div className="cockpit-action-grid" data-tour="create-integration">
            {summary.data.quick_actions.map((action) => {
              const row = action as Row;
              return (
                <Link key={text(row, 'code')} className={`cockpit-action-card ${row.primary ? 'primary' : ''}`} to={`/onec-cockpit/new?preset=${encodeURIComponent(text(row, 'preset'))}`}>
                  <span>{text(row, 'code')}</span>
                  <strong>{text(row, 'title')}</strong>
                  <p>{text(row, 'description')}</p>
                </Link>
              );
            })}
          </div>
        </SectionCard>

        <SectionCard eyebrow="Academy" title="1C POST -> OData -> JSON -> endpoint" description="A guided path for the most confusing setup: inbound token, named OData connection, OData lookup, JSON payload and final endpoint response.">
          <div className="cockpit-action-grid">
            <Link className="cockpit-action-card primary" to="/docs/onec/academy/lesson-01-map-of-the-product">
              <span>01</span>
              <strong>Start learning path</strong>
              <p>Concepts, endpoint contract, OData profiles and visual flow steps in order.</p>
            </Link>
            <Link className="cockpit-action-card" to="/odata-connections">
              <span>02</span>
              <strong>Create OData profiles</strong>
              <p>OData ERP, OData УСП or WMS with URL, user, password/secret and metadata test.</p>
            </Link>
            <Link className="cockpit-action-card" to="/docs/onec/recipes/recipe-01-onec-post-odata-json-endpoint">
              <span>03</span>
              <strong>Use a complete recipe</strong>
              <p>Copy the full business recipe with request examples, timeline checks and common mistakes.</p>
            </Link>
          </div>
        </SectionCard>

        <SectionCard eyebrow="Connection Health" title="1C / API / printer channels">
          {summary.data.connection_health.length === 0 ? <EmptyPanel title="No connectors" detail="Create 1C, REST or printer connectors to see runtime health here." action={<Link className="primary-button" to="/connectors">Add connector</Link>} /> : <div className="cockpit-health-list">{summary.data.connection_health.map((item) => { const row = item as Row; return <article key={text(row, 'id')}><div><strong>{text(row, 'name')}</strong><span>{text(row, 'connector_type')}</span></div><StatusBadge status={text(row, 'status', 'unknown')} label={text(row, 'status', 'unknown')} compact /><p>{text(row, 'message')}</p></article>; })}</div>}
        </SectionCard>
      </section>

      <SectionCard eyebrow="Operate" title="1C integrations" description="The cockpit shows only 1C-related flows: routes sourced from 1C, targeting 1C, or built from 1C presets." actions={<Link className="primary-button" to="/onec-cockpit/new">New route</Link>}>
        <DataTable<Row>
          rows={summary.data.integrations as Row[]}
          getRowKey={(row) => text(row, 'id')}
          emptyTitle="No 1C integrations"
          emptyDetail="Create the first route from 1C to API, OData enrichment, XML bridge or printer flow."
          columns={[
            { key: 'name', header: 'Integration', render: (row) => <div><strong>{text(row, 'name')}</strong><small>{text(row, 'source')} {'->'} {text(row, 'target')}</small></div> },
            { key: 'endpoint', header: 'Endpoint', render: (row) => <EndpointUrlBox url={text(row, 'endpoint_url')} label="" /> },
            { key: 'status', header: 'Status', render: (row) => <StatusBadge status={bool(row, 'enabled') ? 'ok' : 'cancelled'} label={bool(row, 'enabled') ? 'enabled' : 'disabled'} compact /> },
            { key: 'actions', header: 'Actions', render: (row) => <div className="toolbar-actions"><Link className="primary-link" to={text(row, 'builder_url')}>Builder</Link><button className="ghost-link" onClick={() => testFlow.mutate(row)}>Test</button><CopyButton value={text(row, 'onec_http_example')} label="Copy 1C code" className="ghost-link" />{bool(row, 'enabled') && <button className="ghost-link" onClick={() => disableFlow.mutate(text(row, 'id'))}>Disable</button>}</div> },
          ]}
        />
      </SectionCard>

      <section className="cockpit-command-grid lower">
        <SectionCard eyebrow="Recent" title="1C related events">
          {summary.data.recent_events.length === 0 ? <EmptyPanel title="No 1C events yet" detail="New XML/OData/print events will appear here with a direct timeline link." /> : <div className="cockpit-event-list" data-tour="recent-events">{summary.data.recent_events.map((item) => { const row = item as Row; return <article key={text(row, 'id')} className={bool(row, 'requires_attention') ? 'attention-row' : ''}><div><StatusBadge status={text(row, 'status', 'unknown')} compact /><strong>{text(row, 'title', text(row, 'id'))}</strong><p>{text(row, 'summary')}</p><small>{text(row, 'source')} {'->'} {text(row, 'target')}</small></div><TimelineLink to={text(row, 'timeline_url')} /></article>; })}</div>}
        </SectionCard>
        <SectionCard eyebrow="Execution Result" title="Last action response">
          <ResultPanel result={testFlow.data ?? null} />
          {testFlow.error && <div className="error-state compact">{(testFlow.error as Error).message}</div>}
        </SectionCard>
      </section>
    </div>
  );
}
