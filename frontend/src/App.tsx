import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { LoadingState } from './components/LoadingState';
import { PackageGate } from './components/product/PackageGate';
import { useT } from './i18n/useI18n';

const DashboardPage = lazy(() => import('./pages/DashboardPage').then((m) => ({ default: m.DashboardPage })));
const EventJournalPage = lazy(() => import('./pages/EventJournalPage').then((m) => ({ default: m.EventJournalPage })));
const EventTimelinePage = lazy(() => import('./pages/EventTimelinePage').then((m) => ({ default: m.EventTimelinePage })));
const IncidentsPage = lazy(() => import('./pages/IncidentsPage').then((m) => ({ default: m.IncidentsPage })));
const IncidentDetailsPage = lazy(() => import('./pages/IncidentDetailsPage').then((m) => ({ default: m.IncidentDetailsPage })));
const HealthPage = lazy(() => import('./pages/HealthPage').then((m) => ({ default: m.HealthPage })));
const ConnectorsPage = lazy(() => import('./pages/ConnectorsPage').then((m) => ({ default: m.ConnectorsPage })));
const SecretsPage = lazy(() => import('./pages/SecretsPage').then((m) => ({ default: m.SecretsPage })));
const PackagesPage = lazy(() => import('./pages/PackagesPage').then((m) => ({ default: m.PackagesPage })));
const PackageDetailsPage = lazy(() => import('./pages/PackageDetailsPage').then((m) => ({ default: m.PackageDetailsPage })));
const PluginStorePage = lazy(() => import('./pages/PluginStorePage').then((m) => ({ default: m.PluginStorePage })));
const IntegrationBusPage = lazy(() => import('./pages/IntegrationBusPage').then((m) => ({ default: m.IntegrationBusPage })));
const IntegrationFlowsPage = lazy(() => import('./pages/IntegrationFlowsPage').then((m) => ({ default: m.IntegrationFlowsPage })));
const OperationKeysPage = lazy(() => import('./pages/OperationKeysPage').then((m) => ({ default: m.OperationKeysPage })));
const VisualFlowBuilderPage = lazy(() => import('./pages/VisualFlowBuilderPage').then((m) => ({ default: m.VisualFlowBuilderPage })));
const IntegrationDesignerPage = lazy(() => import('./pages/IntegrationDesignerPage').then((m) => ({ default: m.IntegrationDesignerPage })));
const ScenarioLibraryPage = lazy(() => import('./pages/ScenarioLibraryPage').then((m) => ({ default: m.ScenarioLibraryPage })));
const ODataConnectionsPage = lazy(() => import('./pages/ODataConnectionsPage').then((m) => ({ default: m.ODataConnectionsPage })));
const ODataExplorerPage = lazy(() => import('./pages/ODataExplorerPage').then((m) => ({ default: m.ODataExplorerPage })));
const XmlToolsPage = lazy(() => import('./pages/XmlToolsPage').then((m) => ({ default: m.XmlToolsPage })));
const TestConsolePage = lazy(() => import('./pages/TestConsolePage').then((m) => ({ default: m.TestConsolePage })));
const TrainingPage = lazy(() => import('./pages/TrainingPage').then((m) => ({ default: m.TrainingPage })));
const SavedTestCasesPage = lazy(() => import('./pages/SavedTestCasesPage').then((m) => ({ default: m.SavedTestCasesPage })));
const OneCQuickSetupPage = lazy(() => import('./pages/OneCQuickSetupPage').then((m) => ({ default: m.OneCQuickSetupPage })));
const ExecutionStepsPage = lazy(() => import('./pages/ExecutionStepsPage').then((m) => ({ default: m.ExecutionStepsPage })));
const EnterpriseRuntimePages = () => import('./pages/EnterpriseRuntimePages');
const IntegrationQueuePage = lazy(() => EnterpriseRuntimePages().then((m) => ({ default: m.IntegrationQueuePage })));
const QueueItemDetailsPage = lazy(() => EnterpriseRuntimePages().then((m) => ({ default: m.QueueItemDetailsPage })));
const DeadLetterQueuePage = lazy(() => EnterpriseRuntimePages().then((m) => ({ default: m.DeadLetterQueuePage })));
const TransactionMonitorPage = lazy(() => EnterpriseRuntimePages().then((m) => ({ default: m.TransactionMonitorPage })));
const RuntimeBusinessObjectsPage = lazy(() => EnterpriseRuntimePages().then((m) => ({ default: m.BusinessObjectsPage })));
const RuntimeResolversPage = lazy(() => EnterpriseRuntimePages().then((m) => ({ default: m.ResolversPage })));
const TransformationLibraryPage = lazy(() => EnterpriseRuntimePages().then((m) => ({ default: m.TransformationLibraryPage })));
const BusinessRulesPage = lazy(() => EnterpriseRuntimePages().then((m) => ({ default: m.BusinessRulesPage })));
const TransformLibraryPage = lazy(() => import('./pages/TransformsPage').then((m) => ({ default: m.TransformsPage })));
const BusinessRuleSetsPage = lazy(() => import('./pages/BusinessRulesPage').then((m) => ({ default: m.BusinessRulesPage })));
const BusinessRuleDetailsPage = lazy(() => import('./pages/BusinessRuleDetailsPage').then((m) => ({ default: m.BusinessRuleDetailsPage })));
const BusinessObjectsPage = lazy(() => import('./pages/BusinessObjectsPage').then((m) => ({ default: m.BusinessObjectsPage })));
const ResolversPage = lazy(() => import('./pages/ResolversPage').then((m) => ({ default: m.ResolversPage })));
const ResolverDetailsPage = lazy(() => import('./pages/ResolverDetailsPage').then((m) => ({ default: m.ResolverDetailsPage })));
const ResolverCachePage = lazy(() => import('./pages/ResolverCachePage').then((m) => ({ default: m.ResolverCachePage })));
const WorkflowsPage = lazy(() => import('./pages/WorkflowsPage').then((m) => ({ default: m.WorkflowsPage })));
const PipelineEditorPage = lazy(() => import('./pages/PipelineEditorPage').then((m) => ({ default: m.PipelineEditorPage })));
const MappingEditorPage = lazy(() => import('./pages/MappingEditorPage').then((m) => ({ default: m.MappingEditorPage })));
const PollingJobsPage = lazy(() => import('./pages/PollingJobsPage').then((m) => ({ default: m.PollingJobsPage })));
const PrintingPage = lazy(() => import('./pages/PrintingPage').then((m) => ({ default: m.PrintingPage })));
const OneCScenariosPage = lazy(() => import('./pages/OneCScenariosPage').then((m) => ({ default: m.OneCScenariosPage })));
const OneCWorkbenchPage = lazy(() => import('./pages/OneCWorkbenchPage').then((m) => ({ default: m.OneCWorkbenchPage })));
const NotificationRulesPage = lazy(() => import('./pages/NotificationRulesPage').then((m) => ({ default: m.NotificationRulesPage })));
const MaintenancePage = lazy(() => import('./pages/MaintenancePage').then((m) => ({ default: m.MaintenancePage })));
const RetentionPage = lazy(() => import('./pages/RetentionPage').then((m) => ({ default: m.RetentionPage })));
const OneCCockpitPage = lazy(() => import('./features/cockpit/OneCCockpitPage').then((m) => ({ default: m.OneCCockpitPage })));
const OneCCockpitWizardPage = lazy(() => import('./features/cockpit/OneCCockpitWizardPage').then((m) => ({ default: m.OneCCockpitWizardPage })));
const UsersPage = lazy(() => import('./features/auth/UsersPage').then((m) => ({ default: m.UsersPage })));
const ChangePasswordPage = lazy(() => import('./features/auth/ChangePasswordPage').then((m) => ({ default: m.ChangePasswordPage })));
const AuthSettingsPage = lazy(() => import('./features/auth/AuthSettingsPage').then((m) => ({ default: m.AuthSettingsPage })));
const ProductionPage = lazy(() => import('./pages/ProductionPage').then((m) => ({ default: m.ProductionPage })));
const AuditLogPage = lazy(() => import('./pages/AuditLogPage').then((m) => ({ default: m.AuditLogPage })));
const DocumentationPage = lazy(() => import('./pages/DocumentationPage').then((m) => ({ default: m.DocumentationPage })));
const OnboardingPage = lazy(() => import('./pages/OnboardingPage').then((m) => ({ default: m.OnboardingPage })));
const FirstIntegrationWizardPage = lazy(() => import('./pages/FirstIntegrationWizardPage').then((m) => ({ default: m.FirstIntegrationWizardPage })));
const ConfigHistoryPage = lazy(() => import('./pages/ConfigHistoryPage').then((m) => ({ default: m.ConfigHistoryPage })));
const EnvironmentsPage = lazy(() => import('./pages/EnvironmentsPage').then((m) => ({ default: m.EnvironmentsPage })));
const ChangeSetsPage = lazy(() => import('./pages/ChangeSetsPage').then((m) => ({ default: m.ChangeSetsPage })));
const ChangeSetDetailsPage = lazy(() => import('./pages/ChangeSetDetailsPage').then((m) => ({ default: m.ChangeSetDetailsPage })));
const ChangeSetImportPage = lazy(() => import('./pages/ChangeSetImportPage').then((m) => ({ default: m.ChangeSetImportPage })));
const I18nDebugPage = lazy(() => import('./pages/I18nDebugPage').then((m) => ({ default: m.I18nDebugPage })));

function onec(element: React.ReactNode) {
  return <PackageGate packageId="omh-package-onec">{element}</PackageGate>;
}

function printer(element: React.ReactNode) {
  return <PackageGate packageId="omh-package-printer">{element}</PackageGate>;
}

export function App() {
  return (
    <Suspense fallback={<PageLoading />}>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="docs" element={<DocumentationPage />} />
          <Route path="docs/search" element={<DocumentationPage />} />
          <Route path="docs/:packageId" element={<DocumentationPage />} />
          <Route path="docs/:packageId/:sectionId" element={<DocumentationPage />} />
          <Route path="docs/:packageId/:sectionId/:pageId" element={<DocumentationPage />} />
          <Route path="onboarding" element={<OnboardingPage />} />
          <Route path="onboarding/first-integration" element={<FirstIntegrationWizardPage />} />
          <Route path="events" element={<EventJournalPage />} />
          <Route path="events/:eventId" element={<EventTimelinePage />} />
          <Route path="incidents" element={<IncidentsPage />} />
          <Route path="incidents/:incidentId" element={<IncidentDetailsPage />} />
          <Route path="health" element={<HealthPage />} />
          <Route path="connectors" element={<ConnectorsPage />} />
          <Route path="secrets" element={<SecretsPage />} />
          <Route path="packages" element={<PackagesPage />} />
          <Route path="packages/:packageId" element={<PackageDetailsPage />} />
          <Route path="plugin-store" element={<PluginStorePage />} />
          <Route path="onec-cockpit" element={onec(<OneCCockpitPage />)} />
          <Route path="onec-cockpit/new" element={onec(<OneCCockpitWizardPage />)} />
          <Route path="integration-bus" element={<IntegrationBusPage />} />
          <Route path="integration-flows" element={<IntegrationFlowsPage />} />
          <Route path="operation-keys" element={<OperationKeysPage />} />
          <Route path="integration-flows/:flowId/builder" element={<VisualFlowBuilderPage />} />
          <Route path="integration-designer" element={onec(<IntegrationDesignerPage />)} />
          <Route path="scenario-library" element={<ScenarioLibraryPage />} />
          <Route path="odata-connections" element={onec(<ODataConnectionsPage />)} />
          <Route path="odata-explorer" element={onec(<ODataExplorerPage />)} />
          <Route path="xml-tools" element={onec(<XmlToolsPage />)} />
          <Route path="test-console" element={<TestConsolePage />} />
          <Route path="training" element={<TrainingPage />} />
          <Route path="test-cases" element={<SavedTestCasesPage />} />
          <Route path="onec-quick-setup" element={onec(<OneCQuickSetupPage />)} />
          <Route path="execution/steps" element={<ExecutionStepsPage />} />
          <Route path="runtime/queue" element={<IntegrationQueuePage />} />
          <Route path="runtime/queue/:queueId" element={<QueueItemDetailsPage />} />
          <Route path="runtime/dlq" element={<DeadLetterQueuePage />} />
          <Route path="runtime/monitor" element={<TransactionMonitorPage />} />
          <Route path="transaction-monitor" element={<TransactionMonitorPage />} />
          <Route path="runtime/business-objects" element={<RuntimeBusinessObjectsPage />} />
          <Route path="runtime/resolvers" element={<RuntimeResolversPage />} />
          <Route path="business-objects" element={<BusinessObjectsPage />} />
          <Route path="resolvers" element={<ResolversPage />} />
          <Route path="resolvers/cache" element={<ResolverCachePage />} />
          <Route path="resolvers/:id" element={<ResolverDetailsPage />} />
          <Route path="runtime/transforms" element={<TransformationLibraryPage />} />
          <Route path="runtime/business-rules" element={<BusinessRulesPage />} />
          <Route path="transforms" element={<TransformLibraryPage />} />
          <Route path="business-rules" element={<BusinessRuleSetsPage />} />
          <Route path="business-rules/:id" element={<BusinessRuleDetailsPage />} />
          <Route path="workflows" element={<WorkflowsPage />} />
          <Route path="pipelines/:workflowId/edit" element={<PipelineEditorPage />} />
          <Route path="mappings" element={<MappingEditorPage />} />
          <Route path="polling" element={<PollingJobsPage />} />
          <Route path="printing" element={printer(<PrintingPage />)} />
          <Route path="onec-scenarios" element={onec(<OneCScenariosPage />)} />
          <Route path="onec-workbench" element={onec(<OneCWorkbenchPage />)} />
          <Route path="notifications" element={<NotificationRulesPage />} />
          <Route path="maintenance" element={<MaintenancePage />} />
          <Route path="retention" element={<RetentionPage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="change-password" element={<ChangePasswordPage />} />
          <Route path="auth-settings" element={<AuthSettingsPage />} />
          <Route path="production" element={<ProductionPage />} />
          <Route path="audit" element={<AuditLogPage />} />
          <Route path="config-history/:objectType/:objectId" element={<ConfigHistoryPage />} />
          <Route path="environments" element={<EnvironmentsPage />} />
          <Route path="change-sets" element={<ChangeSetsPage />} />
          <Route path="change-sets/import" element={<ChangeSetImportPage />} />
          <Route path="change-sets/:id" element={<ChangeSetDetailsPage />} />
          <Route path="i18n-debug" element={<I18nDebugPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Suspense>
  );
}

function PageLoading() {
  const t = useT();
  return <LoadingState label={t('common.loadingPage')} />;
}
