import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ConnectorsPage } from './pages/ConnectorsPage';
import { DashboardPage } from './pages/DashboardPage';
import { EventJournalPage } from './pages/EventJournalPage';
import { EventTimelinePage } from './pages/EventTimelinePage';
import { ExecutionStepsPage } from './pages/ExecutionStepsPage';
import {
  BusinessObjectsPage,
  BusinessRulesPage,
  DeadLetterQueuePage,
  IntegrationQueuePage,
  ResolversPage,
  TransactionMonitorPage,
  TransformationLibraryPage,
} from './pages/EnterpriseRuntimePages';
import { HealthPage } from './pages/HealthPage';
import { IncidentDetailsPage } from './pages/IncidentDetailsPage';
import { IncidentsPage } from './pages/IncidentsPage';
import { IntegrationBusPage } from './pages/IntegrationBusPage';
import { IntegrationDesignerPage } from './pages/IntegrationDesignerPage';
import { IntegrationFlowsPage } from './pages/IntegrationFlowsPage';
import { MaintenancePage } from './pages/MaintenancePage';
import { MappingEditorPage } from './pages/MappingEditorPage';
import { NotificationRulesPage } from './pages/NotificationRulesPage';
import { ODataExplorerPage } from './pages/ODataExplorerPage';
import { PackageDetailsPage } from './pages/PackageDetailsPage';
import { PackagesPage } from './pages/PackagesPage';
import { OneCScenariosPage } from './pages/OneCScenariosPage';
import { OneCWorkbenchPage } from './pages/OneCWorkbenchPage';
import { OneCQuickSetupPage } from './pages/OneCQuickSetupPage';
import { PipelineEditorPage } from './pages/PipelineEditorPage';
import { PluginStorePage } from './pages/PluginStorePage';
import { PollingJobsPage } from './pages/PollingJobsPage';
import { PrintingPage } from './pages/PrintingPage';
import { RetentionPage } from './pages/RetentionPage';
import { SavedTestCasesPage } from './pages/SavedTestCasesPage';
import { ScenarioLibraryPage } from './pages/ScenarioLibraryPage';
import { TestConsolePage } from './pages/TestConsolePage';
import { WorkflowsPage } from './pages/WorkflowsPage';
import { XmlToolsPage } from './pages/XmlToolsPage';
import { VisualFlowBuilderPage } from './pages/VisualFlowBuilderPage';

export function App() {
  return (
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
        <Route path="integration-bus" element={<IntegrationBusPage />} />
        <Route path="integration-flows" element={<IntegrationFlowsPage />} />
        <Route path="integration-flows/:flowId/builder" element={<VisualFlowBuilderPage />} />
        <Route path="integration-designer" element={<IntegrationDesignerPage />} />
        <Route path="scenario-library" element={<ScenarioLibraryPage />} />
        <Route path="odata-explorer" element={<ODataExplorerPage />} />
        <Route path="xml-tools" element={<XmlToolsPage />} />
        <Route path="test-console" element={<TestConsolePage />} />
        <Route path="test-cases" element={<SavedTestCasesPage />} />
        <Route path="onec-quick-setup" element={<OneCQuickSetupPage />} />
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
        <Route path="printing" element={<PrintingPage />} />
        <Route path="onec-scenarios" element={<OneCScenariosPage />} />
        <Route path="onec-workbench" element={<OneCWorkbenchPage />} />
        <Route path="notifications" element={<NotificationRulesPage />} />
        <Route path="maintenance" element={<MaintenancePage />} />
        <Route path="retention" element={<RetentionPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
