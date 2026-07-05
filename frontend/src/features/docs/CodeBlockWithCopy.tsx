import { CopyButton } from '../../components/product/CopyButton';
import { useT } from '../../i18n/useI18n';

export function CodeBlockWithCopy({ language, code }: { language: string; code: string }) {
  const t = useT();
  return (
    <div className="docs-code-block">
      <div className="docs-code-toolbar"><span>{language || 'text'}</span><CopyButton value={code} label={t('common.buttons.copy')} copiedLabel={t('common.copied')} failedLabel={t('docs.copyUnavailable')} /></div>
      <pre><code className={`language-${language || 'text'}`}>{code}</code></pre>
    </div>
  );
}
