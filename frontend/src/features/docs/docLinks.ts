export const docLinks: Record<string, string> = {
  'core.overview': '/docs/core/start/overview',
  'core.concepts': '/docs/core/start/concepts',
  'onec.start': '/docs/onec/start-here/beginner-path',
  'onec.overview': '/docs/onec/overview/overview',
  'onec.connector': '/docs/onec/tools/connector',
  'onec.odata-explorer': '/docs/onec/tools/odata-explorer',
  'onec.odata-chaining': '/docs/onec/tools/odata-chaining-fields',
  'onec.xml-tools': '/docs/onec/tools/xml-tools',
  'onec.cockpit': '/docs/onec/tools/cockpit',
  'onec.visual-flow-builder': '/docs/onec/tools/visual-flow-builder',
  'onec.troubleshooting': '/docs/onec/support/errors-timeline-artifacts',
  'integration-flows': '/docs/onec/tools/visual-flow-builder',
  'test-console': '/docs/onec/scenarios/onec-post-two-odata-json-endpoint',
  'timeline.errors': '/docs/onec/support/errors-timeline-artifacts',
  'queue': '/docs/core/start/concepts',
  'packages.store': '/docs/packages/packages/plugin-store',
  'auth.install': '/docs/auth/auth/install',
  'secrets.overview': '/docs/secrets/secrets/overview',
  'production.safety': '/docs/core/start/concepts',
  'audit.log': '/docs/core/start/concepts',
};

export function docUrl(docId: string) {
  return docLinks[docId] ?? '/docs';
}
