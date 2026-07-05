import { FormEvent, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../../api/client';
import { ConfigObjectType, ConfigVersion, configVersionQueryKey, configVersionsApi } from '../../api/configVersions';
import { CodeEditor } from '../../components/CodeEditor';
import { JsonBlock } from '../../components/JsonBlock';

function parsePayload(value: string): Record<string, unknown> {
  const parsed = JSON.parse(value || '{}') as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('Test payload must be a JSON object');
  return parsed as Record<string, unknown>;
}

export function DraftTestPanel({ objectType, objectId, draft }: { objectType: ConfigObjectType | string; objectId: string; draft: ConfigVersion | null | undefined }) {
  const queryClient = useQueryClient();
  const [payload, setPayload] = useState(asJson({ payload: { sample: true }, input: { id: 'demo' }, variables: {} }));
  const [formError, setFormError] = useState<string | null>(null);
  const test = useMutation({
    mutationFn: () => configVersionsApi.test(objectType, objectId, draft!.id, parsePayload(payload)),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: configVersionQueryKey(objectType, objectId) }),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    try { test.mutate(); } catch (error) { setFormError(error instanceof Error ? error.message : 'Invalid JSON'); }
  }

  if (!draft) return <div className="empty-panel compact">Create a draft before running release tests.</div>;
  return (
    <form className="config-test-panel" onSubmit={submit}>
      <div className="panel-toolbar"><div><span className="eyebrow">Draft test</span><h3>Run isolated validation</h3></div><button className="primary-button" disabled={test.isPending}>Run test</button></div>
      <label className="field-label">Test envelope<CodeEditor value={payload} onChange={setPayload} language="json" minRows={7} /></label>
      {formError && <div className="error-state compact">{formError}</div>}
      {test.error instanceof Error && <div className="error-state compact">{test.error.message}</div>}
      {test.data && <JsonBlock title="Draft test result" value={test.data} searchable={false} />}
    </form>
  );
}
