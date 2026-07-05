import { Link } from 'react-router-dom';
import { useT } from '../../i18n/useI18n';

export function ScreenshotPlaceholder({ label, assetId, sourceRoute }: { label: string; assetId?: string; sourceRoute?: string }) {
  const t = useT();
  return (
    <figure className="docs-screenshot-placeholder">
      <div className="docs-screenshot-frame">
        <span>{t('docs.screenshotPending')}</span>
        <strong>{label}</strong>
        <small>{sourceRoute ? t('docs.sourceRoute', { route: sourceRoute }) : t('docs.screenshotPlaceholderDetail')}</small>
        <div className="docs-screenshot-actions">
          {sourceRoute && <Link className="primary-link" to={sourceRoute}>{t('docs.openSourcePage')}</Link>}
          <span>{assetId ? t('docs.captureLaterAsset', { assetId }) : t('docs.captureLater')}</span>
        </div>
      </div>
      <figcaption>{label}{sourceRoute ? ` · ${t('docs.sourceRoute', { route: sourceRoute })}` : ''}</figcaption>
    </figure>
  );
}
