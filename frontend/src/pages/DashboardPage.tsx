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
import { OnboardingCard } from '../features/onboarding/OnboardingCard';
import { useT } from '../i18n/useI18n';
import { formatDateTime } from '../utils';

const scenarioCards = [
  {
    title: 'Внешний сервис обращается к OMH и ждёт ответ',
    input: 'POST/GET запрос: JSON, XML или текст',
    output: 'JSON/XML/raw ответ, proxy-ответ OData/API или event_id',
    does: 'Принимает запрос, показывает поля, делает OData/API/XML шаги, собирает ответ и даёт timeline.',
    best: 'Сайт, WMS, терминал, мобильное приложение или внешний API.',
    to: '/test-console?mode=build',
    cta: 'Собрать приём и ответ',
    primary: true,
  },
  {
    title: '1C отправляет данные во внешний сервис',
    input: 'Документ, событие или ручной HTTP-запрос из 1C',
    output: 'Запрос во внешний API, печать, событие или ответ в 1C',
    does: 'Ведёт через выбор источника, авторизации, преобразования, теста и публикации.',
    best: 'Маркировка, DNP, CRM, WMS, личный кабинет, уведомления.',
    to: '/onec-cockpit/new',
    cta: 'Открыть мастер 1C',
  },
  {
    title: 'Нужно прочитать данные из 1C OData',
    input: 'Номер заказа, ИНН, ссылка, дата или другие поля запроса',
    output: 'Найденные записи, выбранные поля или шаг для будущей интеграции',
    does: 'Помогает выбрать подключение, ресурс, фильтр, $select и сохранить результат в сценарий.',
    best: 'Поиск заказа, контрагента, остатков, строки табличной части.',
    to: '/odata-explorer',
    cta: 'Настроить OData',
  },
  {
    title: 'Нужен XML обмен',
    input: 'XML от 1C, EDI, банка, SOAP-like сервиса или старой системы',
    output: 'XML ответ, JSON ответ, пересылка в OData/API или событие',
    does: 'Разбирает XML, показывает поля, помогает собрать XPath-маппинг и ответ без ручной магии.',
    best: 'HTTP-сервисы 1C, УПД, legacy-интеграции, регламентированные обмены.',
    to: '/test-console?mode=build&input=xml',
    cta: 'Собрать XML сценарий',
  },
  {
    title: 'Нужно напечатать этикетку',
    input: 'Заказ, пул кодов, событие 1C или ручной тест',
    output: 'Задание на принтер, журнал события, повтор при ошибке',
    does: 'Связывает интеграционный сценарий с пакетом печати и показывает результат в мониторинге.',
    best: 'Склад, производство, маркировка, Zebra/этикетки.',
    to: '/printing',
    cta: 'Открыть печать',
  },
  {
    title: 'Сначала пройти обучение',
    input: 'Учебный кейс и безопасные примеры',
    output: 'Понимание сценария до настройки продакшена',
    does: 'Проводит по входящему запросу, OData, ответу, тесту и диагностике.',
    best: 'Новый пользователь, новый сотрудник, подготовка к внедрению.',
    to: '/training',
    cta: 'Начать обучение',
  },
];

export function DashboardPage() {
  const t = useT();
  const events = useQuery({ queryKey: ['events'], queryFn: eventsApi.list });
  const incidents = useQuery({ queryKey: ['incidents'], queryFn: incidentsApi.list });
  const health = useQuery({ queryKey: ['health-dashboard'], queryFn: healthApi.dashboard });

  const isLoading = events.isLoading || incidents.isLoading || health.isLoading;
  const error = events.error ?? incidents.error ?? health.error;
  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState error={error} />;

  const eventRows = events.data ?? [];
  const incidentRows = incidents.data ?? [];
  const failed = eventRows.filter((event) => event.status === 'failed');
  const retry = eventRows.filter((event) => event.status === 'retry_waiting');
  const openIncidents = incidentRows.filter((incident) => incident.status === 'open');

  return (
    <div className="page-stack">
      <header className="hero-panel dashboard-hero scenario-start-hero">
        <div>
          <span className="eyebrow">Старт интеграции</span>
          <h1>Что вы хотите интегрировать?</h1>
          <p>Выберите реальный сценарий. OMH откроет нужный мастер, а маршруты, ключи, шаги и технические детали останутся под капотом до момента, когда они действительно нужны.</p>
        </div>
        <div className="hero-instrument"><span>{failed.length}</span><small>{t('dashboard.activeFailures')}</small></div>
      </header>

      <OnboardingCard />

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
        <p>Если вы знаете только “кто обращается”, “что приходит”, “что нужно найти или отправить” и “что вернуть”, этого достаточно для старта. Низкоуровневые сущности доступны в расширенном режиме, но не должны быть первой точкой входа.</p>
      </section>

      <section className="metric-grid">
        <Metric label={t('dashboard.eventsToday')} value={eventRows.length} />
        <Metric label={t('dashboard.failed')} value={failed.length} tone="bad" />
        <Metric label={t('dashboard.retryWaiting')} value={retry.length} tone="warn" />
        <Metric label={t('dashboard.openIncidents')} value={openIncidents.length} tone="info" />
        <Metric label={t('dashboard.queueSize')} value={0} />
      </section>

      <section className="dashboard-grid">
        <div className="panel wide-panel">
          <div className="panel-toolbar"><h2>{t('dashboard.latestFailures')}</h2><Link className="ghost-link" to="/events">{t('dashboard.openJournal')}</Link></div>
          {failed.length === 0 ? <EmptyState title={t('dashboard.noFailedEvents')} detail={t('dashboard.noFailedEventsDetail')} /> : (
            <div className="failure-list">
              {failed.slice(0, 6).map((event) => (
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
          {health.data?.sites.length ? health.data.sites.slice(0, 3).map((site) => <HealthCard key={site.name} site={site} />) : <EmptyState title={t('dashboard.noHealthData')} detail={t('dashboard.noHealthDataDetail')} />}
          <div className="component-strip">
            {health.data?.components.slice(0, 5).map((component) => <span key={`${component.type}-${component.name}`}>{component.name}<StatusBadge status={component.status} compact /></span>)}
          </div>
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value, tone = 'neutral' }: { label: string; value: number; tone?: string }) {
  return <div className={`metric-card ${tone}`}><span>{label}</span><strong>{value.toLocaleString()}</strong></div>;
}
