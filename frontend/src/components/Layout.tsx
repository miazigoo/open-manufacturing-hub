import { NavLink, Outlet } from 'react-router-dom';
import { API_BASE_URL } from '../api/client';
import { useI18n, useT } from '../i18n/useI18n';
import { languageMeta } from '../i18n/dictionary';
import type { Language } from '../i18n/dictionary';

interface NavItem { to: string; labelKey: string }
interface NavSection { titleKey: string; items: NavItem[] }

const navSections: NavSection[] = [
  {
    titleKey: 'nav.sectionOperate',
    items: [
      { to: '/', labelKey: 'nav.dashboard' },
      { to: '/events', labelKey: 'nav.events' },
      { to: '/incidents', labelKey: 'nav.incidents' },
      { to: '/health', labelKey: 'nav.health' },
    ],
  },
  {
    titleKey: 'nav.sectionBuild',
    items: [
      { to: '/connectors', labelKey: 'nav.connectors' },
      { to: '/integration-bus', labelKey: 'nav.integrationBus' },
      { to: '/workflows', labelKey: 'nav.workflows' },
      { to: '/mappings', labelKey: 'nav.mappings' },
      { to: '/execution/steps', labelKey: 'nav.executionSteps' },
    ],
  },
  {
    titleKey: 'nav.sectionOneCTools',
    items: [
      { to: '/integration-designer', labelKey: 'nav.integrationDesigner' },
      { to: '/scenario-library', labelKey: 'nav.scenarioLibrary' },
      { to: '/odata-explorer', labelKey: 'nav.odataExplorer' },
      { to: '/xml-tools', labelKey: 'nav.xmlTools' },
      { to: '/test-console', labelKey: 'nav.testConsole' },
      { to: '/test-cases', labelKey: 'nav.savedTestCases' },
      { to: '/onec-quick-setup', labelKey: 'nav.onecQuickSetup' },
      { to: '/onec-scenarios', labelKey: 'nav.onecScenarios' },
      { to: '/onec-workbench', labelKey: 'nav.onecWorkbench' },
    ],
  },
  {
    titleKey: 'nav.sectionProduction',
    items: [
      { to: '/polling', labelKey: 'nav.polling' },
      { to: '/printing', labelKey: 'nav.printing' },
      { to: '/notifications', labelKey: 'nav.notifications' },
      { to: '/maintenance', labelKey: 'nav.maintenance' },
      { to: '/retention', labelKey: 'nav.retention' },
    ],
  },
];

const languages: Language[] = ['ru', 'en', 'zh'];

export function Layout() {
  const t = useT();
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
        <nav className="main-nav" aria-label={t('nav.primary')}>
          {navSections.map((section) => (
            <section className="nav-section" key={section.titleKey}>
              <span className="nav-section-title">{t(section.titleKey)}</span>
              {section.items.map((item) => (
                <NavLink key={item.to} to={item.to} end={item.to === '/'} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                  <span className="nav-dot" />
                  {t(item.labelKey)}
                </NavLink>
              ))}
            </section>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="microcopy">{t('app.apiEndpoint')}</span>
          <strong className="api-endpoint">{API_BASE_URL}</strong>
        </div>
      </aside>
      <main className="content-shell">
        <TopBar />
        <div className="page-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

function TopBar() {
  const { language, setLanguage, t } = useI18n();
  return (
    <header className="topbar">
      <div className="topbar-product">
        <span className="topbar-kicker">OMH</span>
        <strong>{t('topbar.product')}</strong>
      </div>
      <div className="language-switcher" aria-label={t('topbar.language')}>
        <span className="microcopy">{t('topbar.language')}</span>
        {languages.map((item) => (
          <button
            key={item}
            type="button"
            className={`flag-button ${language === item ? 'active' : ''}`}
            onClick={() => setLanguage(item)}
            aria-label={t(`topbar.flags.${item}`)}
            title={languageMeta[item].nativeName}
          >
            <Flag language={item} />
            <span>{languageMeta[item].shortName}</span>
          </button>
        ))}
      </div>
    </header>
  );
}

function Flag({ language }: { language: Language }) {
  if (language === 'ru') return <RussianFlag />;
  if (language === 'zh') return <ChineseFlag />;
  return <EnglishFlag />;
}

function RussianFlag() {
  return (
    <svg className="flag-icon" viewBox="0 0 36 24" role="img" aria-hidden="true">
      <rect width="36" height="24" rx="3" fill="#fff" />
      <path d="M0 8h36v8H0z" fill="#1c57a7" />
      <path d="M0 16h36v5a3 3 0 0 1-3 3H3a3 3 0 0 1-3-3z" fill="#d52b1e" />
      <rect width="36" height="24" rx="3" fill="none" stroke="rgba(0,0,0,.18)" />
    </svg>
  );
}

function EnglishFlag() {
  return (
    <svg className="flag-icon" viewBox="0 0 36 24" role="img" aria-hidden="true">
      <clipPath id="flag-uk-clip"><rect width="36" height="24" rx="3" /></clipPath>
      <g clipPath="url(#flag-uk-clip)">
        <path fill="#012169" d="M0 0h36v24H0z" />
        <path stroke="#fff" strokeWidth="5" d="m0 0 36 24M36 0 0 24" />
        <path stroke="#c8102e" strokeWidth="3" d="m0 0 36 24M36 0 0 24" />
        <path stroke="#fff" strokeWidth="8" d="M18 0v24M0 12h36" />
        <path stroke="#c8102e" strokeWidth="5" d="M18 0v24M0 12h36" />
      </g>
      <rect width="36" height="24" rx="3" fill="none" stroke="rgba(0,0,0,.18)" />
    </svg>
  );
}

function ChineseFlag() {
  return (
    <svg className="flag-icon" viewBox="0 0 36 24" role="img" aria-hidden="true">
      <rect width="36" height="24" rx="3" fill="#de2910" />
      <path fill="#ffde00" d="m7 4 1.06 3.18h3.35L8.7 9.15l1.03 3.22L7 10.38l-2.73 1.99L5.3 9.15 2.59 7.18h3.35z" />
      <path fill="#ffde00" d="m15.7 3.8.34 1.03h1.08l-.87.64.33 1.04-.88-.64-.88.64.34-1.04-.88-.64h1.08zm4 3 .34 1.03h1.08l-.87.64.33 1.04-.88-.64-.88.64.34-1.04-.88-.64h1.08zm-.2 5 .34 1.03h1.08l-.87.64.33 1.04-.88-.64-.88.64.34-1.04-.88-.64h1.08zm-4-1.1.34 1.03h1.08l-.87.64.33 1.04-.88-.64-.88.64.34-1.04-.88-.64h1.08z" />
      <rect width="36" height="24" rx="3" fill="none" stroke="rgba(0,0,0,.18)" />
    </svg>
  );
}
