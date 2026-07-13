import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { integrationCoverageApi, type CoverageStatus, type DimensionStatus, type IntegrationCoverageItem } from '../api/integrationCoverage';
import { localized } from '../api/integrationPatterns';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

const statusFilters = ['all', 'ready', 'partial', 'planned', 'missing_docs', 'missing_wizard'] as const;
type StatusFilter = (typeof statusFilters)[number];

const statusLabels: Record<string, string> = {
  all: 'Все',
  ready: 'Ready',
  partial: 'Partial',
  planned: 'Planned',
  missing: 'Missing',
  missing_docs: 'Missing docs',
  missing_wizard: 'Missing wizard',
  missing_training: 'Missing training',
  not_applicable: 'N/A',
};

export function IntegrationCoveragePage() {
  const coverage = useQuery({ queryKey: ['integration-coverage'], queryFn: integrationCoverageApi.list });
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [personaFilter, setPersonaFilter] = useState('all');

  const personas = useMemo(() => {
    const values = new Set<string>();
    for (const item of coverage.data?.items ?? []) item.personas.forEach((persona) => values.add(persona));
    return ['all', ...Array.from(values).sort()];
  }, [coverage.data]);

  const visibleItems = useMemo(() => {
    return (coverage.data?.items ?? []).filter((item) => {
      const statusMatches = statusFilter === 'all' || item.status === statusFilter;
      const personaMatches = personaFilter === 'all' || item.personas.includes(personaFilter);
      return statusMatches && personaMatches;
    });
  }, [coverage.data, personaFilter, statusFilter]);

  if (coverage.isPending) return <LoadingState label="Загрузка матрицы интеграционных сценариев" />;
  if (coverage.error) return <ErrorState error={coverage.error} />;

  const summary = coverage.data.summary;

  return (
    <div className="page-stack integration-coverage-page">
      <section className="page-header integration-coverage-hero">
        <span className="eyebrow">Coverage Gate</span>
        <h1>Покрытие интеграционных сценариев</h1>
        <p>Единая матрица требований: какие сценарии можно настраивать сейчас, где есть мастер, документация, обучение, troubleshooting и тестовое покрытие.</p>
        <div className="hero-meta">
          <StatusBadge status="ready" label={`${summary.ready} ready`} />
          <StatusBadge status="partial" label={`${summary.partial} partial`} />
          <StatusBadge status="planned" label={`${summary.planned} planned`} />
          <Link className="primary-link" to="/docs/core/start/integration-scenarios">Какие интеграции можно настроить</Link>
          <Link className="primary-link" to="/docs/onec/troubleshooting/by-scenario">Troubleshooting by scenario</Link>
        </div>
      </section>

      <section className="guidance-strip">
        <div className="guidance-head">
          <div>
            <span className="eyebrow">Coverage Matrix</span>
            <h2>Coverage Matrix: проверяйте готовность сценария до настройки</h2>
            <p>Матрица отвечает на практический вопрос: можно ли уже запускать сценарий пользователю, или сначала не хватает мастера, документации, training example либо troubleshooting playbook.</p>
          </div>
          <div className="action-row wrap-actions">
            <Link className="ghost-button" to="/integration-start">Открыть Scenario Router</Link>
            <Link className="ghost-button" to="/training">Training Sandbox</Link>
          </div>
        </div>
        <div className="guidance-step-grid">
          <article className="guidance-step-card"><span>1</span><strong>Найдите нужный результат</strong><p>Смотрите на Source, Input, OMH actions и Result. Это быстрее, чем выбирать по техническому названию мастера.</p></article>
          <article className="guidance-step-card"><span>2</span><strong>Проверьте статус</strong><p><code>Ready</code> можно настраивать. <code>Partial</code> требует внимательной проверки gaps. <code>Planned</code> не обещает production-ready путь.</p></article>
          <article className="guidance-step-card"><span>3</span><strong>Откройте недостающий шаг</strong><p>Ссылки Wizard, Docs, Training и Troubleshooting показывают, куда идти дальше без поиска по меню.</p></article>
        </div>
      </section>

      <section className="metric-grid coverage-metrics">
        <Metric label="Всего сценариев" value={summary.total} />
        <Metric label="Ready" value={summary.ready} tone="good" />
        <Metric label="Partial" value={summary.partial} tone="warn" />
        <Metric label="Planned" value={summary.planned} tone="info" />
        <Metric label="Readiness" value={`${summary.average_readiness}%`} />
      </section>

      <section className="panel coverage-toolbar">
        <div>
          <h2>Фильтры</h2>
          <p>Missing docs / wizard остаются в матрице, чтобы внедренец не начал незакрытый сценарий по ошибке.</p>
        </div>
        <div className="coverage-filter-row">
          <div className="segmented-control coverage-status-filter">
            {statusFilters.map((status) => (
              <button key={status} className={statusFilter === status ? 'active' : ''} onClick={() => setStatusFilter(status)} type="button">
                {statusLabels[status]}
              </button>
            ))}
          </div>
          <label className="field-label">Persona
            <select value={personaFilter} onChange={(event) => setPersonaFilter(event.target.value)}>
              {personas.map((persona) => <option key={persona} value={persona}>{persona === 'all' ? 'Все' : persona}</option>)}
            </select>
          </label>
        </div>
      </section>

      <section className="table-panel coverage-table-panel">
        <div className="panel-toolbar">
          <div>
            <h2>Матрица требований</h2>
            <p>{visibleItems.length} из {summary.total} сценариев в текущем фильтре.</p>
          </div>
          <Link className="primary-link" to="/integration-start">Открыть Scenario Router</Link>
        </div>
        <div className="coverage-table-scroll">
          <table className="coverage-table">
            <thead>
              <tr>
                <th>Scenario</th>
                <th>Source</th>
                <th>Input</th>
                <th>OMH actions</th>
                <th>Result</th>
                <th>Pattern</th>
                <th>Wizard</th>
                <th>Docs</th>
                <th>Training</th>
                <th>Troubleshooting</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {visibleItems.map((item) => <CoverageRow key={item.requirement_id} item={item} />)}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string | number; tone?: 'good' | 'warn' | 'info' }) {
  return <article className={`metric-card ${tone ?? ''}`}><span>{label}</span><strong>{value}</strong></article>;
}

function CoverageRow({ item }: { item: IntegrationCoverageItem }) {
  const startRoute = item.wizard_route ?? item.workbench_route;
  const startable = Boolean(startRoute) && !['planned', 'missing_wizard'].includes(item.status);
  return (
    <tr className={item.status === 'ready' ? '' : 'attention-row'}>
      <td>
        <strong>{localized(item.title)}</strong>
        <small>{localized(item.description)}</small>
        {item.gaps.length > 0 && <details className="coverage-gap-details"><summary>Gaps: {item.gaps.length}</summary>{item.gaps.map((gap) => <p key={gap}>{gap}</p>)}</details>}
      </td>
      <td><span>{localized(item.source_summary)}</span><small>{item.source_systems.join(', ')}</small></td>
      <td><span>{localized(item.input_summary)}</span><small>{item.input_modes.join(', ')}</small></td>
      <td><span>{localized(item.omh_actions_summary)}</span><small>{item.omh_actions.join(' -> ')}</small></td>
      <td>{localized(item.result_summary)}</td>
      <td><CodeLink code={item.recommended_pattern} route={item.recommended_pattern ? `/integration-patterns/${item.recommended_pattern}` : null} /></td>
      <td><ActionCell status={item.statuses.wizard} route={startable ? startRoute : null} fallback={startRoute ? 'Скоро' : 'Нет'} /></td>
      <td><LinkList status={item.statuses.docs} links={item.docs_links} empty="Нет docs" /></td>
      <td><TrainingCell status={item.statuses.training} ids={item.training_example_ids} /></td>
      <td><LinkList status={item.statuses.troubleshooting} links={item.troubleshooting_links} empty="Нет playbook" /></td>
      <td>
        <div className="coverage-status-cell">
          <StatusBadge status={item.status} label={statusLabels[item.status] ?? item.status} compact />
          <strong>{item.readiness_score}%</strong>
          <Checklist items={item.checklist} />
          {item.package_statuses.some((pkg) => pkg.warning) && (
            <small className="coverage-package-warning">{item.package_statuses.filter((pkg) => pkg.warning).map((pkg) => `${pkg.package_id}: ${pkg.warning}`).join('; ')}</small>
          )}
        </div>
      </td>
    </tr>
  );
}

function CodeLink({ code, route }: { code: string | null; route: string | null }) {
  if (!code) return <span className="muted">-</span>;
  if (!route) return <code>{code}</code>;
  return <Link className="primary-link mono" to={route}>{code}</Link>;
}

function ActionCell({ status, route, fallback }: { status: DimensionStatus; route: string | null; fallback: string }) {
  return (
    <div className="coverage-action-cell">
      <StatusBadge status={status} label={statusLabels[status] ?? status} compact />
      {route ? <Link className="primary-link" to={route}>Открыть</Link> : <small>{fallback}</small>}
    </div>
  );
}

function LinkList({ status, links, empty }: { status: DimensionStatus; links: string[]; empty: string }) {
  return (
    <div className="coverage-action-cell">
      <StatusBadge status={status} label={statusLabels[status] ?? status} compact />
      {links.length ? links.map((link) => <Link className="primary-link" key={link} to={link}>{shortLink(link)}</Link>) : <small>{empty}</small>}
    </div>
  );
}

function TrainingCell({ status, ids }: { status: DimensionStatus; ids: string[] }) {
  return (
    <div className="coverage-action-cell">
      <StatusBadge status={status} label={statusLabels[status] ?? status} compact />
      {ids.length ? ids.map((id) => <Link className="primary-link" key={id} to={`/training?exampleId=${id}`}>{id.replace('training.onec.', '')}</Link>) : <small>Нет example</small>}
    </div>
  );
}

function Checklist({ items }: { items: IntegrationCoverageItem['checklist'] }) {
  return (
    <details className="coverage-checklist">
      <summary>Checklist</summary>
      {items.map((item) => (
        <div key={item.label}>
          <StatusBadge status={item.status} label={statusLabels[item.status] ?? item.status} compact />
          {item.link ? <Link to={item.link}>{item.label}</Link> : <span>{item.label}</span>}
        </div>
      ))}
    </details>
  );
}

function shortLink(link: string) {
  const parts = link.split('/').filter(Boolean);
  return parts.slice(-2).join('/');
}
