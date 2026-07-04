import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { LoadingState } from './components/LoadingState';
import { PackageGate } from './components/product/PackageGate';

const DashboardPage = lazy(() => import('./pages/DashboardPage').then((m) => ({ default: m.DashboardPage })));
const EventJournalPage = lazy(() => import('./pages/EventJournalPage').then((m) => ({ default: m.EventJournalPage })));
const EventTimelinePage = lazy(() => import('./pages/EventTimelinePage').then((m) => ({ default: m.EventTimelinePage })));
const IncidentsPage = lazy(() => import('./pages/IncidentsPage').then((m) => ({ default: m.IncidentsPage })));
const IncidentDetailsPage = lazy(() => import('./pages/IncidentDetailsPage').then((m) => ({ default: m.IncidentDetailsPage })));
const HealthPage = lazy(() => import('./pages/HealthPage').then((m) => ({ default: m.HealthPage })));
const ConnectorsPage = lazy(() => import('./pages/ConnectorsPage').then((m) => ({ default: m.ConnectorsPage })));
const PackagesPage = lazy(() => import('./pages/PackagesPage').then((m) => ({ default: m.PackagesPage })));
const PackageDetailsPage = lazy(() => import('./pages/PackageDetailsPage').then((m) => ({ default: m.PackageDetailsPage })));
const PluginStorePage = lazy(() => import('./pages/PluginStorePage').then((m) => ({ default: m.PluginStorePage })));
const IntegrationBusPage = lazy(() => import('./pages/IntegrationBusPage').then((m) => ({ default: m.IntegrationBusPage })));
const IntegrationFlowsPage = lazy(() => import('./pages/IntegrationFlowsPage').then((m) => ({ default: m.IntegrationFlowsPage })));
const VisualFlowBuilderPage = lazy(() => import('./pages/VisualFlowBuilderPage').then((m) => ({ default: m.VisualFlowBuilderPage })));
const IntegrationDesignerPage = lazy(() => import('./pages/IntegrationDesignerPage').then((m) => ({ default: m.IntegrationDesignerPage })));
const ScenarioLibraryPage = lazy(() => import('./pages/ScenarioLibraryPage').then((m) => ({ default: m.ScenarioLibraryPage })));
const ODataExplorerPage = lazy(() => import('./pages/ODataExplorerPage').then((m) => ({ default: m.ODataExplorerPage })));
const XmlToolsPage = lazy(() => import('./pages/XmlToolsPage').then((m) => ({ default: m.XmlToolsPage })));
const TestConsolePage = lazy(() => import('./pages/TestConsolePage').then((m) => ({ default: m.TestConsolePage })));
const SavedTestCasesPage = lazy(() => import('./pages/SavedTestCasesPage').then((m) => ({ default: m.SavedTestCasesPage })));
const OneCQuickSetupPage = lazy(() => import('./pages/OneCQuickSetupPage').then((m) => ({ default: m.OneCQuickSetupPage })));
const ExecutionStepsPage = lazy(() => import('./pages/ExecutionStepsPage').then((m) => ({ default: m.ExecutionStepsPage })));
const EnterpriseRuntimePages = () => import('./pages/EnterpriseRuntimePages');
const IntegrationQueuePage = lazy(() => EnterpriseRuntimePages().then((m) => ({ default: m.IntegrationQueuePage })));
const DeadLetterQueuePage = lazy(() => EnterpriseRuntimePages().then((m) => ({ default: m.DeadLetterQueuePage })));
const TransactionMonitorPage = lazy(() => EnterpriseRuntimePages().then((m) => ({ default: m.TransactionMonitorPage })));
const BusinessObjectsPage = lazy(() => EnterpriseRuntimePages().then((m) => ({ default: m.BusinessObjectsPage })));
const ResolversPage = lazy(() => EnterpriseRuntimePages().then((m) => ({ default: m.ResolversPage })));
const TransformationLibraryPage = lazy(() => EnterpriseRuntimePages().then((m) => ({ default: m.TransformationLibraryPage })));
const BusinessRulesPage = lazy(() => EnterpriseRuntimePages().then((m) => ({ default: m.BusinessRulesPage })));
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

function onec(element: React.ReactNode) {
  return <PackageGate packageId="omh-package-onec">{element}</PackageGate>;
}

function printer(element: React.ReactNode) {
  return <PackageGate packageId="omh-package-printer">{element}</PackageGate>;
}

export function App() {
  return (
    <Suspense fallback={<LoadingState label="Loading page" />}>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="events" element={<EventJournalPage />} />
          <Route path="events/:eventId" element={<EventTimelinePage />} />
          <Route path="incidents" element={<IncidentsPage />} />
          <Route path="incidents/:incidentId" element={<IncidentDetailsPage />} />
          <Route path="health" element={<HealthPage />} />
          <Route path="connectors" element={<ConnectorsPage />} />
          <Route path="packages" element={<PackagesPage />} />
          <Route path="packages/:packageId" element={<PackageDetailsPage />} />
          <Route path="plugin-store" element={<PluginStorePage />} />
          <Route path="onec-cockpit" element={onec(<OneCCockpitPage />)} />
          <Route path="onec-cockpit/new" element={onec(<OneCCockpitWizardPage />)} />
          <Route path="integration-bus" element={<IntegrationBusPage />} />
          <Route path="integration-flows" element={<IntegrationFlowsPage />} />
          <Route path="integration-flows/:flowId/builder" element={<VisualFlowBuilderPage />} />
          <Route path="integration-designer" element={onec(<IntegrationDesignerPage />)} />
          <Route path="scenario-library" element={<ScenarioLibraryPage />} />
          <Route path="odata-explorer" element={onec(<ODataExplorerPage />)} />
          <Route path="xml-tools" element={onec(<XmlToolsPage />)} />
          <Route path="test-console" element={<TestConsolePage />} />
          <Route path="test-cases" element={<SavedTestCasesPage />} />
          <Route path="onec-quick-setup" element={onec(<OneCQuickSetupPage />)} />
          <Route path="execution/steps" element={<ExecutionStepsPage />} />
          <Route path="runtime/queue" element={<IntegrationQueuePage />} />
          <Route path="runtime/dlq" element={<DeadLetterQueuePage />} />
          <Route path="runtime/monitor" element={<TransactionMonitorPage />} />
          <Route path="runtime/business-objects" element={<BusinessObjectsPage />} />
          <Route path="runtime/resolvers" element={<ResolversPage />} />
          <Route path="runtime/transforms" element={<TransformationLibraryPage />} />
          <Route path="runtime/business-rules" element={<BusinessRulesPage />} />
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
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
