import type { FlowBuilderPreviewResponse } from '../../api/integrationFlows';
import { JsonBlock } from '../JsonBlock';
import { SectionCard } from '../product/SectionCard';
import { StepPreviewTimeline } from './StepPreviewTimeline';

interface FlowPreviewPanelProps {
  preview?: FlowBuilderPreviewResponse | null;
  builder: Record<string, unknown>;
}

export function FlowPreviewPanel({ preview, builder }: FlowPreviewPanelProps) {
  return (
    <SectionCard eyebrow="Preview" title="Flow dry-run" description="Inspect the generated integration before saving it.">
      <StepPreviewTimeline preview={preview} />
      {preview && <JsonBlock title="Final payload" value={preview.final_payload_preview ?? {}} searchable={false} />}
      {preview && <JsonBlock title="Target request" value={preview.target_request_preview ?? {}} searchable={false} />}
      <details className="advanced-json-details">
        <summary>Advanced builder JSON</summary>
        <JsonBlock title="Builder JSON" value={builder} searchable />
      </details>
    </SectionCard>
  );
}
