import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { eventsApi } from '../api/events';
import { incidentsApi } from '../api/incidents';
import { healthApi } from '../api/health';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { HealthCard } from '../components/HealthCard';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { useT } from '../i18n/useI18n';
import { formatDateTime } from '../utils';

const scenarioCards = [
  {
    title: 'Подобрать сценарий',
    input: 'Кто обращается, что приходит и какой результат нужен',
    output: 'Рекомендованный мастер, readiness, обучение, документация и пробелы в покрытии',
    does: 'Маршрутизирует задачу к правильному workbench без выбора endpoint, flow или trigger key вручную.',
    best: 'Новая интеграция, когда понятна бизнес-задача, но ещё не выбран технический шаблон.',
    to: '/integration-start',
    cta: 'Открыть Scenario Router',
    primary: true,
  },
  {
    title: 'Проверить OData',
    input: 'Номер заказа, ИНН, ссылка, дата или другие поля запроса',
    output: 'Найденные записи, выбранные поля или шаг для будущей интеграции',
    does: 'Помогает выбрать подключение, ресурс, фильтр, $select и сохранить результат в сценарий.',
    best: 'Поиск заказа, контрагента, остатков, строки табличной части.',
    to: '/odata-explorer',
    cta: 'Открыть OData Master',
  },
  {
    title: 'Посмотреть интеграции',
    input: 'Сохранённые flow и опубликованные endpoint',
    output: 'Полный маршрут: trigger key, шаги, финальное действие, caller response',
    does: 'Показывает, что реально будет выполнено при входящем POST.',
    best: 'Проверка перед запуском или объяснение оператору, как работает сценарий.',
    to: '/integration-flows',
    cta: 'Открыть интеграции',
  },
  {
    title: 'Проверить результат выполнения',
    input: 'Событие, run_id, timeline или ошибка интеграции',
    output: 'Запросы, ответы, шаги выполнения и понятная диагностика',
    does: 'Открывает журнал событий и timeline для проверки реального запуска.',
    best: 'После тестового POST или при разборе ошибки.',
    to: '/events',
    cta: 'Открыть журнал',
  },
];

export function DashboardPage() {
  const t = useT();
  const summary = useQuery({ queryKey: ['dashboard-summary'], queryFn: () => eventsApi.dashboardSummary() });
  const health = useQuery({ queryKey: ['health-dashboard'], queryFn: healthApi.dashboard, retry: false });

  if (summary.isLoading) return <LoadingState />;
  if (summary.error) return <ErrorState error={summary.error} />;

  const data = summary.data;
  const failedEvents = data?.latest_failures ?? [];
  const eventsToday = data?.events_today ?? 0;
  const failedToday = data?.failed_today ?? 0;
  const retryWaiting = data?.retry_waiting ?? 0;
  const openIncidents = data?.open_incidents ?? 0;
  const queueBacklog = data?.queue_backlog ?? 0;
  const queueProcessing = data?.queue_processing ?? 0;
  const timezone = data?.timezone ?? 'UTC';

  return (
    <div className="page-stack">
      <header className="hero-panel dashboard-hero scenario-start-hero">
        <div>
          <span className="eyebrow">Старт интеграции</span>
          <h1>Что вы хотите интегрировать?</h1>
          <p>Начинайте с рабочего действия: создать интеграцию, проверить OData, посмотреть опубликованный flow или разобрать выполнение. Низкоуровневые инструменты перенесены в расширенный режим.</p>
        </div>
        <div className="hero-instrument"><span>{failedToday}</span><small>{t('dashboard.activeFailures')} (сегодня)</small></div>
      </header>

      <section className="scenario-card-grid start-scenario-grid" data-tour="create-integration">
        {scenarioCards.map((card) => (
          <Link key={card.title} className={`scenario-card ${card.primary ? 'primary' : ''}`} to={card.to}>
            <span className="eyebrow">{card.primary ? 'Частый сценарий' : 'Сценарий'}</span>
            <h2>{card.title}</h2>
            <dl>
              <div><dt>Что приходит</dt><dd>{card.input}</dd></div>
              <div><dt>Что нужно вернуть или сделать</dt><dd>{card.output}</dd></div>
              <div><dt>Что делает OMH</dt><dd>{card.does}</dd></div>
              <div><dt>Лучше всего для</dt><dd>{card.best}</dd></div>
            </dl>
            <strong>{card.cta}</strong>
          </Link>
        ))}
      </section>

      <section className="panel purpose-banner">
        <span className="eyebrow">Принцип OMH</span>
        <h2>Пользователь идёт от задачи, а не от технического термина</h2>
        <p>Если вы знаете только “кто обращается”, “что приходит”, “что нужно найти или отправить” и “что вернуть”, этого достаточно для старта. Endpoint, route, workflow, saved test case и другие внутренние сущности остаются доступными в расширенном режиме.</p>
        <div className="action-row wrap-actions">
          <Link className="primary-link" to="/integration-start">Подобрать сценарий</Link>
          <Link className="ghost-button" to="/training">Пройти учебный пример</Link>
          <Link className="ghost-button" to="/docs/core/start/integration-scenarios">Открыть примеры</Link>
        </div>
      </section>

      <section className="metric-grid">
        <Metric label={`${t('dashboard.eventsToday')} (${timezone})`} value={eventsToday} />
        <Metric label={`${t('dashboard.failed')} (${timezone})`} value={failedToday} tone="bad" />
        <Metric label={t('dashboard.retryWaiting')} value={retryWaiting} tone="warn" />
        <Metric label={t('dashboard.openIncidents')} value={openIncidents} tone="info" />
        <Metric label={`${t('dashboard.queueSize')} (backlog: ${queueBacklog}, proc: ${queueProcessing})`} value={queueBacklog} />
      </section>

      <section className="dashboard-grid">
        <div className="panel wide-panel">
          <div className="panel-toolbar"><h2>{t('dashboard.latestFailures')} (вся история)</h2><Link className="ghost-link" to="/events">{t('dashboard.openJournal')}</Link></div>
          {failedEvents.length === 0 ? <EmptyState title={t('dashboard.noFailedEvents')} detail={t('dashboard.noFailedEventsDetail')} /> : (
            <div className="failure-list">
              {failedEvents.map((event) => (
                <Link key={event.id} to={`/events/${event.id}`} className="failure-row">
                  <StatusBadge status={event.status} />
                  <strong>{event.event_type}</strong>
                  <span>{event.entity_type} #{event.entity_id}</span>
                  <span>{event.source_system} → {event.target_system ?? t('common.unknown')}</span>
                  <span>{formatDateTime(event.created_at)}</span>
                </Link>
              ))}
            </div>
          )}
        </div>
        <div className="panel">
          <div className="panel-toolbar"><h2>{t('dashboard.healthSummary')}</h2><Link className="ghost-link" to="/health">{t('common.details')}</Link></div>
          {health.isLoading ? (
            <LoadingState label="Загрузка статуса здоровья..." />
          ) : health.error ? (
            <div className="error-state compact">Сервис здоровья временно недоступен</div>
          ) : health.data?.sites.length ? (
            health.data.sites.slice(0, 3).map((site) => <HealthCard key={site.name} site={site} />)
          ) : (
            <EmptyState title={t('dashboard.noHealthData')} detail={t('dashboard.noHealthDataDetail')} />
          )}
          {health.data?.components && (
            <div className="component-strip">
              {health.data.components.slice(0, 5).map((component) => (
                <span key={`${component.type}-${component.name}`}>{component.name}<StatusBadge status={component.status} compact /></span>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value, tone = 'neutral' }: { label: string; value: number; tone?: string }) {
  return <div className={`metric-card ${tone}`}><span>{label}</span><strong>{value.toLocaleString()}</strong></div>;
}
