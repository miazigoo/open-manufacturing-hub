import { FormEvent, useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { integrationCoverageApi, type IntegrationCoverageItem } from '../api/integrationCoverage';
import { integrationPatternsApi, localized, type IntegrationPattern, type PatternRecommendRequest } from '../api/integrationPatterns';
import { patternCertificationApi, type PatternCertification, type PatternCertificationStatus } from '../api/patternCertification';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { SectionCard } from '../components/product/SectionCard';

type QuestionnaireState = {
  source_system: string;
  input_mode: NonNullable<PatternRecommendRequest['input_mode']>;
  needs_odata: boolean | null;
  needs_foreach: boolean;
  needs_file_save: boolean;
  needs_response: boolean;
  needs_send_endpoint: boolean;
  needs_print: boolean;
  needs_writeback: boolean;
  needs_polling: boolean;
};

const startableCoverageStatuses = new Set(['ready', 'partial']);
const startableWizardStatuses = new Set(['ready', 'partial']);

export function IntegrationStartPage() {
  const navigate = useNavigate();
  const patterns = useQuery({ queryKey: ['integration-patterns'], queryFn: integrationPatternsApi.list });
  const coverage = useQuery({ queryKey: ['integration-coverage'], queryFn: integrationCoverageApi.list });
  const certification = useQuery({ queryKey: ['pattern-certification'], queryFn: patternCertificationApi.list });
  const recommend = useMutation({ mutationFn: integrationPatternsApi.recommend });
  const start = useMutation({
    mutationFn: integrationPatternsApi.start,
    onSuccess: (data) => navigate(data.wizard_route),
  });
  const [answers, setAnswers] = useState<QuestionnaireState>({
    source_system: 'external_api',
    input_mode: 'json',
    needs_odata: true,
    needs_foreach: false,
    needs_file_save: false,
    needs_response: true,
    needs_send_endpoint: false,
    needs_print: false,
    needs_writeback: false,
    needs_polling: false,
  });

  const patternById = useMemo(() => new Map((patterns.data ?? []).map((item) => [item.pattern_id, item])), [patterns.data]);
  const certificationById = useMemo(() => new Map((certification.data?.items ?? []).map((item) => [item.pattern_id, item])), [certification.data]);
  const scenarioCards = useMemo(() => (coverage.data?.items ?? []).filter((item) => item.show_in_integration_start), [coverage.data]);

  if (patterns.isPending || coverage.isPending || certification.isPending) return <LoadingState label="Загрузка библиотеки сценариев" />;
  if (patterns.error) return <ErrorState error={patterns.error} />;
  if (coverage.error) return <ErrorState error={coverage.error} />;
  if (certification.error) return <ErrorState error={certification.error} />;

  function submit(event: FormEvent) {
    event.preventDefault();
    recommend.mutate(compactAnswers(answers));
  }

  function startScenario(item: IntegrationCoverageItem) {
    if (!canStartRequirement(item)) return;
    if (item.recommended_pattern) {
      start.mutate(item.recommended_pattern);
      return;
    }
    const directRoute = item.wizard_route ?? item.workbench_route;
    if (directRoute) navigate(directRoute);
  }

  const startError = start.error instanceof Error ? start.error.message : null;
  const recommendError = recommend.error instanceof Error ? recommend.error.message : null;

  return (
    <div className="page-stack integration-start-page">
      <section className="page-header integration-start-hero">
        <span className="eyebrow">Scenario Router</span>
        <h1>Что вы хотите интегрировать?</h1>
        <p>Начните с реальной задачи. OMH подберёт паттерн из coverage matrix, объяснит шаги и откроет только готовый мастер или production workbench.</p>
        <div className="hero-meta">
          <StatusBadge status="ready" label={`${coverage.data?.summary.ready ?? 0} ready`} />
          <StatusBadge status="partial" label={`${coverage.data?.summary.partial ?? 0} partial`} />
          <StatusBadge status="planned" label={`${coverage.data?.summary.planned ?? 0} planned`} />
          <Link className="primary-link" to="/integration-coverage">Матрица покрытия</Link>
          <Link className="primary-link" to="/integration-patterns/certification">Готовность мастеров</Link>
          <Link className="primary-link" to="/docs/core/start/integration-scenarios">Какие интеграции можно настроить</Link>
        </div>
      </section>

      {(startError || recommendError) && <div className="error-state compact">{startError ?? recommendError}</div>}

      <SectionCard title="Выберите по сценарию" description="Карточки берутся из Integration Coverage Matrix. Если сценарий planned или не имеет готового wizard/workbench, старт заблокирован.">
        <section className="scenario-router-grid">
          {scenarioCards.map((card) => {
            const pattern = card.recommended_pattern ? patternById.get(card.recommended_pattern) : undefined;
            const patternCertification = card.recommended_pattern ? certificationById.get(card.recommended_pattern) : undefined;
            return <ScenarioCard key={card.requirement_id} card={card} pattern={pattern} certification={patternCertification} onStart={() => startScenario(card)} starting={start.isPending} />;
          })}
        </section>
      </SectionCard>

      <SectionCard title="Подобрать мастер по вопросам" description="Если не уверены, ответьте на короткие вопросы. Router вызовет /api/integration-patterns/recommend.">
        <form className="questionnaire-grid" onSubmit={submit}>
          <label className="field-label">Кто вызывает OMH?
            <select value={answers.source_system} onChange={(event) => setAnswers({ ...answers, source_system: event.target.value })}>
              <option value="onec">1С</option>
              <option value="external_api">Внешний сайт/API</option>
              <option value="wms">WMS</option>
              <option value="omh_scheduler">OMH сам по расписанию</option>
            </select>
          </label>
          <label className="field-label">Что приходит?
            <select value={answers.input_mode} onChange={(event) => setAnswers({ ...answers, input_mode: event.target.value as QuestionnaireState['input_mode'] })}>
              <option value="json">JSON</option>
              <option value="xml">XML</option>
              <option value="raw_text">Raw text</option>
              <option value="file">Файл</option>
            </select>
          </label>
          <Question label="Нужно читать 1С OData?" value={answers.needs_odata} onChange={(value) => setAnswers({ ...answers, needs_odata: value })} unknown />
          <Question label="Нужно делать несколько запросов по массиву?" value={answers.needs_foreach} onChange={(value) => setAnswers({ ...answers, needs_foreach: Boolean(value) })} />
          <fieldset className="question-card wide">
            <legend>Что нужно в конце?</legend>
            <Check label="Вернуть ответ" checked={answers.needs_response} onChange={(value) => setAnswers({ ...answers, needs_response: value })} />
            <Check label="Отправить дальше" checked={answers.needs_send_endpoint} onChange={(value) => setAnswers({ ...answers, needs_send_endpoint: value })} />
            <Check label="Сохранить файл" checked={answers.needs_file_save} onChange={(value) => setAnswers({ ...answers, needs_file_save: value })} />
            <Check label="Напечатать" checked={answers.needs_print} onChange={(value) => setAnswers({ ...answers, needs_print: value })} />
            <Check label="Записать обратно в 1С" checked={answers.needs_writeback} onChange={(value) => setAnswers({ ...answers, needs_writeback: value })} />
          </fieldset>
          <div className="action-row wide"><button className="primary-button" disabled={recommend.isPending}>Подобрать мастер</button></div>
        </form>
      </SectionCard>

      {recommend.data && (
        <SectionCard title="Рекомендация Scenario Router" description="Паттерны отсортированы по confidence. Откройте детали или стартуйте доступный мастер.">
          <div className="recommendation-list">
            {recommend.data.recommended_patterns.map((item) => {
              const coverageItem = coverage.data?.items.find((candidate) => candidate.recommended_pattern === item.pattern_id && candidate.show_in_integration_start);
              const blockedByCoverage = coverageItem ? !canStartRequirement(coverageItem) : false;
              return (
                <article className="recommendation-card" key={item.pattern_id}>
                  <div>
                    <span className="eyebrow">confidence {Math.round(item.confidence * 100)}%</span>
                    <h3>{localized(item.pattern.title)}</h3>
                    <p>{item.reason}</p>
                    {coverageItem && <small className="muted">Coverage: {localized(coverageItem.title)} · {coverageItem.readiness_score}%</small>}
                  </div>
                  <div className="action-row wrap-actions">
                    <StatusBadge status={coverageItem?.status ?? item.pattern.status} label={coverageItem ? coverageItem.status : (item.pattern.status === 'available' ? 'доступен' : 'скоро')} />
                    <StatusBadge status={certificationById.get(item.pattern_id)?.certification_status} label={certificationStartLabel(certificationById.get(item.pattern_id)?.certification_status)} compact />
                    <Link className="primary-link" to={`/integration-patterns/${item.pattern_id}`}>Детали</Link>
                    <button className="primary-button" disabled={item.pattern.status !== 'available' || blockedByCoverage || start.isPending} onClick={() => start.mutate(item.pattern_id)}>{blockedByCoverage ? 'Подробнее' : 'Открыть мастер'}</button>
                  </div>
                </article>
              );
            })}
          </div>
        </SectionCard>
      )}
    </div>
  );
}

function ScenarioCard({ card, pattern, certification, onStart, starting }: { card: IntegrationCoverageItem; pattern?: IntegrationPattern; certification?: PatternCertification; onStart: () => void; starting: boolean }) {
  const canStart = canStartRequirement(card) && (!pattern || pattern.status === 'available');
  const routeLabel = localized(card.recommended_tool, localized(pattern?.wizard_label, pattern?.recommended_wizard ?? '—'));
  const guideLink = card.recipe_link ?? card.docs_links[0] ?? null;
  const trainingExampleId = card.training_example_ids[0] ?? null;
  return (
    <article className="scenario-card scenario-router-card">
      <div className="scenario-card-head">
        <span className="eyebrow">{card.requirement_id}</span>
        <div className="badge-row">
          <StatusBadge status={card.status} label={`${card.status} · ${card.readiness_score}%`} compact />
          <StatusBadge status={certification?.certification_status} label={certificationStartLabel(certification?.certification_status)} compact />
        </div>
      </div>
      <h3>{localized(card.title)}</h3>
      <dl className="scenario-card-meta">
        <div><dt>Что приходит</dt><dd>{localized(card.input_summary)}</dd></div>
        <div><dt>Что делает OMH</dt><dd>{localized(card.omh_actions_summary)}</dd></div>
        <div><dt>Что получается</dt><dd>{localized(card.result_summary)}</dd></div>
        <div><dt>Мастер</dt><dd>{routeLabel}</dd></div>
      </dl>
      {card.gaps.length > 0 && <small className="muted">Gaps: {card.gaps.slice(0, 2).join(' ')}</small>}
      <div className="action-row wrap-actions">
        <button className="primary-button" disabled={!canStart || starting} onClick={onStart}>{canStart ? 'Настроить' : 'Настроить недоступно'}</button>
        {guideLink ? <Link className="primary-link" to={guideLink}>Открыть инструкцию</Link> : <span className="status-badge muted compact">Инструкция будет добавлена позже</span>}
        {trainingExampleId ? <Link className="primary-link" to={`/training?exampleId=${encodeURIComponent(trainingExampleId)}`}>Попробовать на учебном стенде</Link> : <span className="status-badge muted compact">Учебный пример будет добавлен позже</span>}
        {card.recommended_pattern && <Link className="primary-link" to={`/integration-patterns/${card.recommended_pattern}`}>Открыть план</Link>}
        <Link className="primary-link" to={`/integration-coverage?scenario=${card.requirement_id}`}>Coverage</Link>
      </div>
    </article>
  );
}

function canStartRequirement(item: IntegrationCoverageItem) {
  return Boolean(item.wizard_route ?? item.workbench_route) && startableCoverageStatuses.has(item.status) && startableWizardStatuses.has(item.statuses.wizard);
}

function Question({ label, value, onChange, unknown = false }: { label: string; value: boolean | null; onChange: (value: boolean | null) => void; unknown?: boolean }) {
  return (
    <fieldset className="question-card">
      <legend>{label}</legend>
      <button type="button" className={value === true ? 'active' : ''} onClick={() => onChange(true)}>Да</button>
      <button type="button" className={value === false ? 'active' : ''} onClick={() => onChange(false)}>Нет</button>
      {unknown && <button type="button" className={value === null ? 'active' : ''} onClick={() => onChange(null)}>Не знаю</button>}
    </fieldset>
  );
}

function Check({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return <label className="check-row"><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />{label}</label>;
}

function compactAnswers(value: QuestionnaireState): PatternRecommendRequest {
  return Object.fromEntries(Object.entries(value).filter(([, item]) => item !== null)) as PatternRecommendRequest;
}

function certificationStartLabel(status?: PatternCertificationStatus | null) {
  if (status === 'ready_for_production') return 'Готово';
  if (status === 'ready_for_training') return 'Учебный пример есть';
  if (status === 'partial') return 'Частично';
  if (status === 'not_started') return 'Запланировано';
  if (status === 'deprecated') return 'Deprecated';
  return 'Запланировано';
}
