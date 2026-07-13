import type { FlowBuilderPreviewResponse } from '../../api/integrationFlows';
import { JsonBlock } from '../JsonBlock';
import { SectionCard } from '../product/SectionCard';
import { StepPreviewTimeline } from './StepPreviewTimeline';
import { useT } from '../../i18n/useI18n';

interface FlowPreviewPanelProps {
  preview?: FlowBuilderPreviewResponse | null;
  builder: Record<string, unknown>;
}

export function FlowPreviewPanel({ preview, builder }: FlowPreviewPanelProps) {
  const t = useT();
  return (
    <SectionCard eyebrow={t('integration.sharedBuilder.previewEyebrow')} title={t('integration.sharedBuilder.flowDryRun')} description={t('integration.sharedBuilder.flowDryRunDesc')}>
      <StepPreviewTimeline preview={preview} />
      {preview && <JsonBlock title={t('integration.sharedBuilder.finalPayload')} value={preview.final_payload_preview ?? {}} searchable={false} />}
      {preview && <JsonBlock title={t('integration.sharedBuilder.targetRequest')} value={preview.target_request_preview ?? {}} searchable={false} />}
      <details className="advanced-json-details">
        <summary>{t('integration.sharedBuilder.advancedBuilderJson')}</summary>
        <JsonBlock title={t('integration.sharedBuilder.builderJson')} value={builder} searchable />
      </details>
    </SectionCard>
  );
}
