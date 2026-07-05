import { CodeBlock } from '../../components/CodeBlock';
import { useT } from '../../i18n/useI18n';

export function CodeBlockWithCopy({ language, code }: { language: string; code: string }) {
  const t = useT();
  return <CodeBlock code={code} language={language} copyLabel={t('common.buttons.copy')} copiedLabel={t('common.copied')} failedLabel={t('docs.copyUnavailable')} />;
}
