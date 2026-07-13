import { Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { API_BASE_URL } from '../api/client';
import { integrationBusApi } from '../api/integrationBus';
import { JsonBlock } from '../components/JsonBlock';
import { StatusBadge } from '../components/StatusBadge';
import { useT } from '../i18n/useI18n';

const scenarios = ['1C → Website/API', 'Website/API → 1C', '1C XML → 1C', '1C XML + OData lookup', '1C → Printer'];

export function OneCQuickSetupPage() {
  const t = useT();
  const install = useMutation({ mutationFn: integrationBusApi.installPresets });
  return (
    <div className="page-stack quick-setup-page">
      <section className="page-header onec-hero">
        <span className="eyebrow">{t('quick.eyebrow')}</span>
        <h1>{t('quick.title')}</h1>
        <p>{t('quick.subtitle')}</p>
        <div className="hero-meta"><button className="primary-button" onClick={() => install.mutate()} disabled={install.isPending}>{t('quick.install')}</button><Link className="ghost-link" to="/integration-bus">{t('nav.integrationBus')}</Link></div>
      </section>

      <section className="quick-steps">
        <article className="panel quick-step"><span>01</span><h2>{t('quick.stepSystem')}</h2><p>{t('quick.stepSystemText')}</p></article>
        <article className="panel quick-step"><span>02</span><h2>{t('quick.stepScenario')}</h2><div className="workflow-steps">{scenarios.map((item) => <span key={item}>{item}</span>)}</div></article>
        <article className="panel quick-step"><span>03</span><h2>{t('quick.stepEndpoint')}</h2><p>{t('quick.stepEndpointText')}</p></article>
        <article className="panel quick-step"><span>04</span><h2>{t('quick.stepTest')}</h2><p>{t('quick.stepTestText')}</p></article>
      </section>

      {install.error instanceof Error && <div className="error-state compact">{install.error.message}</div>}
      {install.data && (
        <section className="panel">
          <div className="panel-toolbar"><h2>{t('quick.generated')}</h2><StatusBadge status="ok" /></div>
          <div className="bus-list">
            {install.data.endpoints.map((endpoint) => (
              <article className="bus-card" key={endpoint.id}>
                <div><strong>{endpoint.name}</strong><span>{API_BASE_URL}/api/bus/in/{endpoint.slug}</span><small>{endpoint.input_mode} · {endpoint.response_mode} · {endpoint.processing_mode}</small></div>
                <Link className="primary-link" to="/integration-bus">{t('bus.testConsole')}</Link>
              </article>
            ))}
          </div>
          <JsonBlock title={t('quick.rawResult')} value={install.data} searchable={false} />
        </section>
      )}
    </div>
  );
}
