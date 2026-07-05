import { FormEvent, useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { connectorsApi } from '../api/connectors';
import { integrationDesignerApi } from '../api/integrationDesigner';
import { scenarioLibraryApi } from '../api/scenarioLibrary';
import type { ScenarioRead } from '../api/scenarioLibrary';
import { ErrorState } from '../components/ErrorState';
import { CodeBlock } from '../components/CodeBlock';
import { CodeEditor } from '../components/CodeEditor';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';

interface DesignerForm {
  scenario_code: string;
  source_system: string;
  target_system: string;
  endpoint_slug: string;
  input_mode: string;
  response_mode: string;
  target_connector_id: string;
  test_payload: string;
}

const initialForm: DesignerForm = {
  scenario_code: 'onec_xml_raw_bridge',
  source_system: '1C ERP',
  target_system: '1C ERP',
  endpoint_slug: 'designer-upd-xml',
  input_mode: 'xml',
  response_mode: 'sync_response',
  target_connector_id: '',
  test_payload: '<Документ><Номер>UPD-1001</Номер><ИНН>1234567890</ИНН></Документ>',
};

function payloadToText(payload: unknown, mode: string) {
  if (typeof payload === 'string') return payload;
  if (mode === 'json') return asJson(payload ?? {});
  return String(payload ?? '');
}

function deriveFormFromScenario(current: DesignerForm, scenario: ScenarioRead): DesignerForm {
  const inputMode = scenario.input_modes.includes('xml') ? 'xml' : scenario.input_modes[0] ?? current.input_mode;
  return {
    ...current,
    scenario_code: scenario.code,
    source_system: scenario.source,
    target_system: scenario.target,
    endpoint_slug: scenario.default_slug,
    input_mode: inputMode,
    test_payload: payloadToText(scenario.sample_payload, inputMode),
  };
}

function safeJson(value: string) {
  try {
    return JSON.parse(value) as unknown;
  } catch {
    return value;
  }
}

export function IntegrationDesignerPage() {
  const scenarios = useQuery({ queryKey: ['scenario-library'], queryFn: scenarioLibraryApi.list });
  const connectors = useQuery({ queryKey: ['connectors'], queryFn: connectorsApi.list });
  const [form, setForm] = useState<DesignerForm>(initialForm);
  const [formError, setFormError] = useState<string | null>(null);
  const build = useMutation({ mutationFn: integrationDesignerApi.build, onSuccess: () => setFormError(null) });
  const error = scenarios.error ?? connectors.error;
  const selectedScenario = useMemo(() => scenarios.data?.find((item) => item.code === form.scenario_code), [form.scenario_code, scenarios.data]);

  if (scenarios.isLoading || connectors.isLoading) return <LoadingState label="Loading designer" />;
  if (error) return <ErrorState error={error} />;

  function applyScenario(code: string) {
    const scenario = scenarios.data?.find((item) => item.code === code);
    setForm(scenario ? deriveFormFromScenario(form, scenario) : { ...form, scenario_code: code });
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    let testPayload: unknown = form.test_payload;
    if (form.input_mode === 'json') {
      try {
        testPayload = JSON.parse(form.test_payload || '{}') as unknown;
      } catch {
        setFormError('Sample payload JSON is invalid. Fix it or switch the input mode to XML/raw_text.');
        return;
      }
    }
    build.mutate({
      scenario_code: form.scenario_code,
      source: { source_system: form.source_system, endpoint_slug: form.endpoint_slug, input_mode: form.input_mode },
      target: { target_system: form.target_system, target_connector_id: form.target_connector_id || null },
      logic: { response_mode: form.response_mode },
      test_payload: testPayload,
    });
  }

  return (
    <div className="page-stack two-column-page">
      <section className="panel form-panel">
        <span className="eyebrow">1C Integration Designer</span>
        <h1>Build an integration path</h1>
        <form className="stack-form" onSubmit={submit}>
          <label className="field-label">
            Scenario
            <select value={form.scenario_code} onChange={(event) => applyScenario(event.target.value)}>
              {(scenarios.data ?? []).map((item) => <option key={item.code} value={item.code}>{item.title}</option>)}
            </select>
          </label>
          {selectedScenario && <div className="success-note">{selectedScenario.description}</div>}
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">Source<input value={form.source_system} onChange={(event) => setForm({ ...form, source_system: event.target.value })} /></label>
            <label className="field-label">Target<input value={form.target_system} onChange={(event) => setForm({ ...form, target_system: event.target.value })} /></label>
            <label className="field-label">Slug<input value={form.endpoint_slug} onChange={(event) => setForm({ ...form, endpoint_slug: event.target.value })} /></label>
          </div>
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">
              Input
              <select value={form.input_mode} onChange={(event) => setForm({ ...form, input_mode: event.target.value, test_payload: selectedScenario ? payloadToText(selectedScenario.sample_payload, event.target.value) : form.test_payload })}>
                <option value="json">json</option>
                <option value="xml">xml</option>
                <option value="raw_text">raw_text</option>
              </select>
            </label>
            <label className="field-label">
              Response
              <select value={form.response_mode} onChange={(event) => setForm({ ...form, response_mode: event.target.value })}>
                <option value="sync_response">sync_response</option>
                <option value="accepted_event">accepted_event</option>
                <option value="accepted_message">accepted_message</option>
                <option value="proxy_response">proxy_response</option>
              </select>
            </label>
            <label className="field-label">
              Connector
              <select value={form.target_connector_id} onChange={(event) => setForm({ ...form, target_connector_id: event.target.value })}>
                <option value="">By target name</option>
                {(connectors.data ?? []).map((connector) => <option key={connector.id} value={connector.id}>{connector.name} · {connector.connector_type}</option>)}
              </select>
            </label>
          </div>
          <label className="field-label">Sample payload<CodeEditor value={form.test_payload} onChange={(value) => setForm({ ...form, test_payload: value })} language={form.input_mode === 'json' ? 'json' : form.input_mode === 'xml' ? 'xml' : 'text'} minRows={8} /></label>
          {formError && <div className="error-state compact">{formError}</div>}
          {build.error instanceof Error && <div className="error-state compact">{build.error.message}</div>}
          <button className="primary-button" disabled={build.isPending}>Build integration</button>
        </form>
      </section>
      <section className="panel">
        <h2>Generated output</h2>
        {build.data ? (
          <div className="page-stack">
            <div className="success-note"><strong>{build.data.endpoint_url}</strong><span>{build.data.next_steps.join(' · ')}</span></div>
            <CodeBlock title="curl" code={build.data.curl_example} language="bash" />
            <CodeBlock title="1C HTTP" code={build.data.onec_http_example} language="bash" />
            <JsonBlock title="Created objects" value={build.data.created} searchable={false} />
          </div>
        ) : (
          <JsonBlock title="Request preview" value={{ ...form, test_payload: form.input_mode === 'json' ? safeJson(form.test_payload) : form.test_payload }} searchable={false} />
        )}
      </section>
    </div>
  );
}
