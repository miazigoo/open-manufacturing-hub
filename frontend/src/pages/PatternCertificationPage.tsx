import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { localized } from '../api/integrationPatterns';
import { patternCertificationApi, type PatternCertification, type PatternCertificationStatus } from '../api/patternCertification';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

const statusFilters = ['all', 'ready_for_training', 'partial', 'not_started', 'ready_for_production', 'deprecated'] as const;
type StatusFilter = (typeof statusFilters)[number];

const filterLabels: Record<StatusFilter, string> = {
  all: 'Все',
  ready_for_training: 'Training-ready',
  partial: 'Partial',
  not_started: 'Planned',
  ready_for_production: 'Production-ready',
  deprecated: 'Deprecated',
};

export function PatternCertificationPage() {
  const certification = useQuery({ queryKey: ['pattern-certification'], queryFn: patternCertificationApi.list });
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  const items = useMemo(() => {
    return (certification.data?.items ?? []).filter((item) => statusFilter === 'all' || item.certification_status === statusFilter);
  }, [certification.data, statusFilter]);

  if (certification.isPending) return <LoadingState label="Загрузка готовности сценариев" />;
  if (certification.error) return <ErrorState error={certification.error} />;

  const summary = certification.data.summary;

  return (
    <div className="page-stack pattern-certification-page">
      <section className="page-header pattern-certification-hero">
        <span className="eyebrow">Pattern Certification</span>
        <h1>Готовность сценариев интеграции</h1>
        <p>Quality gate по реализации паттернов: UI, docs, training, тесты, Timeline и Simple Mode. Это не бизнес-coverage: матрица покрытия отвечает на вопрос “какие сценарии нужны”, а certification отвечает “насколько качественно реализован мастер”.</p>
        <div className="hero-meta">
          <StatusBadge status="ready_for_training" label={`${summary.ready_for_training} training-ready`} />
          <StatusBadge status="partial" label={`${summary.partial} partial`} />
          <StatusBadge status="planned" label={`${summary.not_started} planned`} />
          <Link className="primary-link" to="/integration-coverage">Матрица покрытия</Link>
          <Link className="primary-link" to="/docs/core/pattern-readiness">Правила readiness</Link>
        </div>
      </section>

      <section className="metric-grid coverage-metrics">
        <Metric label="Паттернов" value={summary.total} />
        <Metric label="Training-ready" value={summary.ready_for_training} tone="good" />
        <Metric label="Partial" value={summary.partial} tone="warn" />
        <Metric label="Production-ready" value={summary.ready_for_production} tone="info" />
        <Metric label="С проблемами" value={summary.problem_patterns} tone="warn" />
      </section>

      <section className="panel coverage-toolbar">
        <div>
          <h2>Фильтры</h2>
          <p>Planned/partial строки остаются видимыми, чтобы не обещать production-ready сценарии без training и smoke evidence.</p>
        </div>
        <div className="segmented-control pattern-certification-filter">
          {statusFilters.map((status) => (
            <button key={status} className={statusFilter === status ? 'active' : ''} onClick={() => setStatusFilter(status)} type="button">
              {filterLabels[status]}
            </button>
          ))}
        </div>
      </section>

      <section className="table-panel coverage-table-panel pattern-certification-table-panel">
        <div className="panel-toolbar">
          <div>
            <h2>Quality Gate</h2>
            <p>{items.length} из {summary.total} паттернов в текущем фильтре.</p>
          </div>
          <div className="action-row wrap-actions">
            <Link className="primary-link" to="/docs/core/why-wizard-not-workflow">Почему wizard, не workflow</Link>
            <Link className="primary-link" to="/docs/core/choosing-integration-scenario">Как выбрать сценарий</Link>
          </div>
        </div>
        <div className="coverage-table-scroll">
          <table className="coverage-table pattern-certification-table">
            <thead>
              <tr>
                <th>Паттерн</th>
                <th>Статус</th>
                <th>UI</th>
                <th>Docs</th>
                <th>Training</th>
                <th>Tests</th>
                <th>Timeline</th>
                <th>Simple Mode</th>
                <th>Проблемы</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => <CertificationRow key={item.pattern_id} item={item} />)}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function CertificationRow({ item }: { item: PatternCertification }) {
  return (
    <tr className={item.certification_status === 'ready_for_training' || item.certification_status === 'ready_for_production' ? '' : 'attention-row'}>
      <td>
        <strong>{localized(item.title)}</strong>
        <small>{item.pattern_id}</small>
        <small>{localized(item.description)}</small>
        <div className="pattern-certification-links">
          {item.wizard_route && <Link className="primary-link" to={item.wizard_route}>Мастер</Link>}
          <Link className="primary-link" to={`/integration-patterns/${item.pattern_id}`}>Детали</Link>
          {item.docs_link && <Link className="primary-link" to={item.docs_link}>Docs</Link>}
        </div>
      </td>
      <td><StatusBadge status={item.certification_status} label={localized(item.status_label)} compact /></td>
      <td><Dimension status={item.ui_status} /></td>
      <td><Dimension status={item.docs_status} /></td>
      <td><Dimension status={item.training_status} /></td>
      <td><Dimension status={item.tests_status} /></td>
      <td><Dimension status={item.timeline_status} /></td>
      <td><Dimension status={item.simple_mode_status} /></td>
      <td>
        {item.problems.length ? (
          <details className="coverage-gap-details" open={item.certification_status !== 'ready_for_training'}>
            <summary>{item.problems.length} проблем</summary>
            {item.problems.slice(0, 6).map((problem) => <p key={problem}>{problem}</p>)}
          </details>
        ) : <span className="muted">Нет блокеров</span>}
      </td>
      <td>
        <ul className="pattern-list compact-list">
          {item.actions.slice(0, 4).map((action) => <li key={localized(action)}>{localized(action)}</li>)}
        </ul>
      </td>
    </tr>
  );
}

function Dimension({ status }: { status: string }) {
  const label = status === 'passed' ? 'OK' : status === 'warning' ? 'Warning' : status === 'planned' ? 'Planned' : 'Fail';
  const badgeStatus = status === 'passed' ? 'ready' : status;
  return <StatusBadge status={badgeStatus} label={label} compact />;
}

function Metric({ label, value, tone }: { label: string; value: string | number; tone?: 'good' | 'warn' | 'info' }) {
  return <article className={`metric-card ${tone ?? ''}`}><span>{label}</span><strong>{value}</strong></article>;
}

export function certificationStartLabel(status?: PatternCertificationStatus | null) {
  if (status === 'ready_for_production') return 'Готово';
  if (status === 'ready_for_training') return 'Учебный пример есть';
  if (status === 'partial') return 'Частично';
  if (status === 'not_started') return 'Запланировано';
  if (status === 'deprecated') return 'Deprecated';
  return 'Готовность не проверена';
}
