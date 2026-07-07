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
  'integration-flows': { id: 'integration-flows', title: 'Integration Flow Builder', description: 'Create no-code integration flows with endpoint, matcher, lookup, transform and target action.', actions: ['Install visual preset', 'Create flow', 'Test matcher', 'Open visual builder'], example: 'Run 1C POST -> API example', docId: 'integration-flows', tourId: 'visual-flow-builder-first-tour' },
  'test-console': { id: 'test-console', title: 'Test Console', description: 'Send real or dry-run requests through configured endpoints and open the resulting timeline.', actions: ['Select endpoint', 'Paste payload', 'Dry run', 'Open timeline'], docId: 'test-console', tourId: 'test-console-first-tour' },
  connectors: { id: 'connectors', title: 'Connectors', description: 'Register external systems through stable connector contracts and keep secrets out of JSON.', actions: ['Create 1C connector', 'Validate config', 'Run healthcheck'], docId: 'onec.connector' },
  packages: { id: 'packages', title: 'Packages', description: 'Packages add product capabilities. Installed and enabled packages expose runtime pages.', actions: ['Open Plugin Store', 'Install 1C', 'Install Auth if needed'], docId: 'packages.store' },
  queue: { id: 'queue', title: 'Queue and DLQ', description: 'Queue-first runtime gives retries, DLQ recovery and transaction visibility.', actions: ['Inspect attempts', 'Retry now', 'Open timeline', 'Move to DLQ'], docId: 'queue' },
  timeline: { id: 'timeline', title: 'Timeline and errors', description: 'Timeline shows every run, step, artifact and original external error for one event.', actions: ['Inspect failed step', 'Open artifact', 'Replay', 'Dry run'], docId: 'timeline.errors', tourId: 'event-timeline-first-tour' },
  secrets: { id: 'secrets', title: 'Secrets Store', description: 'Store passwords and tokens as secret references instead of raw connector JSON values.', actions: ['Create secret', 'Copy reference', 'Use in connector'], docId: 'secrets.overview' },
  auth: { id: 'auth', title: 'Auth package', description: 'Optional UI access control. It protects the web app without touching integrations.', actions: ['Install package', 'Create first user', 'Save recovery keys'], docId: 'auth.install' },
  production: { id: 'production', title: 'Production safety', description: 'Use backups, doctor checks and update mode before changing a live installation.', actions: ['Export config', 'Run doctor', 'Enable update mode'], docId: 'production.safety' },
  audit: { id: 'audit', title: 'Audit log', description: 'Audit log tracks configuration changes and operator actions.', actions: ['Filter changes', 'Open details', 'Compare before/after'], docId: 'audit.log' },
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
  return null;
}

export function topicDocUrl(topic: HelpTopic) {
  return docUrl(topic.docId);
}
