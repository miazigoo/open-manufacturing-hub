export const docLinks: Record<string, string> = {
  'core.overview': '/docs/core/start/overview',
  'core.concepts': '/docs/core/start/concepts',
  'onec.overview': '/docs/onec/overview/overview',
  'onec.connector': '/docs/onec/tools/connector',
  'onec.odata-explorer': '/docs/onec/tools/odata-explorer',
  'onec.xml-tools': '/docs/onec/tools/xml-tools',
  'onec.cockpit': '/docs/onec/tools/cockpit',
  'onec.visual-flow-builder': '/docs/onec/tools/visual-flow-builder',
  'onec.troubleshooting': '/docs/onec/errors/troubleshooting',
  'integration-flows': '/docs/onec/tools/visual-flow-builder',
  'test-console': '/docs/onec/quick-start/quick-start',
  'timeline.errors': '/docs/onec/errors/errors-timeline',
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
