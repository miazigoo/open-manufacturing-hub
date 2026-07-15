import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

export function RouteScrollManager() {
  const { pathname, hash } = useLocation();

  useEffect(() => {
    let frame = 0;
    let attempts = 0;

    const run = () => {
      if (hash) {
        const id = decodeURIComponent(hash.slice(1));
        const target = document.getElementById(id);
        if (target) {
          target.scrollIntoView({ block: 'start', behavior: 'auto' });
          return;
        }
        if (attempts < 5) {
          attempts += 1;
          frame = window.requestAnimationFrame(run);
          return;
        }
      }
      window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
    };

    frame = window.requestAnimationFrame(run);

    return () => window.cancelAnimationFrame(frame);
  }, [pathname, hash]);

  return null;
}
