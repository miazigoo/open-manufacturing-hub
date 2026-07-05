import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { integrationFlowsApi } from '../../api/integrationFlows';
import { onboardingApi } from '../../api/onboarding';
import { ExampleRunnerButton } from './ExampleRunnerButton';

export function FirstIntegrationWizard() {
  const queryClient = useQueryClient();
  const installPreset = useMutation({
    mutationFn: integrationFlowsApi.installTwoODataToEndpoint,
    onSuccess: async () => {
      await onboardingApi.complete('create_first_integration_flow', { preset: 'onec-post-two-odata-to-endpoint' });
      queryClient.invalidateQueries({ queryKey: ['onboarding-state'] });
      queryClient.invalidateQueries({ queryKey: ['integration-flows'] });
    },
  });
  return (
    <div className="page-stack first-integration-page">
      <section className="hero-panel first-integration-hero product-page-header">
        <div>
          <span className="eyebrow">First integration wizard</span>
          <h1>1C POST {'->'} OData lookup {'->'} JSON {'->'} endpoint.</h1>
          <p>This guided path creates a practical first route. It stays simpler than Integration Designer and gives you clear next actions.</p>
          <div className="hero-meta"><button className="primary-button" onClick={() => installPreset.mutate()} disabled={installPreset.isPending}>Install working preset</button><Link className="ghost-button" to="/integration-flows">Open Integration Flows</Link></div>
          {installPreset.error instanceof Error && <div className="error-state compact">{installPreset.error.message}</div>}
        </div>
      </section>
      <section className="wizard-roadmap">
        {[
          ['01', 'Choose scenario', 'Main path: 1C POST -> two OData lookups -> JSON endpoint.'],
          ['02', 'Select/create source endpoint', 'The preset creates an inbound endpoint for test requests.'],
          ['03', 'Select 1C connector', 'Use Connectors page to register real OData credentials.'],
          ['04', 'Configure OData lookup', 'Open OData Explorer to verify resource, filter and selected fields.'],
          ['05', 'Configure target REST connector', 'Use connector JSON or secret references for auth.'],
          ['06', 'Build target JSON', 'Visual builder transforms lookup result and source payload.'],
          ['07', 'Send test request', 'Use Test Console or run the safe example below.'],
          ['08', 'Open Timeline', 'Inspect artifacts, request, response and external errors.'],
          ['09', 'Enable flow', 'When test artifacts are correct, keep the flow enabled.'],
        ].map(([step, title, body]) => <article className="panel wizard-roadmap-card" key={step}><span className="step-index">{step}</span><h2>{title}</h2><p>{body}</p></article>)}
      </section>
      <section className="panel">
        <div className="panel-toolbar"><div><span className="eyebrow">Safe test</span><h2>Run the example and open timeline</h2></div><ExampleRunnerButton exampleId="onec_post_to_api" /></div>
      </section>
    </div>
  );
}
