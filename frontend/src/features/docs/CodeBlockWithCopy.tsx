import { CopyButton } from '../../components/product/CopyButton';
import { useI18n } from '../../i18n/useI18n';

const labels = {
  ru: { copy: 'Копировать', copied: 'Скопировано', failed: 'Недоступно' },
  en: { copy: 'Copy', copied: 'Copied', failed: 'Copy unavailable' },
  zh: { copy: '复制', copied: '已复制', failed: '无法复制' },
};

export function CodeBlockWithCopy({ language, code }: { language: string; code: string }) {
  const { language: currentLanguage } = useI18n();
  const copy = labels[currentLanguage];
  return (
    <div className="docs-code-block">
      <div className="docs-code-toolbar"><span>{language || 'text'}</span><CopyButton value={code} label={copy.copy} copiedLabel={copy.copied} failedLabel={copy.failed} /></div>
      <pre><code className={`language-${language || 'text'}`}>{code}</code></pre>
    </div>
  );
}
