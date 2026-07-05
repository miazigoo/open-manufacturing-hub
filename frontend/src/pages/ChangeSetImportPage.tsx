import { ChangeEvent, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { changeSetsApi, ChangeSetMapping } from '../api/changeSets';
import { JsonBlock } from '../components/JsonBlock';
import { StatusBadge } from '../components/StatusBadge';

function parseJsonObject(value: string, label: string): Record<string, unknown> {
  const parsed = JSON.parse(value || '{}') as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error(`${label} must be a JSON object`);
  return parsed as Record<string, unknown>;
}

export function ChangeSetImportPage() {
  const [payloadText, setPayloadText] = useState('{\n  "omh_change_set_version": 1,\n  "name": "Paste exported change set",\n  "items": []\n}');
  const [secretMappingText, setSecretMappingText] = useState('{}');
  const [connectorMappingText, setConnectorMappingText] = useState('{}');
  const [environmentVariablesText, setEnvironmentVariablesText] = useState('{}');
  const [allowConflicts, setAllowConflicts] = useState(false);
  const [runSmokeTests, setRunSmokeTests] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const parsedPayload = useMemo(() => {
    try { return parseJsonObject(payloadText, 'Change set'); } catch { return null; }
  }, [payloadText]);
  const preview = useMutation({ mutationFn: () => changeSetsApi.previewImport(parseJsonObject(payloadText, 'Change set'), mapping()) });
  const apply = useMutation({ mutationFn: () => changeSetsApi.applyImport(parseJsonObject(payloadText, 'Change set'), mapping()) });

  async function loadFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setPayloadText(await file.text());
  }

  function mapping(): ChangeSetMapping {
    return {
      connector_mapping: parseJsonObject(connectorMappingText, 'Connector mapping') as Record<string, string>,
      secret_mapping: parseJsonObject(secretMappingText, 'Secret mapping') as Record<string, string>,
      environment_variables: parseJsonObject(environmentVariablesText, 'Environment variables'),
      allow_conflicts: allowConflicts,
      run_smoke_tests: runSmokeTests,
    };
  }

  function runPreview() {
    setError(null);
    try { preview.mutate(); } catch (err) { setError(err instanceof Error ? err.message : 'Invalid import payload'); }
  }

  function runApply() {
    setError(null);
    try { apply.mutate(); } catch (err) { setError(err instanceof Error ? err.message : 'Invalid import payload'); }
  }

  const result = apply.data ?? preview.data;
  const mutationError = (preview.error ?? apply.error) instanceof Error ? ((preview.error ?? apply.error) as Error).message : null;

  return (
    <div className="page-stack promotion-page">
      <section className="page-header promotion-hero import-hero">
        <div>
          <span className="eyebrow">Import Pipeline</span>
          <h1>Preview before production apply.</h1>
          <p>Detect missing packages, secret refs, environment variables and identity conflicts before any runtime object is changed.</p>
        </div>
        <div className="hero-meta"><Link className="ghost-button" to="/change-sets">Back to change sets</Link><Link className="ghost-button" to="/environments">Set current environment</Link></div>
      </section>

      <section className="promotion-grid wide-left">
        <section className="panel stack-form">
          <div className="panel-toolbar"><div><span className="eyebrow">Change Set JSON</span><h2>Reference-only package</h2></div><StatusBadge status={parsedPayload ? 'ok' : 'failed'} label={parsedPayload ? 'valid json' : 'invalid'} /></div>
          <input type="file" accept="application/json" onChange={loadFile} />
          <label className="field-label">Payload<textarea className="large-json-input" value={payloadText} onChange={(event) => setPayloadText(event.target.value)} /></label>
        </section>

        <section className="panel stack-form">
          <div className="panel-toolbar"><div><span className="eyebrow">Target Mapping</span><h2>Secrets, connectors, variables</h2></div></div>
          <label className="field-label">Secret mapping<textarea value={secretMappingText} onChange={(event) => setSecretMappingText(event.target.value)} /></label>
          <label className="field-label">Connector mapping<textarea value={connectorMappingText} onChange={(event) => setConnectorMappingText(event.target.value)} /></label>
          <label className="field-label">Environment variables<textarea value={environmentVariablesText} onChange={(event) => setEnvironmentVariablesText(event.target.value)} /></label>
          <label className="inline-check"><input type="checkbox" checked={allowConflicts} onChange={(event) => setAllowConflicts(event.target.checked)} /> Allow identity conflicts</label>
          <label className="inline-check"><input type="checkbox" checked={runSmokeTests} onChange={(event) => setRunSmokeTests(event.target.checked)} /> Run smoke tests after apply</label>
          <div className="action-row wrap-actions"><button className="ghost-button" onClick={runPreview} disabled={preview.isPending}>Preview import</button><button className="primary-button" onClick={runApply} disabled={apply.isPending || !result?.valid}>Apply to current environment</button></div>
          {(error || mutationError) && <div className="error-state compact">{error || mutationError}</div>}
          {result && <StatusBadge status={result.valid ? 'ok' : 'failed'} label={result.valid ? (result.applied ? 'applied' : 'preview valid') : 'blocked'} />}
        </section>
      </section>

      {result && <JsonBlock title="Import result" value={result} />}
      <JsonBlock title="Mapping JSON" value={{ secret_mapping: safeJson(secretMappingText), connector_mapping: safeJson(connectorMappingText), environment_variables: safeJson(environmentVariablesText) }} searchable={false} />
    </div>
  );
}

function safeJson(value: string) {
  try { return JSON.parse(value); } catch { return value; }
}
