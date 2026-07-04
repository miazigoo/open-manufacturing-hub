import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { integrationBusApi } from '../api/integrationBus';
import { testConsoleApi } from '../api/testConsole';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

const jsonSample = '{\n  "warehouse_id": "MAIN",\n  "target_order_id": "SO-1001",\n  "items": []\n}';
const xmlSample = '<Документ><Номер>UPD-1001</Номер></Документ>';
const rawSample = 'free-form integration message';

function sampleForMode(mode: string) {
  if (mode === 'json') return jsonSample;
  if (mode === 'raw_text') return rawSample;
  return xmlSample;
}

export function SavedTestCasesPage() {
  const queryClient = useQueryClient();
  const cases = useQuery({ queryKey: ['test-cases'], queryFn: testConsoleApi.listCases });
  const endpoints = useQuery({ queryKey: ['bus-endpoints'], queryFn: integrationBusApi.endpoints });
  const [form, setForm] = useState({ name: 'UPD XML sample', endpoint_id: '', input_mode: 'xml', body_text: xmlSample });
  const [formError, setFormError] = useState<string | null>(null);
  const [last, setLast] = useState<unknown>(null);
  const create = useMutation({
    mutationFn: (payload: { bodyJson: Record<string, unknown> | null }) => testConsoleApi.createCase({
      name: form.name,
      endpoint_id: form.endpoint_id || null,
      input_mode: form.input_mode,
      body_text: form.body_text,
      body_json: payload.bodyJson,
      headers_json: { 'Content-Type': form.input_mode === 'xml' ? 'application/xml' : 'application/json' },
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['test-cases'] });
      setFormError(null);
    },
  });
  const run = useMutation({ mutationFn: (id: string) => testConsoleApi.runCase(id), onSuccess: (data) => { setLast(data); queryClient.invalidateQueries({ queryKey: ['test-cases'] }); } });
  const remove = useMutation({ mutationFn: testConsoleApi.deleteCase, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['test-cases'] }) });
  const error = cases.error ?? endpoints.error;

  if (cases.isLoading || endpoints.isLoading) return <LoadingState label="Loading test cases" />;
  if (error) return <ErrorState error={error} />;

  function submit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    let bodyJson: Record<string, unknown> | null = null;
    if (form.input_mode === 'json') {
      try {
        bodyJson = JSON.parse(form.body_text || '{}') as Record<string, unknown>;
      } catch {
        setFormError('Body JSON is invalid. Fix it before saving the test case.');
        return;
      }
    }
    create.mutate({ bodyJson });
  }

  return (
    <div className="page-stack two-column-page">
      <form className="panel form-panel stack-form" onSubmit={submit}>
        <span className="eyebrow">Saved Test Cases</span>
        <h1>Reusable integration checks</h1>
        <label className="field-label">Name<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
        <label className="field-label">
          Endpoint
          <select value={form.endpoint_id} onChange={(event) => setForm({ ...form, endpoint_id: event.target.value })}>
            <option value="">Unlinked</option>
            {(endpoints.data ?? []).map((endpoint) => <option key={endpoint.id} value={endpoint.id}>{endpoint.name}</option>)}
          </select>
        </label>
        <label className="field-label">
          Input
          <select value={form.input_mode} onChange={(event) => setForm({ ...form, input_mode: event.target.value, body_text: sampleForMode(event.target.value) })}>
            <option value="json">json</option>
            <option value="xml">xml</option>
            <option value="raw_text">raw_text</option>
          </select>
        </label>
        <label className="field-label">Body<textarea value={form.body_text} onChange={(event) => setForm({ ...form, body_text: event.target.value })} /></label>
        {formError && <div className="error-state compact">{formError}</div>}
        {create.error instanceof Error && <div className="error-state compact">{create.error.message}</div>}
        <button className="primary-button" disabled={create.isPending}>Save Test Case</button>
      </form>
      <section className="page-stack">
        {(run.error instanceof Error || remove.error instanceof Error) && <div className="error-state compact">{(run.error as Error | null)?.message ?? (remove.error as Error | null)?.message}</div>}
        <section className="table-panel">
          <table>
            <thead><tr><th>Name</th><th>Input</th><th>Last run</th><th>Actions</th></tr></thead>
            <tbody>
              {(cases.data ?? []).map((item) => (
                <tr key={item.id}>
                  <td><strong>{item.name}</strong><small>{item.description}</small></td>
                  <td>{item.input_mode}</td>
                  <td>{item.last_run_status ? <StatusBadge status={item.last_run_status === 'success' ? 'ok' : 'warning'} label={item.last_run_status} /> : '—'}</td>
                  <td>
                    <div className="action-row">
                      <button className="ghost-button" disabled={run.isPending} onClick={() => run.mutate(item.id)}>Run</button>
                      {item.last_run_event_id && <Link className="primary-link" to={`/events/${item.last_run_event_id}`}>Timeline</Link>}
                      <button className="ghost-button" disabled={remove.isPending} onClick={() => remove.mutate(item.id)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <JsonBlock title="Last run" value={(last as Record<string, unknown> | null) ?? { hint: 'Run a saved case to inspect the response.' }} searchable={false} />
      </section>
    </div>
  );
}
