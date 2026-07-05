import { FormEvent, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { integrationBusApi } from '../api/integrationBus';
import { testConsoleApi } from '../api/testConsole';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { getExternalErrorTranslation } from '../i18n/errors';
import { useI18n } from '../i18n/useI18n';

const jsonSample = asJson({ warehouse_id: 'MAIN', target_order_id: 'SO-1001', items: [] });
const xmlSample = '<Документ><Номер>UPD-1001</Номер><ИНН>1234567890</ИНН></Документ>';
const rawSample = 'free-form integration message';

function sampleForMode(mode: string) {
  if (mode === 'xml') return xmlSample;
  if (mode === 'raw_text') return rawSample;
  return jsonSample;
}

function normalizeTimelineUrl(url: string) {
  if (url.startsWith('/events/')) return url;
  if (/^[a-f0-9-]{20,}$/i.test(url)) return `/events/${url}`;
  return url;
}

export function TestConsolePage() {
  const { language, t } = useI18n();
  const [searchParams] = useSearchParams();
  const exampleId = searchParams.get('exampleId');
  const endpoints = useQuery({ queryKey: ['bus-endpoints'], queryFn: integrationBusApi.endpoints });
  const docsExample = useQuery({ queryKey: ['docs-example', exampleId], queryFn: () => testConsoleApi.docsExample(exampleId!), enabled: Boolean(exampleId) });
  const [form, setForm] = useState({ endpoint_id: '', input_mode: 'json', headers_json: '{}', body: jsonSample });
  const [formError, setFormError] = useState<string | null>(null);
  const send = useMutation({
    mutationFn: (payload: { dry_run: boolean; headers: Record<string, string>; bodyJson: Record<string, unknown> | null }) =>
      testConsoleApi.send({
        endpoint_id: form.endpoint_id,
        input_mode: form.input_mode,
        headers_json: payload.headers,
        body_text: form.body,
        body_json: payload.bodyJson,
        dry_run: payload.dry_run,
      }),
  });

  useEffect(() => {
    if (!docsExample.data || endpoints.isLoading) return;
    const endpoint = endpoints.data?.find((item) => item.slug === docsExample.data.endpoint_slug);
    setForm({
      endpoint_id: endpoint?.id ?? '',
      input_mode: docsExample.data.input_mode,
      headers_json: JSON.stringify(docsExample.data.headers ?? {}, null, 2),
      body: docsExample.data.input_mode === 'json' ? JSON.stringify(docsExample.data.body ?? {}, null, 2) : docsExample.data.body_text ?? '',
    });
  }, [docsExample.data, endpoints.data, endpoints.isLoading]);

  if (endpoints.isLoading) return <LoadingState label={t('integration.testConsoleLoading')} />;
  if (endpoints.error) return <ErrorState error={endpoints.error} />;

  function parsePayload(dryRun: boolean) {
    setFormError(null);
    let headers: Record<string, string>;
    let bodyJson: Record<string, unknown> | null = null;
    try {
      headers = JSON.parse(form.headers_json || '{}') as Record<string, string>;
    } catch {
      setFormError(t('integration.invalidHeaders'));
      return null;
    }
    if (form.input_mode === 'json') {
      try {
        bodyJson = JSON.parse(form.body || '{}') as Record<string, unknown>;
      } catch {
        setFormError(t('integration.invalidBody'));
        return null;
      }
    }
    return { dry_run: dryRun, headers, bodyJson };
  }

  function run(dryRun: boolean) {
    const payload = parsePayload(dryRun);
    if (payload) send.mutate(payload);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    run(false);
  }

  const timelineUrl = send.data?.timeline_url ? normalizeTimelineUrl(send.data.timeline_url) : null;
  const externalError = send.data?.external_error as { code?: string } | undefined;
  const translatedError = externalError ? getExternalErrorTranslation(externalError.code, t) : null;

  return (
    <div className="page-stack two-column-page">
      <form className="panel form-panel stack-form" onSubmit={submit}>
        <span className="eyebrow">{t('integration.testConsole')}</span>
        <h1>{t('integration.sendRequests')}</h1>
        {docsExample.data && (
          <div className="docs-example-loaded">
            <strong>{t('integration.loadedDocsExample', { title: docsExample.data.title[language] ?? docsExample.data.title.en ?? docsExample.data.id })}</strong>
            <span>{t('integration.endpointSlug', { slug: docsExample.data.endpoint_slug })}</span>
            {!form.endpoint_id && <small>{t('integration.endpointMissing')}</small>}
          </div>
        )}
        {docsExample.error instanceof Error && <div className="error-state compact">{docsExample.error.message}</div>}
        <label className="field-label" data-tour="test-endpoint">
          {t('integration.endpoint')}
          <select
            value={form.endpoint_id}
            onChange={(event) => {
              const endpoint = endpoints.data?.find((item) => item.id === event.target.value);
              const nextMode = endpoint?.input_mode ?? form.input_mode;
              setForm({ ...form, endpoint_id: event.target.value, input_mode: nextMode, body: sampleForMode(nextMode) });
            }}
          >
            <option value="">{t('integration.selectEndpoint')}</option>
            {(endpoints.data ?? []).map((endpoint) => (
              <option key={endpoint.id} value={endpoint.id}>{endpoint.name} · /api/bus/in/{endpoint.slug}</option>
            ))}
          </select>
        </label>
        <label className="field-label">
          {t('integration.inputMode')}
          <select value={form.input_mode} onChange={(event) => setForm({ ...form, input_mode: event.target.value, body: sampleForMode(event.target.value) })}>
            <option value="json">json</option>
            <option value="xml">xml</option>
            <option value="raw_text">raw_text</option>
          </select>
        </label>
        <label className="field-label">{t('integration.headersJson')}<textarea value={form.headers_json} onChange={(event) => setForm({ ...form, headers_json: event.target.value })} /></label>
        <label className="field-label" data-tour="test-body">{t('integration.body')}<textarea value={form.body} onChange={(event) => setForm({ ...form, body: event.target.value })} /></label>
        {formError && <div className="error-state compact">{formError}</div>}
        {send.error instanceof Error && <div className="error-state compact">{send.error.message}</div>}
        <div className="action-row" data-tour="test-actions">
          <button className="primary-button" disabled={!form.endpoint_id || send.isPending}>{t('integration.send')}</button>
          <button type="button" className="ghost-button" disabled={!form.endpoint_id || send.isPending} onClick={() => run(true)}>{t('common.buttons.dryRun')}</button>
        </div>
      </form>
      <section className="page-stack">
        {timelineUrl && <Link className="primary-link" to={timelineUrl}>{t('integration.openLastTimeline')}</Link>}
        {translatedError && <div className="error-state compact"><strong>{translatedError.title}</strong><span>{translatedError.hint}</span></div>}
        {send.data?.external_error && <JsonBlock title={t('integration.externalError')} value={send.data.external_error} searchable={false} />}
        <JsonBlock title={t('integration.response')} value={send.data ?? { hint: t('integration.responseHint') }} searchable />
      </section>
    </div>
  );
}
