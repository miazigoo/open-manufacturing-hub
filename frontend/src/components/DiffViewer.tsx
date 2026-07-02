import { ArtifactDiff } from '../api/client';
import { useT } from '../i18n/useI18n';
import { EmptyState } from './EmptyState';

function lineValue(value: unknown) {
  return typeof value === 'string' ? `"${value}"` : JSON.stringify(value);
}

export function DiffViewer({ diff }: { diff: ArtifactDiff | null }) {
  const t = useT();
  if (!diff) return <EmptyState title={t('diff.noDiff')} detail={t('diff.noDiffDetail')} />;

  const lines = [
    ...Object.entries(diff.removed).map(([key, value]) => ({ tone: 'removed', text: `- ${key}: ${lineValue(value)}` })),
    ...Object.entries(diff.added).map(([key, value]) => ({ tone: 'added', text: `+ ${key}: ${lineValue(value)}` })),
    ...Object.entries(diff.changed).flatMap(([key, value]) => [
      { tone: 'removed', text: `- ${key}: ${lineValue(value.from)}` },
      { tone: 'added', text: `+ ${key}: ${lineValue(value.to)}` },
    ]),
  ];

  if (lines.length === 0) return <EmptyState title={t('diff.noChanges')} detail={t('diff.noChangesDetail')} />;

  return (
    <section className="diff-panel">
      <div className="panel-toolbar"><h3>{t('diff.title')}</h3></div>
      <pre className="diff-block">
        {lines.map((line, index) => <span key={`${line.text}-${index}`} className={line.tone}>{line.text}\n</span>)}
      </pre>
    </section>
  );
}
