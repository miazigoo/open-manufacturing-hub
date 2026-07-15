import { useMemo, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { API_BASE_URL } from '../api/client';
import { uiApi } from '../api/ui';
import { ProductionBanner } from './ProductionBanner';
import { CommandPalette } from './command-palette/CommandPalette';
import { UserMenu } from '../features/auth/UserMenu';
import { ContextHelpButton } from '../features/help/ContextHelpButton';
import { helpForPath } from '../features/help/helpRegistry';
import { useI18n, useT } from '../i18n/useI18n';
import { languageMeta } from '../i18n/dictionary';
import type { Language } from '../i18n/dictionary';
import { fallbackNavigation, groupKey, groupOrder, modeAllows, normalizeNavigation, routeKey, type UIMode, uiModes, uiModeStorageKey } from '../navigation/navModel';

const languages: Language[] = ['ru', 'en', 'zh'];

export function Layout() {
  const t = useT();
  const navigation = useQuery({ queryKey: ['ui-navigation'], queryFn: uiApi.navigation, retry: false });
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set(['Operate', 'Build']));
  const [scenarioChooserOpen, setScenarioChooserOpen] = useState(false);
  const [uiMode, setUiMode] = useState<UIMode>(() => {
    const saved = localStorage.getItem(uiModeStorageKey);
    return saved === 'simple' || saved === 'advanced' || saved === 'developer' ? saved : 'simple';
  });
  const items = normalizeNavigation(navigation.data?.length ? navigation.data : fallbackNavigation);
  const sections = useMemo(() => {
    const grouped = new Map<string, typeof items>();
    items.filter((item) => item.enabled && modeAllows(item, uiMode)).forEach((item) => {
      grouped.set(item.group, [...(grouped.get(item.group) ?? []), item]);
    });
    const groupIndex = (group: string) => {
      const index = groupOrder.indexOf(group as (typeof groupOrder)[number]);
      return index === -1 ? 99 : index;
    };
    return Array.from(grouped.entries()).sort(([left], [right]) => groupIndex(left) - groupIndex(right));
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
          <div className="ui-mode-switch" aria-label={t('nav.uiMode')}>
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
            <small>{t(`nav.modeHint.${uiMode}`)}</small>
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
                  const labelKey = item.titleKey || routeKey[item.route];
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
          {navigation.error && <span className="microcopy nav-warning">{t('navigation.bffUnavailable')}</span>}
        </nav>
        <div className="sidebar-footer">
          <span className="microcopy">{t('app.apiEndpoint')}</span>
          <strong className="api-endpoint">{API_BASE_URL}</strong>
        </div>
      </aside>
      <main className="content-shell">
        <TopBar onCreateIntegration={() => setScenarioChooserOpen(true)} />
        <ProductionBanner />
        <div className="page-content">
          <Outlet />
        </div>
      </main>
      {scenarioChooserOpen && <ScenarioChooser onClose={() => setScenarioChooserOpen(false)} />}
      <CommandPalette />
    </div>
  );
}

function TopBar({ onCreateIntegration }: { onCreateIntegration: () => void }) {
  const { language, setLanguage, t } = useI18n();
  const location = useLocation();
  const topic = helpForPath(location.pathname);
  return (
    <header className="topbar slim-topbar">
      <div className="topbar-product">
        <span className="topbar-kicker">OMH</span>
        <strong>{t('topbar.product')}</strong>
      </div>
      <button type="button" className="create-integration-button" onClick={onCreateIntegration}>{t('nav.createIntegration')}</button>
      <button type="button" className="command-palette-trigger" onClick={() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }))} aria-label={t('navigation.commandPalette.openHint')} title={t('navigation.commandPalette.openHint')}>
        <span>{t('navigation.commandPalette.triggerLabel')}</span>
        <kbd>{t('navigation.commandPalette.shortcut')}</kbd>
      </button>
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

const scenarioCards = [
  {
    titleKey: 'navigation.scenarioChooser.cards.router.title',
    inputKey: 'navigation.scenarioChooser.cards.router.input',
    outputKey: 'navigation.scenarioChooser.cards.router.output',
    doesKey: 'navigation.scenarioChooser.cards.router.does',
    bestKey: 'navigation.scenarioChooser.cards.router.best',
    to: '/integration-start',
    primary: true,
  },
  {
    titleKey: 'navigation.scenarioChooser.cards.odata.title',
    inputKey: 'navigation.scenarioChooser.cards.odata.input',
    outputKey: 'navigation.scenarioChooser.cards.odata.output',
    doesKey: 'navigation.scenarioChooser.cards.odata.does',
    bestKey: 'navigation.scenarioChooser.cards.odata.best',
    to: '/odata-explorer',
  },
  {
    titleKey: 'navigation.scenarioChooser.cards.flows.title',
    inputKey: 'navigation.scenarioChooser.cards.flows.input',
    outputKey: 'navigation.scenarioChooser.cards.flows.output',
    doesKey: 'navigation.scenarioChooser.cards.flows.does',
    bestKey: 'navigation.scenarioChooser.cards.flows.best',
    to: '/integration-flows',
  },
  {
    titleKey: 'navigation.scenarioChooser.cards.events.title',
    inputKey: 'navigation.scenarioChooser.cards.events.input',
    outputKey: 'navigation.scenarioChooser.cards.events.output',
    doesKey: 'navigation.scenarioChooser.cards.events.does',
    bestKey: 'navigation.scenarioChooser.cards.events.best',
    to: '/events',
  },
];

function ScenarioChooser({ onClose }: { onClose: () => void }) {
  const t = useT();
  return (
    <div className="scenario-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="scenario-modal" role="dialog" aria-modal="true" aria-labelledby="scenario-modal-title" onMouseDown={(event) => event.stopPropagation()}>
        <div className="panel-toolbar">
          <div>
            <span className="eyebrow">{t('navigation.scenarioChooser.eyebrow')}</span>
            <h2 id="scenario-modal-title">{t('navigation.scenarioChooser.title')}</h2>
            <p>{t('navigation.scenarioChooser.description')}</p>
          </div>
          <button type="button" className="ghost-button" onClick={onClose}>{t('common.buttons.close')}</button>
        </div>
        <div className="scenario-card-grid compact-scenario-grid">
          {scenarioCards.map((card) => (
            <Link key={card.titleKey} className={`scenario-card ${card.primary ? 'primary' : ''}`} to={card.to} onClick={onClose}>
              <span className="eyebrow">{card.primary ? t('navigation.scenarioChooser.recommendedStart') : t('navigation.scenarioChooser.scenario')}</span>
              <h3>{t(card.titleKey)}</h3>
              <dl>
                <div><dt>{t('navigation.scenarioChooser.whatComes')}</dt><dd>{t(card.inputKey)}</dd></div>
                <div><dt>{t('navigation.scenarioChooser.whatReturn')}</dt><dd>{t(card.outputKey)}</dd></div>
                <div><dt>{t('navigation.scenarioChooser.whatOmhDoes')}</dt><dd>{t(card.doesKey)}</dd></div>
                <div><dt>{t('navigation.scenarioChooser.bestFor')}</dt><dd>{t(card.bestKey)}</dd></div>
              </dl>
            </Link>
          ))}
        </div>
      </section>
    </div>
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
