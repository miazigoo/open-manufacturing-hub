import { useMemo, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { API_BASE_URL } from '../api/client';
import { uiApi, type UINavigationItem } from '../api/ui';
import { ProductionBanner } from './ProductionBanner';
import { UserMenu } from '../features/auth/UserMenu';
import { ContextHelpButton } from '../features/help/ContextHelpButton';
import { helpForPath } from '../features/help/helpRegistry';
import { useI18n, useT } from '../i18n/useI18n';
import { languageMeta } from '../i18n/dictionary';
import type { Language } from '../i18n/dictionary';

const languages: Language[] = ['ru', 'en', 'zh'];
type UIMode = 'simple' | 'advanced' | 'developer';
const uiModes: UIMode[] = ['simple', 'advanced', 'developer'];
const uiModeStorageKey = 'omh.ui.mode.v1';

const fallbackNavigation: UINavigationItem[] = [
  { group: 'Operate', title: 'Documentation', route: '/docs', package_id: null, enabled: true, advanced: false },
  { group: 'Operate', title: 'Onboarding', route: '/onboarding', package_id: null, enabled: true, advanced: false },
  { group: 'Operate', title: 'Dashboard', route: '/', package_id: null, enabled: true, advanced: false },
  { group: 'Operate', title: 'Transaction Monitor', route: '/runtime/monitor', package_id: null, enabled: true, advanced: false },
  { group: 'Operate', title: 'Audit Log', route: '/audit', package_id: null, enabled: true, advanced: false },
  { group: 'Operate', title: 'Event Journal', route: '/events', package_id: null, enabled: true, advanced: false },
  { group: 'Build', title: '1C Integration Cockpit', route: '/onec-cockpit', package_id: 'omh-package-onec', enabled: false, installed: false, advanced: false },
  { group: 'Build', title: 'Integration Flows', route: '/integration-flows', package_id: null, enabled: true, advanced: false },
  { group: 'Data Tools', title: 'OData Explorer', route: '/odata-explorer', package_id: 'omh-package-onec', enabled: false, installed: false, advanced: false },
  { group: 'Packages', title: 'Packages', route: '/packages', package_id: null, enabled: true, advanced: false },
  { group: 'Advanced', title: 'Connectors', route: '/connectors', package_id: null, enabled: true, advanced: true },
  { group: 'Advanced', title: 'Secrets', route: '/secrets', package_id: 'omh-package-secrets', enabled: false, installed: false, advanced: true },
  { group: 'Advanced', title: 'Environments', route: '/environments', package_id: null, enabled: true, advanced: true },
  { group: 'Advanced', title: 'Change Sets', route: '/change-sets', package_id: null, enabled: true, advanced: true },
];

const groupKey: Record<string, string> = {
  Operate: 'nav.sectionOperate',
  Build: 'nav.sectionBuild',
  'Data Tools': 'nav.sectionDataTools',
  Packages: 'nav.sectionPackages',
  Settings: 'nav.sectionSettings',
  Advanced: 'nav.sectionAdvanced',
  Developer: 'nav.sectionDeveloper',
};

const routeKey: Record<string, string> = {
  '/docs': 'nav.documentation',
  '/onboarding': 'nav.onboarding',
  '/': 'nav.dashboard',
  '/runtime/monitor': 'nav.transactionMonitor',
  '/runtime/queue': 'nav.integrationQueue',
  '/runtime/dlq': 'nav.deadLetterQueue',
  '/audit': 'nav.auditLog',
  '/events': 'nav.events',
  '/incidents': 'nav.incidents',
  '/health': 'nav.health',
  '/onec-cockpit': 'nav.onecCockpit',
  '/integration-flows': 'nav.integrationFlows',
  '/test-console': 'nav.testConsole',
  '/test-cases': 'nav.savedTestCases',
  '/odata-explorer': 'nav.odataExplorer',
  '/xml-tools': 'nav.xmlTools',
  '/mappings': 'nav.mappings',
  '/business-objects': 'nav.businessObjects',
  '/resolvers': 'nav.resolvers',
  '/resolvers/cache': 'nav.resolvers',
  '/runtime/resolvers': 'nav.resolvers',
  '/transforms': 'nav.transforms',
  '/business-rules': 'nav.businessRules',
  '/runtime/transforms': 'nav.transforms',
  '/runtime/business-rules': 'nav.businessRules',
  '/packages': 'nav.packages',
  '/plugin-store': 'nav.pluginStore',
  '/packages/omh-package-onec': 'nav.onecPackage',
  '/packages/omh-package-printer': 'nav.printerPackage',
  '/connectors': 'nav.connectors',
  '/secrets': 'nav.secrets',
  '/integration-bus': 'nav.integrationBus',
  '/workflows': 'nav.workflows',
  '/execution/steps': 'nav.executionSteps',
  '/maintenance': 'nav.maintenance',
  '/environments': 'nav.environments',
  '/change-sets': 'nav.changeSets',
  '/production': 'nav.production',
  '/retention': 'nav.retention',
  '/notifications': 'nav.notifications',
  '/users': 'nav.users',
  '/auth-settings': 'nav.authSettings',
};

const groupOrder = ['Operate', 'Build', 'Data Tools', 'Packages', 'Settings', 'Advanced', 'Developer'];
const modeRank: Record<UIMode, number> = { simple: 0, advanced: 1, developer: 2 };
const simpleRoutes = new Set(['/docs', '/onboarding', '/', '/runtime/monitor', '/events', '/onec-cockpit', '/integration-flows', '/test-console', '/packages', '/plugin-store']);
const developerRoutes = new Set(['/workflows', '/execution/steps']);

export function Layout() {
  const t = useT();
  const navigation = useQuery({ queryKey: ['ui-navigation'], queryFn: uiApi.navigation, retry: false });
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set(['Operate', 'Build', 'Data Tools', 'Packages']));
  const [uiMode, setUiMode] = useState<UIMode>(() => {
    const saved = localStorage.getItem(uiModeStorageKey);
    return saved === 'simple' || saved === 'advanced' || saved === 'developer' ? saved : 'advanced';
  });
  const items = navigation.data?.length ? navigation.data : fallbackNavigation;
  const sections = useMemo(() => {
    const grouped = new Map<string, UINavigationItem[]>();
    items.filter((item) => item.enabled && modeAllows(item, uiMode)).forEach((item) => {
      const group = developerRoutes.has(item.route) ? 'Developer' : item.group;
      grouped.set(group, [...(grouped.get(group) ?? []), item]);
    });
    return Array.from(grouped.entries()).sort(([left], [right]) => (groupOrder.indexOf(left) === -1 ? 99 : groupOrder.indexOf(left)) - (groupOrder.indexOf(right) === -1 ? 99 : groupOrder.indexOf(right)));
  }, [items, uiMode]);

  function toggle(group: string) {
    const next = new Set(expanded);
    if (next.has(group)) next.delete(group);
    else next.add(group);
    setExpanded(next);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-sigil">OMH</div>
          <div>
            <div className="brand-title">Open Manufacturing Hub</div>
            <div className="brand-subtitle">{t('app.brandSubtitle')}</div>
          </div>
        </div>
        <nav className="main-nav compact-main-nav" aria-label={t('nav.primary')}>
          <div className="ui-mode-switch" aria-label="UI mode">
            <span>{t('nav.uiMode')}</span>
            <div>
              {uiModes.map((mode) => (
                <button
                  key={mode}
                  type="button"
                  className={uiMode === mode ? 'active' : ''}
                  onClick={() => {
                    localStorage.setItem(uiModeStorageKey, mode);
                    setUiMode(mode);
                  }}
                >
                  {t(`nav.mode.${mode}`)}
                </button>
              ))}
            </div>
          </div>
          {sections.map(([group, groupItems]) => {
            const isExpanded = expanded.has(group);
            const titleKey = groupKey[group];
            return (
              <section className="nav-section collapsible-nav-section" key={group}>
                <button type="button" className="nav-section-toggle" onClick={() => toggle(group)} aria-expanded={isExpanded}>
                  <span>{titleKey ? t(titleKey) : group}</span>
                  <strong>{groupItems.length}</strong>
                </button>
                {isExpanded && groupItems.map((item) => {
                  const labelKey = routeKey[item.route];
                  return (
                    <NavLink key={`${item.group}:${item.route}`} to={item.route} end={item.route === '/'} className={({ isActive }) => `nav-link ${item.advanced ? 'advanced' : ''} ${isActive ? 'active' : ''}`}>
                      <span className="nav-dot" />
                      {labelKey ? t(labelKey) : item.title}
                    </NavLink>
                  );
                })}
              </section>
            );
          })}
          {navigation.error && <span className="microcopy nav-warning">Navigation BFF unavailable, using local fallback.</span>}
        </nav>
        <div className="sidebar-footer">
          <span className="microcopy">{t('app.apiEndpoint')}</span>
          <strong className="api-endpoint">{API_BASE_URL}</strong>
        </div>
      </aside>
      <main className="content-shell">
        <TopBar />
        <ProductionBanner />
        <div className="page-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

function modeAllows(item: UINavigationItem, mode: UIMode) {
  if (simpleRoutes.has(item.route)) return true;
  const minimumMode: UIMode = developerRoutes.has(item.route) ? 'developer' : item.advanced ? 'advanced' : 'simple';
  return modeRank[mode] >= modeRank[minimumMode];
}

function TopBar() {
  const { language, setLanguage, t } = useI18n();
  const location = useLocation();
  const topic = helpForPath(location.pathname);
  return (
    <header className="topbar slim-topbar">
      <div className="topbar-product">
        <span className="topbar-kicker">OMH</span>
        <strong>{t('topbar.product')}</strong>
      </div>
      <div className="language-switcher" aria-label={t('topbar.language')}>
        <span className="microcopy">{t('topbar.language')}</span>
        {languages.map((item) => (
          <button key={item} type="button" className={`flag-button ${language === item ? 'active' : ''}`} onClick={() => setLanguage(item)} aria-label={t(`topbar.flags.${item}`)} title={languageMeta[item].nativeName}>
            <Flag language={item} />
            <span>{languageMeta[item].shortName}</span>
          </button>
        ))}
      </div>
      <ContextHelpButton topic={topic} />
      <UserMenu />
    </header>
  );
}

function Flag({ language }: { language: Language }) {
  if (language === 'ru') return <RussianFlag />;
  if (language === 'zh') return <ChineseFlag />;
  return <EnglishFlag />;
}

function RussianFlag() {
  return <svg className="flag-icon" viewBox="0 0 36 24" role="img" aria-hidden="true"><rect width="36" height="24" rx="3" fill="#fff" /><path d="M0 8h36v8H0z" fill="#1c57a7" /><path d="M0 16h36v5a3 3 0 0 1-3 3H3a3 3 0 0 1-3-3z" fill="#d52b1e" /><rect width="36" height="24" rx="3" fill="none" stroke="rgba(0,0,0,.18)" /></svg>;
}

function EnglishFlag() {
  return <svg className="flag-icon" viewBox="0 0 36 24" role="img" aria-hidden="true"><clipPath id="flag-uk-clip"><rect width="36" height="24" rx="3" /></clipPath><g clipPath="url(#flag-uk-clip)"><path fill="#012169" d="M0 0h36v24H0z" /><path stroke="#fff" strokeWidth="5" d="m0 0 36 24M36 0 0 24" /><path stroke="#c8102e" strokeWidth="3" d="m0 0 36 24M36 0 0 24" /><path stroke="#fff" strokeWidth="8" d="M18 0v24M0 12h36" /><path stroke="#c8102e" strokeWidth="5" d="M18 0v24M0 12h36" /></g><rect width="36" height="24" rx="3" fill="none" stroke="rgba(0,0,0,.18)" /></svg>;
}

function ChineseFlag() {
  return <svg className="flag-icon" viewBox="0 0 36 24" role="img" aria-hidden="true"><rect width="36" height="24" rx="3" fill="#de2910" /><path fill="#ffde00" d="m7 4 1.06 3.18h3.35L8.7 9.15l1.03 3.22L7 10.38l-2.73 1.99L5.3 9.15 2.59 7.18h3.35z" /><path fill="#ffde00" d="m15.7 3.8.34 1.03h1.08l-.87.64.33 1.04-.88-.64-.88.64.34-1.04-.88-.64h1.08zm4 3 .34 1.03h1.08l-.87.64.33 1.04-.88-.64-.88.64.34-1.04-.88-.64h1.08zm-.2 5 .34 1.03h1.08l-.87.64.33 1.04-.88-.64-.88.64.34-1.04-.88-.64h1.08zm-4-1.1.34 1.03h1.08l-.87.64.33 1.04-.88-.64-.88.64.34-1.04-.88-.64h1.08z" /><rect width="36" height="24" rx="3" fill="none" stroke="rgba(0,0,0,.18)" /></svg>;
}
