import { Link } from 'react-router-dom';

export function OpenPageLink({ route, label }: { route: string; label: string }) {
  return <Link className="docs-open-page-link" to={route}>{label}</Link>;
}
