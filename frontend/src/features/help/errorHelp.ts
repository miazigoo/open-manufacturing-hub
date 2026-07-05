import { docUrl } from '../docs/docLinks';

export interface ErrorHelpInfo { title: string; checks: string[]; docsUrl: string }

const explicit: Record<string, ErrorHelpInfo> = {
  ODATA_LOOKUP_NOT_FOUND: { title: 'OData lookup did not find a matching object.', checks: ['Check selected 1C connector.', 'Check resource name.', 'Check filter template.', 'Check the source value used by the lookup.'], docsUrl: docUrl('onec.troubleshooting') },
  CONNECTOR_REQUEST_FAILED: { title: 'External connector request failed.', checks: ['Open outgoing request artifact.', 'Check target URL and credentials.', 'Inspect original external response.'], docsUrl: docUrl('timeline.errors') },
  VALIDATION_FAILED: { title: 'Payload validation failed.', checks: ['Check required fields.', 'Compare raw payload with expected schema.', 'Use Test Console dry run before retry.'], docsUrl: docUrl('test-console') },
};

export function errorHelp(errorCode?: string | null): ErrorHelpInfo | null {
  if (!errorCode) return null;
  if (explicit[errorCode]) return explicit[errorCode];
  if (errorCode.includes('ODATA')) return explicit.ODATA_LOOKUP_NOT_FOUND;
  if (errorCode.includes('CONNECTOR') || errorCode.includes('HTTP')) return explicit.CONNECTOR_REQUEST_FAILED;
  return { title: 'Use timeline artifacts to diagnose this failure.', checks: ['Open failed step.', 'Inspect request and response artifacts.', 'Use Replay or Dry Run after fixing data.'], docsUrl: docUrl('timeline.errors') };
}
