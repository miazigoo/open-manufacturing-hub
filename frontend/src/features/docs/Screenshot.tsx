import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useI18n } from '../../i18n/useI18n';
import { docsAssetImageUrl, getDocsAsset, getDocsAssetAnnotations } from './DocsAssetRegistry';
import { ScreenshotPlaceholder } from './ScreenshotPlaceholder';

export function Screenshot({ assetId, label }: { assetId: string; label?: string }) {
  const { language } = useI18n();
  const asset = getDocsAsset(assetId);
  const [annotated, setAnnotated] = useState(true);
  const [missing, setMissing] = useState(false);

  if (!asset) return <ScreenshotPlaceholder label={label ?? `Missing screenshot asset: ${assetId}`} assetId={assetId} />;

  const annotations = getDocsAssetAnnotations(assetId);
  const imagePath = annotated && asset.annotated_path ? asset.annotated_path : asset.path;
  const caption = label ?? asset.description[language] ?? asset.description.ru;

  return (
    <figure className="docs-screenshot-block">
      <div className="docs-screenshot-toolbar">
        <span>{assetId}</span>
        <div className="action-row compact-actions">
          {asset.annotated_path && <button className="ghost-button" type="button" onClick={() => setAnnotated(!annotated)}>{annotated ? 'Original' : 'Annotated'}</button>}
          <a className="primary-link" href={docsAssetImageUrl(imagePath)} target="_blank" rel="noreferrer">Open full size</a>
        </div>
      </div>
      <div className="docs-screenshot-stage">
        {missing ? (
          <ScreenshotPlaceholder label={caption} assetId={assetId} sourceRoute={asset.source_route} />
        ) : (
          <img src={docsAssetImageUrl(imagePath)} alt={caption} onError={() => setMissing(true)} />
        )}
        {annotated && annotations.length > 0 && !missing && (
          <div className="docs-annotation-layer" aria-hidden="true">
            {annotations.map((annotation, index) => annotation.type === 'box' ? (
              <span
                key={index}
                className="docs-annotation-box"
                style={{ left: `${annotation.x ?? 0}%`, top: `${annotation.y ?? 0}%`, width: `${annotation.width ?? 10}%`, height: `${annotation.height ?? 10}%` }}
              >
                <strong>{annotation.label[language] ?? annotation.label.ru}</strong>
              </span>
            ) : null)}
          </div>
        )}
      </div>
      <figcaption>{caption} · <Link to={asset.source_route}>Open source page</Link></figcaption>
    </figure>
  );
}
