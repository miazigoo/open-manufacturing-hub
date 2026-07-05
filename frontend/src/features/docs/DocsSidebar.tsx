import { NavLink } from 'react-router-dom';
import { useT } from '../../i18n/useI18n';
import { packageOverviewPath, pagePath } from './content';
import type { DocsLanguageBundle } from './types';

export function DocsSidebar({ bundle }: { bundle: DocsLanguageBundle }) {
  const t = useT();
  return (
    <aside className="docs-sidebar-panel" aria-label={t('docs.tree')}>
      <div className="docs-sidebar-head">
        <span className="eyebrow">{t('docs.documentation')}</span>
        <strong>{t('docs.packagesCount', { count: bundle.packages.length })}</strong>
      </div>
      <nav className="docs-tree">
        {bundle.packages.map((pkg) => (
          <section key={pkg.id} className={`docs-tree-package accent-${pkg.accent}`}>
            <NavLink to={packageOverviewPath(pkg)} className="docs-package-link">
              <span>{pkg.title}</span>
              <small>{pkg.description}</small>
            </NavLink>
            {pkg.sections.map((section) => (
              <div key={section.id} className="docs-tree-section">
                <div className="docs-tree-section-title">{section.title}</div>
                {section.pages.map((page) => (
                  <NavLink key={page.id} to={pagePath(page)} className={({ isActive }) => `docs-page-link ${isActive ? 'active' : ''}`}>
                    {page.title}
                  </NavLink>
                ))}
              </div>
            ))}
          </section>
        ))}
      </nav>
    </aside>
  );
}
