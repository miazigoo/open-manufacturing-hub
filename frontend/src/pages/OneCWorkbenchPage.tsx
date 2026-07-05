import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { onecWorkbenchApi } from '../api/onecWorkbench';
import { CodeEditor } from '../components/CodeEditor';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { useT } from '../i18n/useI18n';
import { formatDateTime } from '../utils';

const defaultXml = '<Документ><Номер>UPD-1001</Номер><СвПродПер><СвЮЛУч><ИННЮЛ>1234567890</ИННЮЛ></СвЮЛУч></СвПродПер></Документ>';
const defaultInput = { inn: '1234567890' };
const defaultExtract = { contractor_uuid: 'Ref_Key', contractor_name: 'Description' };

export function OneCWorkbenchPage() {
  const t = useT();
  const queryClient = useQueryClient();
  const [xmlForm, setXmlForm] = useState({ source_system: '1C UPD', target_system: '1C ERP', message_type: 'UPD', correlation_id: 'upd-1001', xml: defaultXml });
  const [lookupForm, setLookupForm] = useState({ connector_name: '1C ERP', resource: 'Catalog_Контрагенты', filter_template: "ИНН eq '{inn}'", input: asJson(defaultInput), extract: asJson(defaultExtract) });
  const [formError, setFormError] = useState<string | null>(null);

  const messages = useQuery({ queryKey: ['onec-workbench-messages'], queryFn: onecWorkbenchApi.messages });
  const templates = useQuery({ queryKey: ['operation-templates'], queryFn: onecWorkbenchApi.templates });
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['onec-workbench-messages'] });
    queryClient.invalidateQueries({ queryKey: ['operation-templates'] });
    queryClient.invalidateQueries({ queryKey: ['workflows'] });
    queryClient.invalidateQueries({ queryKey: ['events'] });
  };
  const sendXml = useMutation({ mutationFn: onecWorkbenchApi.sendXml, onSuccess: refresh });
  const lookup = useMutation({ mutationFn: onecWorkbenchApi.lookup });
  const installTemplates = useMutation({ mutationFn: onecWorkbenchApi.installTemplates, onSuccess: refresh });
  const installXmlBridge = useMutation({ mutationFn: onecWorkbenchApi.installXmlBridge, onSuccess: refresh });
  const installInn = useMutation({ mutationFn: onecWorkbenchApi.installInnLookupDemo, onSuccess: refresh });
  const installPrint = useMutation({ mutationFn: onecWorkbenchApi.installPrintPipeline, onSuccess: refresh });

  function submitXml(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    sendXml.mutate({ ...xmlForm, target_system: xmlForm.target_system || null, correlation_id: xmlForm.correlation_id || null });
  }

  function submitLookup(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    try {
      lookup.mutate({
        connector_name: lookupForm.connector_name,
        resource: lookupForm.resource,
        filter_template: lookupForm.filter_template,
        input: JSON.parse(lookupForm.input) as Record<string, unknown>,
        extract: JSON.parse(lookupForm.extract) as Record<string, string>,
      });
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Invalid JSON');
    }
  }

  const error = messages.error ?? templates.error;
  if (messages.isLoading || templates.isLoading) return <LoadingState label={t('onecWorkbench.loading')} />;
  if (error) return <ErrorState error={error} />;

  const latestInstall = installPrint.data ?? installInn.data ?? installXmlBridge.data;

  return (
    <div className="page-stack onec-workbench-page">
      <section className="page-header onec-hero">
        <span className="eyebrow">{t('onecWorkbench.eyebrow')}</span>
        <h1>{t('onecWorkbench.title')}</h1>
        <p>{t('onecWorkbench.subtitle')}</p>
      </section>

      <section className="workbench-grid">
        <form className="panel stack-form" onSubmit={submitXml}>
          <div className="panel-toolbar"><h2>{t('onecWorkbench.xmlInbound')}</h2><span className="microcopy">POST /api/onec/xml/inbound</span></div>
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">{t('common.source')}<input value={xmlForm.source_system} onChange={(event) => setXmlForm({ ...xmlForm, source_system: event.target.value })} /></label>
            <label className="field-label">{t('common.target')}<input value={xmlForm.target_system} onChange={(event) => setXmlForm({ ...xmlForm, target_system: event.target.value })} /></label>
            <label className="field-label">{t('common.type')}<input value={xmlForm.message_type} onChange={(event) => setXmlForm({ ...xmlForm, message_type: event.target.value })} /></label>
            <label className="field-label">{t('events.correlationId')}<input value={xmlForm.correlation_id} onChange={(event) => setXmlForm({ ...xmlForm, correlation_id: event.target.value })} /></label>
          </div>
          <label className="field-label">XML<CodeEditor value={xmlForm.xml} onChange={(value) => setXmlForm({ ...xmlForm, xml: value })} language="xml" minRows={8} /></label>
          {sendXml.error instanceof Error && <div className="error-state compact">{sendXml.error.message}</div>}
          <button className="primary-button" disabled={sendXml.isPending}>{t('onecWorkbench.sendXml')}</button>
          {sendXml.data && <div className="success-note"><strong>{t('onecWorkbench.messageCreated')}</strong><span>{sendXml.data.message_id}</span><Link className="primary-link" to={`/events/${sendXml.data.event_id}`}>{t('onec.openTimeline')}</Link></div>}
        </form>

        <form className="panel stack-form" onSubmit={submitLookup}>
          <div className="panel-toolbar"><h2>{t('onecWorkbench.lookupTest')}</h2><span className="microcopy">POST /api/onec/lookup/test</span></div>
          <label className="field-label">{t('connectors.onecInstance')}<input value={lookupForm.connector_name} onChange={(event) => setLookupForm({ ...lookupForm, connector_name: event.target.value })} /></label>
          <label className="field-label">Resource<input value={lookupForm.resource} onChange={(event) => setLookupForm({ ...lookupForm, resource: event.target.value })} /></label>
          <label className="field-label">Filter template<input value={lookupForm.filter_template} onChange={(event) => setLookupForm({ ...lookupForm, filter_template: event.target.value })} /></label>
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">Input JSON<CodeEditor value={lookupForm.input} onChange={(value) => setLookupForm({ ...lookupForm, input: value })} language="json" minRows={6} /></label>
            <label className="field-label">Extract JSON<CodeEditor value={lookupForm.extract} onChange={(value) => setLookupForm({ ...lookupForm, extract: value })} language="json" minRows={6} /></label>
          </div>
          {formError && <div className="error-state compact">{formError}</div>}
          {lookup.error instanceof Error && <div className="error-state compact">{lookup.error.message}</div>}
          <button className="primary-button" disabled={lookup.isPending}>{t('onecWorkbench.runLookup')}</button>
          <JsonBlock title={t('onecWorkbench.lookupResult')} value={lookup.data ?? {}} searchable={false} />
        </form>
      </section>

      <section className="workbench-grid lower">
        <div className="panel">
          <div className="panel-toolbar"><h2>{t('onecWorkbench.presets')}</h2><span className="microcopy">{latestInstall?.workflow_name ?? t('common.none')}</span></div>
          <div className="action-row wrap-actions">
            <button className="primary-button" onClick={() => installXmlBridge.mutate()} disabled={installXmlBridge.isPending}>{t('onecWorkbench.installXmlBridge')}</button>
            <button className="ghost-button" onClick={() => installInn.mutate()} disabled={installInn.isPending}>{t('onecWorkbench.installInn')}</button>
            <button className="ghost-button" onClick={() => installPrint.mutate()} disabled={installPrint.isPending}>{t('onecWorkbench.installPrint')}</button>
            <button className="ghost-button" onClick={() => installTemplates.mutate()} disabled={installTemplates.isPending}>{t('onecWorkbench.installTemplates')}</button>
          </div>
          <div className="template-list">
            {(templates.data ?? []).map((template) => (
              <article className="template-card" key={template.id}>
                <div><strong>{template.operation}</strong><span>{template.name}</span></div>
                <StatusBadge status={template.enabled ? 'ok' : 'unknown'} />
              </article>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-toolbar"><h2>{t('onecWorkbench.messages')}</h2><span className="microcopy">{messages.data?.length ?? 0}</span></div>
          <div className="message-list">
            {(messages.data ?? []).map((message) => (
              <article className="message-card" key={message.id}>
                <div><strong>{message.message_type}</strong><span>{message.source_system} → {message.target_system ?? t('common.unassigned')}</span><small>{formatDateTime(message.created_at)} · {message.payload_size_bytes} B</small></div>
                <StatusBadge status={message.status} />
                {message.event_id && <Link className="primary-link" to={`/events/${message.event_id}`}>{t('onec.openTimeline')}</Link>}
              </article>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
