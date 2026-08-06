import { docUrl } from '../docs/docLinks';
import type { TourId } from '../tours/tourRegistry';

export interface HelpTopic {
  id: string;
  title: string;
  description: string;
  actions: string[];
  example?: string;
  docId: string;
  tourId?: TourId;
}

export const helpTopics: Record<string, HelpTopic> = {
  dashboard: { id: 'dashboard', title: 'Where should I start?', description: 'Use onboarding when this is the first environment or when you need a repeatable setup path.', actions: ['Open onboarding', 'Install packages', 'Create connector', 'Run first example'], docId: 'core.overview' },
  'onec-cockpit': { id: 'onec-cockpit', title: '1C Cockpit', description: 'Cockpit is the command center for 1C integrations: presets, health, recent events and quick starts.', actions: ['Create integration', 'Check connector health', 'Open recent timeline'], example: 'Run 1C POST -> API example', docId: 'onec.cockpit', tourId: 'onec-cockpit-first-tour' },
  'integration-master': { id: 'integration-master', title: 'Мастер интеграции', description: 'Начинайте интеграцию с входящего контракта: сценарий, sample, поля, route key, business key и endpoint slug.', actions: ['Выберите сценарий', 'Разберите sample', 'Проверьте поля', 'Сохраните draft'], example: 'DnP CHZ input contract', docId: 'integration-master' },
  'odata-explorer': { id: 'odata-explorer', title: 'Мастер OData-интеграции', description: 'Соберите входящий запрос, OData-шаги, foreach, payload и сохраните рабочую интеграцию.', actions: ['Вставьте пример запроса', 'Добавьте OData-шаги', 'Выберите итоговое действие', 'Проверьте и сохраните'], example: 'DnP CHZ code pool sync', docId: 'onec.odata-master', tourId: 'odata-explorer-first-tour' },
  'xml-tools': { id: 'xml-tools', title: 'XML Tools', description: 'Validate, hash, diff and forward raw XML without losing the original payload.', actions: ['Paste XML', 'Validate structure', 'Compare hash', 'Forward raw body'], example: 'Run XML raw bridge example', docId: 'onec.xml-tools' },
  'integration-flows': { id: 'integration-flows', title: 'Integration Flow Builder', description: 'No-code цепочки: чтение полей, разбор (extract), фильтрация массивов, условия с ветвлением, foreach-отправка, сборка JSON/XML, вызов endpoint, операции из каталога и sub-flow. Инспектор переменных и проверка путей по sample.', actions: ['Install visual preset', 'Add condition or filter step', 'Preview and open the variables inspector', 'Проверить пути по sample'], example: 'Filter rows by item.type -> foreach send -> XML response', docId: 'integration-flows', tourId: 'visual-flow-builder-first-tour' },
  'test-console': { id: 'test-console', title: 'Test Console', description: 'Send real or dry-run requests through configured endpoints and open the resulting timeline.', actions: ['Select endpoint', 'Paste payload', 'Dry run', 'Open timeline'], docId: 'test-console', tourId: 'test-console-first-tour' },
  connectors: { id: 'connectors', title: 'Connectors', description: 'Register external systems through stable connector contracts and keep secrets out of JSON.', actions: ['Create 1C connector', 'Validate config', 'Run healthcheck'], docId: 'onec.connector' },
  packages: { id: 'packages', title: 'Packages', description: 'Packages add product capabilities. Installed and enabled packages expose runtime pages.', actions: ['Open Plugin Store', 'Install 1C', 'Install Auth if needed'], docId: 'packages.store' },
  queue: { id: 'queue', title: 'Queue and DLQ', description: 'Queue-first runtime gives retries, DLQ recovery and transaction visibility.', actions: ['Inspect attempts', 'Retry now', 'Open timeline', 'Move to DLQ'], docId: 'queue' },
  timeline: { id: 'timeline', title: 'Timeline and errors', description: 'Timeline shows every run, step, artifact and original external error for one event.', actions: ['Inspect failed step', 'Open artifact', 'Replay', 'Dry run'], docId: 'timeline.errors', tourId: 'event-timeline-first-tour' },
  secrets: { id: 'secrets', title: 'Secrets Store', description: 'Store passwords and tokens as secret references instead of raw connector JSON values.', actions: ['Create secret', 'Copy reference', 'Use in connector'], docId: 'secrets.overview' },
  auth: { id: 'auth', title: 'Auth package', description: 'Optional UI access control. It protects the web app without touching integrations.', actions: ['Install package', 'Create first user', 'Save recovery keys'], docId: 'auth.install' },
  production: { id: 'production', title: 'Production safety', description: 'Use backups, doctor checks and update mode before changing a live installation.', actions: ['Export config', 'Run doctor', 'Enable update mode'], docId: 'production.safety' },
  audit: { id: 'audit', title: 'Audit log', description: 'Audit log tracks configuration changes and operator actions.', actions: ['Filter changes', 'Open details', 'Compare before/after'], docId: 'audit.log' },
  docs: { id: 'docs', title: 'Документация и обучение', description: 'Документация устроена как путь: сначала понять сценарий, затем пройти урок, затем запустить пример в Training Sandbox.', actions: ['Open learning path', 'Run training example', 'Use troubleshooting by symptom'], example: '1C beginner path -> Training Sandbox -> Test Console -> Timeline', docId: 'core.overview' },
  training: { id: 'training', title: 'Training Sandbox', description: 'Безопасная песочница с mock 1C/OData/DNP/Printer. Нужна, чтобы пользователь мог учиться без реальной 1C и внешних сервисов.', actions: ['Install sandbox', 'Run example', 'Open Test Console', 'Inspect Timeline'], example: 'training.onec.post_two_odata_to_dnp', docId: 'training.sandbox' },
  'integration-start': { id: 'integration-start', title: 'Scenario Router', description: 'Начинайте не с endpoint или connector, а с бизнес-сценария. Router покажет готовность, мастер, docs и training example.', actions: ['Pick scenario card', 'Answer questionnaire', 'Open available wizard', 'Check coverage gaps'], example: 'External API -> OData lookup -> response', docId: 'integration-scenarios' },
  'integration-coverage': { id: 'integration-coverage', title: 'Coverage Matrix', description: 'Матрица показывает, какие сценарии готовы, частичные или запланированы, и что ещё мешает production-ready запуску.', actions: ['Filter by status', 'Open scenario', 'Open docs', 'Start training example'], docId: 'integration-coverage' },
  'connection-center': { id: 'connection-center', title: 'Connection Center', description: 'Connection Profile отвечает только за “куда подключаться”: 1C, REST API, printer, SMB или local directory. Действия поверх подключения живут в Operation Catalog.', actions: ['Create connection', 'Save and test', 'Create operation', 'Use secret references'], example: 'OData ERP + DNP API + LINE-1 Printer', docId: 'connection-center' },
  'operation-catalog': { id: 'operation-catalog', title: 'Operation Catalog', description: 'Operation Profile отвечает за “что сделать”: method, path, headers, body type, success condition and extractors.', actions: ['Choose connection', 'Define operation path', 'Set success condition', 'Dry-run operation', 'Create mapping'], example: 'POST /api/v2/integrations/omh/chz/codes/import', docId: 'operation-catalog' },
  'mapping-center': { id: 'mapping-center', title: 'Data Contract & Mapping Center', description: 'Контракт описывает целевые поля, mapping объясняет откуда взять значения: request, OData result, foreach array or constant.', actions: ['Choose target contract', 'Map source variables', 'Preview payload', 'Validate before save'], example: 'codes -> payload.rows', docId: 'data-contracts-and-mappings' },
  'marking-code-pools': { id: 'marking-code-pools', title: 'Пулы кодов ЧЗ', description: 'Рабочее место оператора ЧЗ: приём пулов из 1С, архив и отправка в DnP/лазер, маршрутизация кодов по правилам, регистрация агрегаций и получение упакованных кодов из DnP для документа «Нанесение и ввод в оборот».', actions: ['Проверьте настройки', 'Настройте правила на вкладке Маршрутизация', 'Сделайте preview на вкладке Тест', 'Проверьте журнал экспортов'], example: 'Правило: GTIN начинается с 04646 -> лазер линии 1 + HTTP-сервис', docId: 'chz.marking-code-pools' },
  'scenario-library': { id: 'scenario-library', title: 'Scenario Library', description: 'Каталог готовых сценариев. Используйте preview перед установкой, чтобы увидеть создаваемые endpoints, flows and operations.', actions: ['Preview scenario', 'Install scenario', 'Open created flow'], docId: 'scenario-library' },
  'business-rules': { id: 'business-rules', title: 'Business Rules', description: 'Наборы правил без кода: условие (поле — оператор — значение) и действия (переменная, маршрут, пропуск шага, ошибка, retry). Редактор визуальный, проверка на примере до сохранения.', actions: ['Создайте набор правил', 'Добавьте условие и действие', 'Проверьте через Test на примере', 'Сохраните draft'], example: 'pool_type равно DNP -> Направить в систему DnP Service', docId: 'integration-flows' },
  'data-inbox': { id: 'data-inbox', title: 'Приемник данных (ТСД)', description: 'Шаблоны приема данных без кода: обязательные поля и политика их отсутствия, хранение по сроку или всегда, записи с просмотром/правкой/повторной отправкой.', actions: ['Создайте шаблон', 'Укажите обязательные поля', 'Проверьте на примере', 'Отправьте данные с ТСД на endpoint'], example: 'POST /api/inbox/tsd-priemka с order_number и qty', docId: 'tsd-data-inbox' },
  'sql-console': { id: 'sql-console', title: 'SQL-консоль', description: 'SELECT-запросы к базе OMH только на чтение. Запрещенные слова и мультистейтменты блокируются с понятной ошибкой. Результат можно выгрузить в CSV.', actions: ['Выберите пример запроса', 'Выполните SELECT', 'Экспортируйте результат в CSV'], example: 'select status, count(*) from inbox_records group by status', docId: 'tsd-data-inbox' },
  'federation': { id: 'federation', title: 'Федерация (холдинг)', description: 'Центр раздает конфиг интеграций филиалам без секретов. Филиал забирает его по расписанию или кнопкой — обновление в центре раскатывается на все филиалы одним кликом.', actions: ['Центр: задайте FEDERATION_TOKEN', 'Филиал: укажите URL центра и токен', 'Нажмите «Синхронизировать сейчас»', 'Проверьте историю синхронизаций'], example: 'GET /api/federation/config-bundle с X-OMH-Token', docId: 'federation-holding' },
};

export function helpForPath(pathname: string): HelpTopic | null {
  if (pathname === '/') return helpTopics.dashboard;
  if (pathname.startsWith('/onec-cockpit')) return helpTopics['onec-cockpit'];
  if (pathname.startsWith('/master')) return helpTopics['integration-master'];
  if (pathname.startsWith('/odata-explorer')) return helpTopics['odata-explorer'];
  if (pathname.startsWith('/xml-tools')) return helpTopics['xml-tools'];
  if (pathname.startsWith('/integration-flows')) return helpTopics['integration-flows'];
  if (pathname.startsWith('/test-console')) return helpTopics['test-console'];
  if (pathname.startsWith('/connectors')) return helpTopics.connectors;
  if (pathname.startsWith('/packages') || pathname.startsWith('/plugin-store')) return helpTopics.packages;
  if (pathname.startsWith('/runtime/queue') || pathname.startsWith('/runtime/dlq') || pathname.startsWith('/runtime/monitor')) return helpTopics.queue;
  if (pathname.startsWith('/events/')) return helpTopics.timeline;
  if (pathname.startsWith('/secrets')) return helpTopics.secrets;
  if (pathname.startsWith('/users') || pathname.startsWith('/auth-settings')) return helpTopics.auth;
  if (pathname.startsWith('/production') || pathname.startsWith('/maintenance')) return helpTopics.production;
  if (pathname.startsWith('/audit')) return helpTopics.audit;
  if (pathname.startsWith('/docs')) return helpTopics.docs;
  if (pathname.startsWith('/training')) return helpTopics.training;
  if (pathname.startsWith('/integration-start')) return helpTopics['integration-start'];
  if (pathname.startsWith('/integration-coverage') || pathname.startsWith('/integration-patterns/certification')) return helpTopics['integration-coverage'];
  if (pathname.startsWith('/connection-center')) return helpTopics['connection-center'];
  if (pathname.startsWith('/operation-catalog')) return helpTopics['operation-catalog'];
  if (pathname.startsWith('/mapping-center')) return helpTopics['mapping-center'];
  if (pathname.startsWith('/marking-code-pools')) return helpTopics['marking-code-pools'];
  if (pathname.startsWith('/scenario-library')) return helpTopics['scenario-library'];
  if (pathname.startsWith('/business-rules') || pathname.startsWith('/runtime/business-rules')) return helpTopics['business-rules'];
  if (pathname.startsWith('/data-inbox')) return helpTopics['data-inbox'];
  if (pathname.startsWith('/sql-console')) return helpTopics['sql-console'];
  if (pathname.startsWith('/federation')) return helpTopics['federation'];
  return null;
}

export function topicDocUrl(topic: HelpTopic) {
  return docUrl(topic.docId);
}
