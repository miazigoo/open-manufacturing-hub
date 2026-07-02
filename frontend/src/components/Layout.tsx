import { NavLink, Outlet } from 'react-router-dom';
import { API_BASE_URL } from '../api/client';

const navItems = [
  ['/', 'Dashboard'],
  ['/events', 'Event Journal'],
  ['/incidents', 'Incidents'],
  ['/health', 'Health'],
  ['/connectors', 'Connectors'],
  ['/execution/steps', 'Execution Steps'],
  ['/workflows', 'Workflows'],
  ['/mappings', 'Mapping Editor'],
  ['/notifications', 'Notifications'],
  ['/maintenance', 'Maintenance'],
  ['/retention', 'Retention'],
];

export function Layout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-sigil">OMH</div>
          <div>
            <div className="brand-title">Open Manufacturing Hub</div>
            <div className="brand-subtitle">Operations control plane</div>
          </div>
        </div>
        <nav className="main-nav">
          {navItems.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <span className="nav-dot" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="microcopy">API endpoint</span>
          <strong className="api-endpoint">{API_BASE_URL}</strong>
        </div>
      </aside>
      <main className="content-shell">
        <Outlet />
      </main>
    </div>
  );
}
