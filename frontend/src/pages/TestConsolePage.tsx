import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { integrationBusApi } from '../api/integrationBus';
import { testConsoleApi } from '../api/testConsole';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';

export function TestConsolePage() {
  const endpoints = useQuery({ queryKey: ['bus-endpoints'], queryFn: integrationBusApi.endpoints });
  const [form, setForm] = useState({ endpoint_id: '', input_mode: 'json', headers_json: '{}', body: asJson({ warehouse_id: 'MAIN', target_order_id: 'SO-1001', items: [] }) });
  const send = useMutation({ mutationFn: (dry_run: boolean) => testConsoleApi.send({ endpoint_id: form.endpoint_id, input_mode: form.input_mode, headers_json: JSON.parse(form.headers_json) as Record<string, string>, body_text: form.body, body_json: form.input_mode === 'json' ? JSON.parse(form.body) as Record<string, unknown> : null, dry_run }) });
  if (endpoints.isLoading) return <LoadingState label="Loading test console" />;
  if (endpoints.error) return <ErrorState error={endpoints.error} />;
  function submit(event: FormEvent) { event.preventDefault(); send.mutate(false); }
  return <div className="page-stack two-column-page"><form className="panel form-panel stack-form" onSubmit={submit}><span className="eyebrow">Test Console</span><h1>Send integration requests</h1><label className="field-label">Endpoint<select value={form.endpoint_id} onChange={(event) => { const endpoint = endpoints.data?.find((item) => item.id === event.target.value); setForm({ ...form, endpoint_id: event.target.value, input_mode: endpoint?.input_mode ?? form.input_mode }); }}><option value="">Select endpoint</option>{(endpoints.data ?? []).map((endpoint) => <option key={endpoint.id} value={endpoint.id}>{endpoint.name} · /api/bus/in/{endpoint.slug}</option>)}</select></label><label className="field-label">Input mode<select value={form.input_mode} onChange={(event) => setForm({ ...form, input_mode: event.target.value })}><option value="json">json</option><option value="xml">xml</option><option value="raw_text">raw_text</option></select></label><label className="field-label">Headers JSON<textarea value={form.headers_json} onChange={(event) => setForm({ ...form, headers_json: event.target.value })} /></label><label className="field-label">Body<textarea value={form.body} onChange={(event) => setForm({ ...form, body: event.target.value })} /></label><div className="action-row"><button className="primary-button" disabled={!form.endpoint_id || send.isPending}>Send</button><button type="button" className="ghost-button" disabled={!form.endpoint_id || send.isPending} onClick={() => send.mutate(true)}>Dry Run</button></div></form><section className="page-stack">{send.data?.timeline_url && <Link className="primary-link" to={send.data.timeline_url}>Open Last Timeline</Link>}{send.data?.external_error && <JsonBlock title="External Error" value={send.data.external_error} searchable={false} />}<JsonBlock title="Response" value={send.data ?? {}} searchable /></section></div>;
}
