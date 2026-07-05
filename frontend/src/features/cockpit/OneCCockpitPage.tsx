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
import { useI18n } from '../../i18n/useI18n';

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
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const summary = useQuery({ queryKey: ['ui-cockpit-summary'], queryFn: uiApi.cockpitSummary });
  const installPackage = useMutation({ mutationFn: () => packagesApi.install('omh-package-onec', true), onSuccess: () => queryClient.invalidateQueries() });
  const enablePackage = useMutation({ mutationFn: () => packagesApi.enable('omh-package-onec'), onSuccess: () => queryClient.invalidateQueries() });
  const disableFlow = useMutation({ mutationFn: (id: string) => integrationFlowsApi.patch(id, { enabled: false }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['ui-cockpit-summary'] }) });
  const testFlow = useMutation({ mutationFn: (flow: Row) => integrationFlowsApi.test(text(flow, 'id'), { input_mode: 'json', payload_json: { inn: '1234567890', product_code: 'ABC-123', pool_id: 'POOL-001', codes: ['code1'] }, dry_run: false }) });

  if (summary.isLoading) return <LoadingState label={t('integration.cockpit.loading')} />;
  if (summary.error) return <ErrorState error={summary.error} />;
  if (!summary.data) return <ErrorState error={new Error(t('integration.cockpit.empty'))} />;

  const state = summary.data.package_state;
  const packageAction = !state.installed
    ? <button className="primary-button" onClick={() => installPackage.mutate()} disabled={installPackage.isPending}>{t('integration.cockpit.installPackage')}</button>
    : !state.enabled
      ? <button className="primary-button" onClick={() => enablePackage.mutate()} disabled={enablePackage.isPending}>{t('integration.cockpit.enablePackage')}</button>
      : <Link className="primary-button" to="/onec-cockpit/new">{t('integration.cockpit.createIntegration')}</Link>;

  return (
    <div className="page-stack cockpit-page">
      <PageHeader
        eyebrow={t('integration.cockpit.eyebrow')}
        title={t('integration.cockpit.title')}
        description={t('integration.cockpit.description')}
        className="cockpit-hero"
        meta={<><StatusBadge status={state.enabled ? 'ok' : 'warning'} label={state.enabled ? t('integration.cockpit.packageEnabled') : state.action_label} /><span className="microcopy">{t('integration.cockpit.package', { id: state.package_id })}</span></>}
        actions={<>{packageAction}<Link className="ghost-button" to="/integration-flows">{t('integration.cockpit.allFlows')}</Link></>}
      />

      <section className="metric-grid cockpit-metrics">
        <article className="metric-card"><span>{t('integration.cockpit.enabledFlows')}</span><strong>{metric(summary.data.metrics, 'enabled_integrations')}</strong></article>
        <article className="metric-card bad"><span>{t('integration.cockpit.failedEvents')}</span><strong>{metric(summary.data.metrics, 'failed_events')}</strong></article>
        <article className="metric-card warn"><span>{t('integration.cockpit.needAttention')}</span><strong>{metric(summary.data.metrics, 'attention_events')}</strong></article>
        <article className="metric-card info"><span>{t('integration.cockpit.connectors')}</span><strong>{metric(summary.data.metrics, 'connectors')}</strong></article>
      </section>

      <section className="cockpit-command-grid">
        <SectionCard eyebrow={t('integration.cockpit.fastStart')} title={t('integration.cockpit.commonRoutes')} description={t('integration.cockpit.commonRoutesDesc')}>
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

        <SectionCard eyebrow={t('integration.cockpit.academy')} title={t('integration.cockpit.academyTitle')} description={t('integration.cockpit.academyDesc')}>
          <div className="cockpit-action-grid">
            <Link className="cockpit-action-card primary" to="/docs/onec/academy/lesson-01-map-of-the-product">
              <span>01</span>
              <strong>{t('integration.cockpit.startLearning')}</strong>
              <p>{t('integration.cockpit.startLearningDesc')}</p>
            </Link>
            <Link className="cockpit-action-card" to="/odata-connections">
              <span>02</span>
              <strong>{t('integration.cockpit.createODataProfiles')}</strong>
              <p>{t('integration.cockpit.createODataProfilesDesc')}</p>
            </Link>
            <Link className="cockpit-action-card" to="/docs/onec/recipes/recipe-02-onec-post-two-odata-lookups">
              <span>03</span>
              <strong>{t('integration.cockpit.useRecipe')}</strong>
              <p>{t('integration.cockpit.useRecipeDesc')}</p>
            </Link>
          </div>
        </SectionCard>

        <SectionCard eyebrow={t('integration.cockpit.connectionHealth')} title={t('integration.cockpit.connectionHealthTitle')}>
          {summary.data.connection_health.length === 0 ? <EmptyPanel title={t('integration.cockpit.noConnectors')} detail={t('integration.cockpit.noConnectorsDetail')} action={<Link className="primary-button" to="/connectors">{t('integration.cockpit.addConnector')}</Link>} /> : <div className="cockpit-health-list">{summary.data.connection_health.map((item) => { const row = item as Row; return <article key={text(row, 'id')}><div><strong>{text(row, 'name')}</strong><span>{text(row, 'connector_type')}</span></div><StatusBadge status={text(row, 'status', 'unknown')} label={text(row, 'status', 'unknown')} compact /><p>{text(row, 'message')}</p></article>; })}</div>}
        </SectionCard>
      </section>

      <SectionCard eyebrow={t('integration.cockpit.operate')} title={t('integration.cockpit.integrations')} description={t('integration.cockpit.integrationsDesc')} actions={<Link className="primary-button" to="/onec-cockpit/new">{t('integration.cockpit.newRoute')}</Link>}>
        <DataTable<Row>
          rows={summary.data.integrations as Row[]}
          getRowKey={(row) => text(row, 'id')}
          emptyTitle={t('integration.cockpit.noIntegrations')}
          emptyDetail={t('integration.cockpit.noIntegrationsDetail')}
          columns={[
            { key: 'name', header: t('integration.cockpit.integration'), render: (row) => <div><strong>{text(row, 'name')}</strong><small>{text(row, 'source')} {'->'} {text(row, 'target')}</small></div> },
            { key: 'endpoint', header: 'Endpoint', render: (row) => <EndpointUrlBox url={text(row, 'endpoint_url')} label="" /> },
            { key: 'status', header: t('integration.cockpit.status'), render: (row) => <StatusBadge status={bool(row, 'enabled') ? 'ok' : 'cancelled'} label={bool(row, 'enabled') ? t('integration.cockpit.enabled') : t('integration.cockpit.disabled')} compact /> },
            { key: 'actions', header: t('integration.cockpit.actions'), render: (row) => <div className="toolbar-actions"><Link className="primary-link" to={text(row, 'builder_url')}>{t('integration.cockpit.builder')}</Link><button className="ghost-link" onClick={() => testFlow.mutate(row)}>{t('integration.cockpit.test')}</button><CopyButton value={text(row, 'onec_http_example')} label={t('integration.cockpit.copy1cCode')} className="ghost-link" />{bool(row, 'enabled') && <button className="ghost-link" onClick={() => disableFlow.mutate(text(row, 'id'))}>{t('integration.cockpit.disable')}</button>}</div> },
          ]}
        />
      </SectionCard>

      <section className="cockpit-command-grid lower">
        <SectionCard eyebrow={t('integration.cockpit.recent')} title={t('integration.cockpit.recentEvents')}>
          {summary.data.recent_events.length === 0 ? <EmptyPanel title={t('integration.cockpit.noEvents')} detail={t('integration.cockpit.noEventsDetail')} /> : <div className="cockpit-event-list" data-tour="recent-events">{summary.data.recent_events.map((item) => { const row = item as Row; return <article key={text(row, 'id')} className={bool(row, 'requires_attention') ? 'attention-row' : ''}><div><StatusBadge status={text(row, 'status', 'unknown')} compact /><strong>{text(row, 'title', text(row, 'id'))}</strong><p>{text(row, 'summary')}</p><small>{text(row, 'source')} {'->'} {text(row, 'target')}</small></div><TimelineLink to={text(row, 'timeline_url')} /></article>; })}</div>}
        </SectionCard>
        <SectionCard eyebrow={t('integration.cockpit.executionResult')} title={t('integration.cockpit.lastAction')}>
          <ResultPanel result={testFlow.data ?? null} />
          {testFlow.error && <div className="error-state compact">{(testFlow.error as Error).message}</div>}
        </SectionCard>
      </section>
    </div>
  );
}
