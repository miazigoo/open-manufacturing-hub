import { NavLink } from 'react-router-dom';
import { packageOverviewPath, pagePath } from './content';
import type { DocsLanguageBundle } from './types';

export function DocsSidebar({ bundle }: { bundle: DocsLanguageBundle }) {
  return (
    <aside className="docs-sidebar-panel" aria-label="Documentation tree">
      <div className="docs-sidebar-head">
        <span className="eyebrow">Documentation</span>
        <strong>{bundle.packages.length} packages</strong>
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
