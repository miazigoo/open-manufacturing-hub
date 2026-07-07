import { JsonBlock } from '../../../components/JsonBlock';

interface ODataResultPreviewProps { title: string; value: unknown }

export function ODataResultPreview({ title, value }: ODataResultPreviewProps) {
  if (!value) return null;
  return <JsonBlock title={title} value={value} searchable />;
}
