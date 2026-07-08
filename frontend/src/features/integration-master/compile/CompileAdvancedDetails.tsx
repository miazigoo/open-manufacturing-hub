import { CodeBlock } from '../../../components/CodeBlock';

interface CompileAdvancedDetailsProps {
  advanced?: Record<string, unknown> | null;
}

export function CompileAdvancedDetails({ advanced }: CompileAdvancedDetailsProps) {
  if (!advanced || Object.keys(advanced).length === 0) return null;
  return (
    <details className="advanced-json-details compile-advanced-details">
      <summary><span>Advanced details</span><strong>builder_json</strong></summary>
      <CodeBlock code={JSON.stringify(advanced, null, 2)} language="json" copyLabel="Скопировать JSON" copiedLabel="Скопировано" />
    </details>
  );
}
