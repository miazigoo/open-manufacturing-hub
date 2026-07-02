import { ArtifactDiff } from '../api/client';
import { EmptyState } from './EmptyState';

function lineValue(value: unknown) {
  return typeof value === 'string' ? `"${value}"` : JSON.stringify(value);
}

export function DiffViewer({ diff }: { diff: ArtifactDiff | null }) {
  if (!diff) return <EmptyState title="No diff selected" detail="Choose two artifacts to compare their top-level JSON fields." />;

  const lines = [
    ...Object.entries(diff.removed).map(([key, value]) => ({ tone: 'removed', text: `- ${key}: ${lineValue(value)}` })),
    ...Object.entries(diff.added).map(([key, value]) => ({ tone: 'added', text: `+ ${key}: ${lineValue(value)}` })),
    ...Object.entries(diff.changed).flatMap(([key, value]) => [
      { tone: 'removed', text: `- ${key}: ${lineValue(value.from)}` },
      { tone: 'added', text: `+ ${key}: ${lineValue(value.to)}` },
    ]),
  ];

  if (lines.length === 0) return <EmptyState title="No JSON changes" detail="Artifacts have identical top-level content." />;

  return (
    <section className="diff-panel">
      <div className="panel-toolbar"><h3>JSON Diff</h3></div>
      <pre className="diff-block">
        {lines.map((line, index) => <span key={`${line.text}-${index}`} className={line.tone}>{line.text}\n</span>)}
      </pre>
    </section>
  );
}
