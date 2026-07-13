import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

export function RouteScrollManager() {
  const { pathname, search, hash } = useLocation();

  useEffect(() => {
    const scroll = window.setTimeout(() => {
      if (hash) {
        const id = decodeURIComponent(hash.slice(1));
        const target = document.getElementById(id);
        if (target) {
          target.scrollIntoView({ block: 'start', behavior: 'auto' });
          return;
        }
      }
      window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
    }, 0);

    return () => window.clearTimeout(scroll);
  }, [pathname, search, hash]);

  return null;
}
