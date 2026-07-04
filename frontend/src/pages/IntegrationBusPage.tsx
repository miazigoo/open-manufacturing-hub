import { FormEvent, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { IntegrationEndpoint, integrationBusApi } from '../api/integrationBus';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { useT } from '../i18n/useI18n';

const sampleJson = { warehouse_id: 'MAIN', target_order_id: 'SO-1001', items: [] };
const sampleXml = '<Документ><Номер>UPD-1001</Номер></Документ>';

export function IntegrationBusPage() {
  const t = useT();
  const queryClient = useQueryClient();
  const endpoints = useQuery({ queryKey: ['bus-endpoints'], queryFn: integrationBusApi.endpoints });
  const routes = useQuery({ queryKey: ['bus-routes'], queryFn: integrationBusApi.routes });
  const lookups = useQuery({ queryKey: ['bus-lookups'], queryFn: integrationBusApi.lookups });
  const [endpointForm, setEndpointForm] = useState({ name: 'Website contractor lookup', slug: 'site-contractor-lookup-custom', input_mode: 'json', response_mode: 'sync_response', default_event_type: 'ContractorLookupRequested', default_source_system: 'Website', default_target_system: '1C ERP', auth_mode: 'none', token: '' });
  const [routeForm, setRouteForm] = useState({ name: 'Route contractor lookup', event_type: 'ContractorLookupRequested', target_system: '1C ERP', priority: '50' });
  const [consoleForm, setConsoleForm] = useState({ slug: '', input_mode: 'json', headers: '{}', body: asJson(sampleJson) });
  const [formError, setFormError] = useState<string | null>(null);

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['bus-endpoints'] });
    queryClient.invalidateQueries({ queryKey: ['bus-routes'] });
    queryClient.invalidateQueries({ queryKey: ['bus-lookups'] });
  };
  const createEndpoint = useMutation({ mutationFn: integrationBusApi.createEndpoint, onSuccess: refresh });
  const createRoute = useMutation({ mutationFn: integrationBusApi.createRoute, onSuccess: refresh });
  const installPresets = useMutation({ mutationFn: integrationBusApi.installPresets, onSuccess: refresh });
  const sendTest = useMutation({ mutationFn: ({ slug, inputMode, headers, body }: { slug: string; inputMode: string; headers: Record<string, string>; body: string }) => {
    if (inputMode === 'xml') return integrationBusApi.sendText(slug, body, 'application/xml', headers);
    if (inputMode === 'raw_text') return integrationBusApi.sendText(slug, body, 'text/plain', headers);
    return integrationBusApi.sendJson(slug, JSON.parse(body), headers);
  }});

  const selectedEndpoint = useMemo(() => endpoints.data?.find((item) => item.slug === consoleForm.slug), [endpoints.data, consoleForm.slug]);
  const error = endpoints.error ?? routes.error ?? lookups.error;
  if (endpoints.isLoading || routes.isLoading || lookups.isLoading) return <LoadingState label={t('bus.loading')} />;
  if (error) return <ErrorState error={error} />;

  function submitEndpoint(event: FormEvent) {
    event.preventDefault();
    createEndpoint.mutate({
      name: endpointForm.name,
      slug: endpointForm.slug,
      input_mode: endpointForm.input_mode,
      response_mode: endpointForm.response_mode,
      default_event_type: endpointForm.default_event_type,
      default_source_system: endpointForm.default_source_system || null,
      default_target_system: endpointForm.default_target_system || null,
      auth_mode: endpointForm.auth_mode,
      auth_config_json: endpointForm.auth_mode === 'static_token' ? { token: endpointForm.token } : {},
    });
  }

  function submitRoute(event: FormEvent) {
    event.preventDefault();
    createRoute.mutate({ name: routeForm.name, event_type: routeForm.event_type || null, target_system: routeForm.target_system || null, priority: Number(routeForm.priority) || 100 });
  }

  function submitTest(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    try {
      sendTest.mutate({ slug: consoleForm.slug, inputMode: consoleForm.input_mode, headers: JSON.parse(consoleForm.headers), body: consoleForm.body });
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Invalid JSON');
    }
  }

  function selectEndpoint(endpoint: IntegrationEndpoint) {
    setConsoleForm({ slug: endpoint.slug, input_mode: endpoint.input_mode, headers: endpoint.auth_mode === 'static_token' ? asJson({ 'X-OMH-Token': 'secret' }) : '{}', body: endpoint.input_mode === 'xml' ? sampleXml : asJson(sampleJson) });
  }

  return (
    <div className="page-stack integration-bus-page">
      <section className="page-header onec-hero">
        <span className="eyebrow">{t('bus.eyebrow')}</span>
        <h1>{t('bus.title')}</h1>
        <p>{t('bus.subtitle')}</p>
        <div className="hero-meta"><button className="primary-button" onClick={() => installPresets.mutate()} disabled={installPresets.isPending}>{t('bus.installPresets')}</button><Link className="ghost-link" to="/onec-quick-setup">{t('bus.quickSetup')}</Link></div>
      </section>

      <section className="bus-grid">
        <form className="panel stack-form" onSubmit={submitEndpoint}>
          <div className="panel-toolbar"><h2>{t('bus.newEndpoint')}</h2><span className="microcopy">POST /api/bus/in/{endpointForm.slug || '{slug}'}</span></div>
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">{t('common.name')}<input value={endpointForm.name} onChange={(event) => setEndpointForm({ ...endpointForm, name: event.target.value })} /></label>
            <label className="field-label">Slug<input value={endpointForm.slug} onChange={(event) => setEndpointForm({ ...endpointForm, slug: event.target.value })} /></label>
            <label className="field-label">{t('bus.inputMode')}<select value={endpointForm.input_mode} onChange={(event) => setEndpointForm({ ...endpointForm, input_mode: event.target.value })}><option value="json">json</option><option value="xml">xml</option><option value="raw_text">raw_text</option><option value="form">form</option><option value="multipart_file">multipart_file</option></select></label>
            <label className="field-label">{t('bus.responseMode')}<select value={endpointForm.response_mode} onChange={(event) => setEndpointForm({ ...endpointForm, response_mode: event.target.value })}><option value="accepted_event">accepted_event</option><option value="accepted_message">accepted_message</option><option value="sync_response">sync_response</option><option value="proxy_response">proxy_response</option></select></label>
            <label className="field-label">{t('events.eventType')}<input value={endpointForm.default_event_type} onChange={(event) => setEndpointForm({ ...endpointForm, default_event_type: event.target.value })} /></label>
            <label className="field-label">{t('common.source')}<input value={endpointForm.default_source_system} onChange={(event) => setEndpointForm({ ...endpointForm, default_source_system: event.target.value })} /></label>
            <label className="field-label">{t('common.target')}<input value={endpointForm.default_target_system} onChange={(event) => setEndpointForm({ ...endpointForm, default_target_system: event.target.value })} /></label>
            <label className="field-label">Auth<select value={endpointForm.auth_mode} onChange={(event) => setEndpointForm({ ...endpointForm, auth_mode: event.target.value })}><option value="none">none</option><option value="static_token">static_token</option></select></label>
          </div>
          {endpointForm.auth_mode === 'static_token' && <label className="field-label">Token<input value={endpointForm.token} onChange={(event) => setEndpointForm({ ...endpointForm, token: event.target.value })} /></label>}
          {createEndpoint.error instanceof Error && <div className="error-state compact">{createEndpoint.error.message}</div>}
          <button className="primary-button" disabled={createEndpoint.isPending}>{t('bus.createEndpoint')}</button>
        </form>

        <form className="panel stack-form" onSubmit={submitTest}>
          <div className="panel-toolbar"><h2>{t('bus.testConsole')}</h2><span className="microcopy">{selectedEndpoint ? `/api/bus/in/${selectedEndpoint.slug}` : t('bus.selectEndpoint')}</span></div>
          <label className="field-label">Endpoint<select value={consoleForm.slug} onChange={(event) => {
            const next = endpoints.data?.find((endpoint) => endpoint.slug === event.target.value);
            if (next) selectEndpoint(next); else setConsoleForm({ ...consoleForm, slug: event.target.value });
          }}><option value="">{t('bus.selectEndpoint')}</option>{(endpoints.data ?? []).map((endpoint) => <option key={endpoint.id} value={endpoint.slug}>{endpoint.name} · {endpoint.slug}</option>)}</select></label>
          <label className="field-label">Headers JSON<textarea value={consoleForm.headers} onChange={(event) => setConsoleForm({ ...consoleForm, headers: event.target.value })} spellCheck={false} /></label>
          <label className="field-label">Body<textarea value={consoleForm.body} onChange={(event) => setConsoleForm({ ...consoleForm, body: event.target.value })} spellCheck={false} /></label>
          {formError && <div className="error-state compact">{formError}</div>}
          {sendTest.error instanceof Error && <div className="error-state compact">{sendTest.error.message}</div>}
          <button className="primary-button" disabled={!consoleForm.slug || sendTest.isPending}>{t('bus.sendTest')}</button>
          <JsonBlock title={t('bus.response')} value={sendTest.data ?? {}} searchable={false} />
        </form>
      </section>

      <section className="bus-grid lower">
        <div className="panel"><div className="panel-toolbar"><h2>{t('bus.endpoints')}</h2><span className="microcopy">{endpoints.data?.length ?? 0}</span></div><div className="bus-list">{(endpoints.data ?? []).map((endpoint) => <article className="bus-card" key={endpoint.id} onClick={() => selectEndpoint(endpoint)}><div><strong>{endpoint.name}</strong><span>/api/bus/in/{endpoint.slug}</span><small>{endpoint.input_mode} · {endpoint.response_mode}</small></div><StatusBadge status={endpoint.enabled ? 'ok' : 'unknown'} /></article>)}</div></div>
        <div className="panel"><div className="panel-toolbar"><h2>{t('bus.routes')}</h2><span className="microcopy">{routes.data?.length ?? 0}</span></div><form className="stack-form inline-create" onSubmit={submitRoute}><input value={routeForm.name} onChange={(event) => setRouteForm({ ...routeForm, name: event.target.value })} placeholder={t('common.name')} /><input value={routeForm.event_type} onChange={(event) => setRouteForm({ ...routeForm, event_type: event.target.value })} placeholder={t('events.eventType')} /><input value={routeForm.target_system} onChange={(event) => setRouteForm({ ...routeForm, target_system: event.target.value })} placeholder={t('common.target')} /><button className="ghost-button" disabled={createRoute.isPending}>{t('common.create')}</button></form><div className="bus-list">{(routes.data ?? []).map((route) => <article className="bus-card" key={route.id}><div><strong>{route.priority} · {route.name}</strong><span>{route.event_type ?? t('common.all')} → {route.target_system ?? t('common.unassigned')}</span><small>{route.operation ?? t('common.none')}</small></div><StatusBadge status={route.enabled ? 'ok' : 'unknown'} /></article>)}</div></div>
      </section>

      <section className="panel"><div className="panel-toolbar"><h2>{t('bus.lookups')}</h2><span className="microcopy">{lookups.data?.length ?? 0}</span></div><div className="bus-list lookup-grid">{(lookups.data ?? []).map((lookup) => <article className="bus-card" key={lookup.id}><div><strong>{lookup.name}</strong><span>{lookup.resource}</span><small>{lookup.filter_template}</small></div><JsonBlock title="extract" value={lookup.extract_json} searchable={false} /></article>)}</div></section>
    </div>
  );
}
