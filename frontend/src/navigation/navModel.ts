import type { UINavigationItem } from '../api/ui';

export type UIMode = 'simple' | 'advanced' | 'developer';
export type NavGroup = 'Operate' | 'Build' | 'Data Tools' | 'Packages' | 'Settings' | 'Advanced' | 'Developer';

export interface NavModelItem extends UINavigationItem {
  id: string;
  group: NavGroup;
  titleKey: string;
  modes: UIMode[];
  order: number;
}

export const uiModes: UIMode[] = ['simple', 'advanced', 'developer'];
export const uiModeStorageKey = 'omh.ui.mode.v1';

export const groupOrder: NavGroup[] = ['Operate', 'Build', 'Data Tools', 'Packages', 'Settings', 'Advanced', 'Developer'];

export const groupKey: Record<string, string> = {
  Operate: 'nav.sectionOperate',
  Build: 'nav.sectionBuild',
  'Data Tools': 'nav.sectionDataTools',
  Packages: 'nav.sectionPackages',
  Settings: 'nav.sectionSettings',
  Advanced: 'nav.sectionAdvanced',
  Developer: 'nav.sectionDeveloper',
};

const simple: UIMode[] = ['simple', 'advanced', 'developer'];
const advanced: UIMode[] = ['advanced', 'developer'];
const developer: UIMode[] = ['developer'];

export const navModel: NavModelItem[] = [
  nav('docs', 'Operate', 'Documentation', '/docs', 'nav.documentation', simple, 10),
  nav('training', 'Operate', 'Training Sandbox', '/training', 'nav.training', simple, 20, 'omh-package-training'),
  nav('start', 'Operate', 'Start', '/', 'nav.start', simple, 30),
  nav('runtime-monitor', 'Operate', 'Transaction Monitor', '/runtime/monitor', 'nav.transactionMonitor', simple, 40),
  nav('events', 'Operate', 'Event Journal', '/events', 'nav.events', simple, 50),
  nav('incidents', 'Operate', 'Incidents', '/incidents', 'nav.incidents', simple, 60),
  nav('health', 'Operate', 'Health', '/health', 'nav.health', simple, 70),

  nav('onec-cockpit', 'Build', '1C Cockpit', '/onec-cockpit', 'nav.onecCockpit', simple, 10, 'omh-package-onec'),
  nav('request-response', 'Build', 'Request/Response Workbench', '/test-console', 'nav.testConsole', simple, 20),
  nav('odata-connections', 'Build', 'OData Connections', '/odata-connections', 'onec.odataConnections', simple, 30, 'omh-package-onec'),
  nav('odata-explorer', 'Build', 'OData Explorer', '/odata-explorer', 'nav.odataExplorer', simple, 40, 'omh-package-onec'),
  nav('integration-flows', 'Build', 'Integration Flows', '/integration-flows', 'nav.integrationFlows', simple, 50),
  nav('printing', 'Build', 'Printing', '/printing', 'nav.printing', advanced, 60, 'omh-package-printer'),

  nav('packages', 'Packages', 'Packages', '/packages', 'nav.packages', simple, 10),
  nav('production', 'Packages', 'Production', '/production', 'nav.production', simple, 20),
  nav('plugin-store', 'Packages', 'Plugin Store', '/plugin-store', 'nav.pluginStore', advanced, 30),

  nav('business-objects', 'Data Tools', 'Business Objects', '/business-objects', 'nav.businessObjects', advanced, 10),
  nav('resolvers', 'Data Tools', 'Resolvers', '/resolvers', 'nav.resolvers', advanced, 20),
  nav('resolver-cache', 'Data Tools', 'Resolver Cache', '/resolvers/cache', 'nav.resolvers', advanced, 30),
  nav('transforms', 'Data Tools', 'Transforms', '/transforms', 'nav.transforms', advanced, 40),
  nav('business-rules', 'Data Tools', 'Business Rules', '/business-rules', 'nav.businessRules', advanced, 50),
  nav('mappings', 'Data Tools', 'Mappings', '/mappings', 'nav.mappings', advanced, 60),
  nav('test-cases', 'Data Tools', 'Saved Test Cases', '/test-cases', 'nav.savedTestCases', advanced, 70),
  nav('xml-tools', 'Data Tools', 'XML Tools', '/xml-tools', 'nav.xmlTools', advanced, 80, 'omh-package-onec'),

  nav('connectors', 'Settings', 'Connectors', '/connectors', 'nav.connectors', advanced, 10),
  nav('secrets', 'Settings', 'Secrets', '/secrets', 'nav.secrets', advanced, 20, 'omh-package-secrets'),
  nav('users', 'Settings', 'Users', '/users', 'nav.users', advanced, 30, 'omh-package-auth'),
  nav('auth-settings', 'Settings', 'Auth', '/auth-settings', 'nav.authSettings', advanced, 40, 'omh-package-auth'),
  nav('environments', 'Settings', 'Environments', '/environments', 'nav.environments', advanced, 50),
  nav('change-sets', 'Settings', 'Change Sets', '/change-sets', 'nav.changeSets', advanced, 60),
  nav('notifications', 'Settings', 'Notifications', '/notifications', 'nav.notifications', advanced, 70),
  nav('retention', 'Settings', 'Retention', '/retention', 'nav.retention', advanced, 80),
  nav('audit', 'Settings', 'Audit Log', '/audit', 'nav.auditLog', advanced, 90),

  nav('runtime-queue', 'Advanced', 'Integration Queue', '/runtime/queue', 'nav.integrationQueue', advanced, 10),
  nav('runtime-dlq', 'Advanced', 'Dead Letter Queue', '/runtime/dlq', 'nav.deadLetterQueue', advanced, 20),
  nav('operation-keys', 'Advanced', 'Operation Keys', '/operation-keys', 'nav.operationKeys', advanced, 30),
  nav('scenario-library', 'Advanced', 'Scenario Library', '/scenario-library', 'nav.scenarioLibrary', advanced, 40),
  nav('integration-designer', 'Advanced', 'Integration Designer', '/integration-designer', 'nav.integrationDesigner', advanced, 50, 'omh-package-onec'),
  nav('onec-scenarios', 'Advanced', '1C Scenarios', '/onec-scenarios', 'nav.onecScenarios', advanced, 60, 'omh-package-onec'),
  nav('onec-workbench', 'Advanced', '1C Workbench', '/onec-workbench', 'nav.onecWorkbench', advanced, 70, 'omh-package-onec'),
  nav('polling', 'Advanced', 'Polling Jobs', '/polling', 'nav.polling', advanced, 80),
  nav('maintenance', 'Advanced', 'Maintenance', '/maintenance', 'nav.maintenance', advanced, 90),

  nav('integration-bus', 'Developer', 'Integration Bus', '/integration-bus', 'nav.integrationBus', developer, 10),
  nav('workflows', 'Developer', 'Workflows', '/workflows', 'nav.workflows', developer, 20),
  nav('execution-steps', 'Developer', 'Execution Steps', '/execution/steps', 'nav.executionSteps', developer, 30),
  nav('i18n-debug', 'Developer', 'i18n Debug', '/i18n-debug', 'navigation.i18nDebug', developer, 40),
];

export const fallbackNavigation: UINavigationItem[] = navModel.map(({ group, title, route, package_id, enabled, installed, advanced }) => ({
  group,
  title,
  route,
  package_id,
  enabled,
  installed,
  advanced,
}));

export const routeKey: Record<string, string> = Object.fromEntries(navModel.map((item) => [item.route, item.titleKey]));

const modelByRoute = new Map(navModel.map((item) => [item.route, item]));

export function normalizeNavigation(apiItems: UINavigationItem[] = fallbackNavigation): NavModelItem[] {
  const apiByRoute = new Map(apiItems.map((item) => [item.route, item]));
  const modeled = navModel.map((item) => {
    const apiItem = apiByRoute.get(item.route);
    return apiItem ? { ...item, enabled: apiItem.enabled, installed: apiItem.installed, package_id: apiItem.package_id ?? item.package_id } : item;
  });
  const unknown = apiItems
    .filter((item) => !modelByRoute.has(item.route))
    .map((item, index): NavModelItem => ({
      ...item,
      id: `api-${item.route}`,
      group: item.advanced ? 'Advanced' : 'Build',
      titleKey: routeKey[item.route] ?? '',
      modes: item.advanced ? advanced : simple,
      order: 900 + index,
    }));
  return [...modeled, ...unknown].sort((left, right) => {
    const groupDiff = groupIndex(left.group) - groupIndex(right.group);
    return groupDiff || left.order - right.order || left.title.localeCompare(right.title);
  });
}

export function modeAllows(item: NavModelItem, mode: UIMode) {
  return item.modes.includes(mode);
}

export function navGroupForRoute(route: string): NavGroup | null {
  return modelByRoute.get(route)?.group ?? null;
}

function nav(id: string, group: NavGroup, title: string, route: string, titleKey: string, modes: UIMode[], order: number, packageId: string | null = null): NavModelItem {
  const minMode = modes[0];
  return {
    id,
    group,
    title,
    route,
    titleKey,
    modes,
    order,
    package_id: packageId,
    enabled: !packageId,
    installed: packageId ? false : undefined,
    advanced: minMode !== 'simple',
  };
}

function groupIndex(group: string) {
  const index = groupOrder.indexOf(group as NavGroup);
  return index === -1 ? 99 : index;
}
