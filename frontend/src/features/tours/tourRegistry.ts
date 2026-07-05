export type TourId = 'onec-cockpit-first-tour' | 'odata-explorer-first-tour' | 'visual-flow-builder-first-tour' | 'test-console-first-tour' | 'event-timeline-first-tour';

export interface TourStep {
  target: string;
  title: string;
  body: string;
}

export interface TourDefinition {
  id: TourId;
  title: string;
  steps: TourStep[];
}

export const tourRegistry: Record<TourId, TourDefinition> = {
  'onec-cockpit-first-tour': {
    id: 'onec-cockpit-first-tour',
    title: '1C Cockpit first run',
    steps: [
      { target: "[data-tour='create-integration']", title: 'Create integration', body: 'Start here when you need a new 1C route.' },
      { target: "[data-tour='recent-events']", title: 'Recent events', body: 'Use recent events to jump into timelines and errors.' },
    ],
  },
  'odata-explorer-first-tour': {
    id: 'odata-explorer-first-tour',
    title: 'OData lookup tour',
    steps: [
      { target: "[data-tour='odata-connector']", title: 'Select connector', body: 'Choose the 1C connector that exposes OData.' },
      { target: "[data-tour='odata-query']", title: 'Run query', body: 'Test resource, filter and select before using them in a flow.' },
      { target: "[data-tour='odata-lookup']", title: 'Create lookup', body: 'Save stable OData queries as lookup templates.' },
    ],
  },
  'visual-flow-builder-first-tour': {
    id: 'visual-flow-builder-first-tour',
    title: 'Visual flow builder tour',
    steps: [
      { target: "[data-tour='flow-presets']", title: 'Presets', body: 'Install a tested preset when you need a fast working baseline.' },
      { target: "[data-tour='flow-create']", title: 'Create flow', body: 'Define endpoint, matcher and target action without code.' },
      { target: "[data-tour='flow-detail']", title: 'Test and open builder', body: 'Run a test request or open the detailed visual builder.' },
    ],
  },
  'test-console-first-tour': {
    id: 'test-console-first-tour',
    title: 'Test console tour',
    steps: [
      { target: "[data-tour='test-endpoint']", title: 'Endpoint', body: 'Select the endpoint that should receive your test request.' },
      { target: "[data-tour='test-body']", title: 'Payload', body: 'Paste JSON, XML or raw text exactly as the external system sends it.' },
      { target: "[data-tour='test-actions']", title: 'Send or dry run', body: 'Use dry run when you need artifacts without external side effects.' },
    ],
  },
  'event-timeline-first-tour': {
    id: 'event-timeline-first-tour',
    title: 'Timeline tour',
    steps: [
      { target: "[data-tour='timeline-runs']", title: 'Runs', body: 'Every replay creates a separate run so history is preserved.' },
      { target: "[data-tour='timeline-steps']", title: 'Steps', body: 'Select failed steps to inspect normalized and original errors.' },
      { target: "[data-tour='timeline-artifacts']", title: 'Artifacts', body: 'Artifacts contain raw payloads, mapped payloads, requests and responses.' },
    ],
  },
};
