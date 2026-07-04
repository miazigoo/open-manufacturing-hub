import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ConnectorsPage } from './pages/ConnectorsPage';
import { DashboardPage } from './pages/DashboardPage';
import { EventJournalPage } from './pages/EventJournalPage';
import { EventTimelinePage } from './pages/EventTimelinePage';
import { ExecutionStepsPage } from './pages/ExecutionStepsPage';
import { HealthPage } from './pages/HealthPage';
import { IncidentDetailsPage } from './pages/IncidentDetailsPage';
import { IncidentsPage } from './pages/IncidentsPage';
import { MaintenancePage } from './pages/MaintenancePage';
import { MappingEditorPage } from './pages/MappingEditorPage';
import { NotificationRulesPage } from './pages/NotificationRulesPage';
import { OneCScenariosPage } from './pages/OneCScenariosPage';
import { OneCWorkbenchPage } from './pages/OneCWorkbenchPage';
import { PollingJobsPage } from './pages/PollingJobsPage';
import { PrintingPage } from './pages/PrintingPage';
import { RetentionPage } from './pages/RetentionPage';
import { WorkflowsPage } from './pages/WorkflowsPage';

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
        <Route path="execution/steps" element={<ExecutionStepsPage />} />
        <Route path="workflows" element={<WorkflowsPage />} />
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
