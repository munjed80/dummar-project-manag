import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import { Suspense, lazy } from 'react';
import { apiService } from '@/services/api';
import { useAuth } from '@/hooks/useAuth';
import type { UserRole } from '@/hooks/useAuth';
import { InstallPrompt } from '@/components/InstallPrompt';

// Lazy-loaded page components
const LoginPage = lazy(() => import('@/pages/LoginPage'));
const DashboardPage = lazy(() => import('@/pages/DashboardPage'));
const CitizenDashboardPage = lazy(() => import('@/pages/CitizenDashboardPage'));
const ComplaintsListPage = lazy(() => import('@/pages/ComplaintsListPage'));
const ComplaintDetailsPage = lazy(() => import('@/pages/ComplaintDetailsPage'));
const ComplaintSubmitPage = lazy(() => import('@/pages/ComplaintSubmitPage'));
const ComplaintTrackPage = lazy(() => import('@/pages/ComplaintTrackPage'));
const ComplaintsMapPage = lazy(() => import('@/pages/ComplaintsMapPage'));
const TasksListPage = lazy(() => import('@/pages/TasksListPage'));
const TaskDetailsPage = lazy(() => import('@/pages/TaskDetailsPage'));
const ContractsListPage = lazy(() => import('@/pages/ContractsListPage'));
const ContractDetailsPage = lazy(() => import('@/pages/ContractDetailsPage'));
const ContractIntelligencePage = lazy(() => import('@/pages/ContractIntelligencePage'));
const ProcessingQueuePage = lazy(() => import('@/pages/ProcessingQueuePage'));
const DocumentReviewPage = lazy(() => import('@/pages/DocumentReviewPage'));
const BulkImportPage = lazy(() => import('@/pages/BulkImportPage'));
const RiskInsightsPage = lazy(() => import('@/pages/RiskInsightsPage'));
const DuplicateReviewPage = lazy(() => import('@/pages/DuplicateReviewPage'));
const IntelligenceReportsPage = lazy(() => import('@/pages/IntelligenceReportsPage'));
const LocationsListPage = lazy(() => import('@/pages/LocationsListPage'));
const UsersPage = lazy(() => import('@/pages/UsersPage'));
const ReportsPage = lazy(() => import('@/pages/ReportsPage'));
const SettingsPage = lazy(() => import('@/pages/SettingsPage'));

function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
    </div>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!apiService.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function RoleProtectedRoute({ children, roles }: { children: React.ReactNode; roles: UserRole[] }) {
  const { role, loading } = useAuth();

  if (!apiService.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  if (loading) return null;

  if (role && roles.includes(role)) {
    return <>{children}</>;
  }

  // Citizen users go to their own dashboard; others go to main dashboard
  if (role === 'citizen') {
    return <Navigate to="/citizen" replace />;
  }

  return <Navigate to="/dashboard" replace />;
}

// Internal staff roles (all roles except citizen)
const INTERNAL_ROLES: UserRole[] = [
  'project_director', 'contracts_manager', 'engineer_supervisor',
  'complaints_officer', 'area_supervisor', 'field_team', 'contractor_user',
];

// Roles that can view reports
const REPORT_ROLES: UserRole[] = [
  'project_director', 'contracts_manager', 'engineer_supervisor',
  'complaints_officer', 'area_supervisor',
];

// Roles that can access contract intelligence
const CONTRACT_INTELLIGENCE_ROLES: UserRole[] = [
  'project_director', 'contracts_manager',
];

function App() {
  return (
    <BrowserRouter>
      <Toaster />
      <InstallPrompt />
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/complaints/new" element={<ComplaintSubmitPage />} />
          <Route path="/complaints/track" element={<ComplaintTrackPage />} />
          
          <Route path="/" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><DashboardPage /></RoleProtectedRoute>} />
          <Route path="/dashboard" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><DashboardPage /></RoleProtectedRoute>} />
          <Route path="/citizen" element={<RoleProtectedRoute roles={['citizen']}><CitizenDashboardPage /></RoleProtectedRoute>} />
          <Route path="/complaints" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><ComplaintsListPage /></RoleProtectedRoute>} />
          <Route path="/complaints/:id" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><ComplaintDetailsPage /></RoleProtectedRoute>} />
          <Route path="/complaints-map" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><ComplaintsMapPage /></RoleProtectedRoute>} />
          <Route path="/tasks" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><TasksListPage /></RoleProtectedRoute>} />
          <Route path="/tasks/:id" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><TaskDetailsPage /></RoleProtectedRoute>} />
          <Route path="/contracts" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><ContractsListPage /></RoleProtectedRoute>} />
          <Route path="/contracts/:id" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><ContractDetailsPage /></RoleProtectedRoute>} />
          <Route path="/contract-intelligence" element={<RoleProtectedRoute roles={CONTRACT_INTELLIGENCE_ROLES}><ContractIntelligencePage /></RoleProtectedRoute>} />
          <Route path="/contract-intelligence/queue" element={<RoleProtectedRoute roles={CONTRACT_INTELLIGENCE_ROLES}><ProcessingQueuePage /></RoleProtectedRoute>} />
          <Route path="/contract-intelligence/documents/:id" element={<RoleProtectedRoute roles={CONTRACT_INTELLIGENCE_ROLES}><DocumentReviewPage /></RoleProtectedRoute>} />
          <Route path="/contract-intelligence/bulk-import" element={<RoleProtectedRoute roles={CONTRACT_INTELLIGENCE_ROLES}><BulkImportPage /></RoleProtectedRoute>} />
          <Route path="/contract-intelligence/risks" element={<RoleProtectedRoute roles={CONTRACT_INTELLIGENCE_ROLES}><RiskInsightsPage /></RoleProtectedRoute>} />
          <Route path="/contract-intelligence/duplicates" element={<RoleProtectedRoute roles={CONTRACT_INTELLIGENCE_ROLES}><DuplicateReviewPage /></RoleProtectedRoute>} />
          <Route path="/contract-intelligence/reports" element={<RoleProtectedRoute roles={CONTRACT_INTELLIGENCE_ROLES}><IntelligenceReportsPage /></RoleProtectedRoute>} />
          <Route path="/locations" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><LocationsListPage /></RoleProtectedRoute>} />
          <Route path="/users" element={<RoleProtectedRoute roles={['project_director']}><UsersPage /></RoleProtectedRoute>} />
          <Route path="/reports" element={<RoleProtectedRoute roles={REPORT_ROLES}><ReportsPage /></RoleProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;