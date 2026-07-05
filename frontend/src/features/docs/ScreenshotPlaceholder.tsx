import { useT } from '../../i18n/useI18n';

export function ScreenshotPlaceholder({ label, assetId, sourceRoute }: { label: string; assetId?: string; sourceRoute?: string }) {
  const t = useT();
  return (
    <figure className="docs-screenshot-placeholder">
      <div className="docs-screenshot-frame">
        <span>{assetId ? t('docs.screenshotMissing') : t('docs.screenshot')}</span>
        <strong>{label}</strong>
        <small>{assetId ? t('docs.screenshotMissingDetail', { assetId }) : t('docs.screenshotPlaceholderDetail')}</small>
      </div>
      <figcaption>{label}{sourceRoute ? ` · ${t('docs.sourceRoute', { route: sourceRoute })}` : ''}</figcaption>
    </figure>
  );
}
