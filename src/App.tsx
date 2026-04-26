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
const LocationDetailPage = lazy(() => import('@/pages/LocationDetailPage'));
const LocationReportsPage = lazy(() => import('@/pages/LocationReportsPage'));
const GeoDashboardPage = lazy(() => import('@/pages/GeoDashboardPage'));
const ProjectsListPage = lazy(() => import('@/pages/ProjectsListPage'));
const ProjectDetailsPage = lazy(() => import('@/pages/ProjectDetailsPage'));
const TeamsListPage = lazy(() => import('@/pages/TeamsListPage'));
const TeamDetailsPage = lazy(() => import('@/pages/TeamDetailsPage'));
const UsersPage = lazy(() => import('@/pages/UsersPage'));
const ReportsPage = lazy(() => import('@/pages/ReportsPage'));
const SettingsPage = lazy(() => import('@/pages/SettingsPage'));
const ChangePasswordPage = lazy(() => import('@/pages/ChangePasswordPage'));
const PublicLandingPage = lazy(() => import('@/pages/PublicLandingPage'));

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
  if (
    localStorage.getItem('must_change_password') === '1' &&
    window.location.pathname !== '/change-password'
  ) {
    return <Navigate to="/change-password" replace />;
  }
  return <>{children}</>;
}

function RoleProtectedRoute({ children, roles }: { children: React.ReactNode; roles: UserRole[] }) {
  const { role, loading } = useAuth();

  if (!apiService.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  if (
    localStorage.getItem('must_change_password') === '1' &&
    window.location.pathname !== '/change-password'
  ) {
    return <Navigate to="/change-password" replace />;
  }

  if (loading) return <PageLoader />;

  if (role && roles.includes(role)) {
    return <>{children}</>;
  }

  // Citizen users go to their own dashboard; others go to main dashboard
  if (role === 'citizen') {
    return <Navigate to="/citizen" replace />;
  }

  return <Navigate to="/login" replace />;
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

function RootRoute() {
  // Unauthenticated visitors see the public landing page so the complaint
  // intake CTAs are the very first thing they see — not the staff login.
  if (!apiService.isAuthenticated()) {
    return <PublicLandingPage />;
  }
  // Authenticated users are routed to their role-appropriate home.
  return <RoleProtectedRoute roles={INTERNAL_ROLES}><DashboardPage /></RoleProtectedRoute>;
}

function App() {
  return (
    <BrowserRouter>
      <Toaster />
      <InstallPrompt />
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/change-password"
            element={
              apiService.isAuthenticated()
                ? <ChangePasswordPage />
                : <Navigate to="/login" replace />
            }
          />
          <Route path="/complaints/new" element={<ComplaintSubmitPage />} />
          <Route path="/complaints/track" element={<ComplaintTrackPage />} />
          
          <Route path="/" element={<RootRoute />} />
          <Route path="/dashboard" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><DashboardPage /></RoleProtectedRoute>} />
          <Route path="/citizen" element={<RoleProtectedRoute roles={['citizen']}><CitizenDashboardPage /></RoleProtectedRoute>} />
          <Route path="/complaints" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><ComplaintsListPage /></RoleProtectedRoute>} />
          <Route path="/complaints/:id" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><ComplaintDetailsPage /></RoleProtectedRoute>} />
          <Route path="/complaints-map" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><ComplaintsMapPage /></RoleProtectedRoute>} />
          <Route path="/tasks" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><TasksListPage /></RoleProtectedRoute>} />
          <Route path="/tasks/:id" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><TaskDetailsPage /></RoleProtectedRoute>} />
          <Route path="/contracts" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><ContractsListPage /></RoleProtectedRoute>} />
          <Route path="/contracts/:id" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><ContractDetailsPage /></RoleProtectedRoute>} />
          <Route path="/projects" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><ProjectsListPage /></RoleProtectedRoute>} />
          <Route path="/projects/:id" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><ProjectDetailsPage /></RoleProtectedRoute>} />
          <Route path="/teams" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><TeamsListPage /></RoleProtectedRoute>} />
          <Route path="/teams/:id" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><TeamDetailsPage /></RoleProtectedRoute>} />
          <Route path="/contract-intelligence" element={<RoleProtectedRoute roles={CONTRACT_INTELLIGENCE_ROLES}><ContractIntelligencePage /></RoleProtectedRoute>} />
          <Route path="/contract-intelligence/queue" element={<RoleProtectedRoute roles={CONTRACT_INTELLIGENCE_ROLES}><ProcessingQueuePage /></RoleProtectedRoute>} />
          <Route path="/contract-intelligence/documents/:id" element={<RoleProtectedRoute roles={CONTRACT_INTELLIGENCE_ROLES}><DocumentReviewPage /></RoleProtectedRoute>} />
          <Route path="/contract-intelligence/bulk-import" element={<RoleProtectedRoute roles={CONTRACT_INTELLIGENCE_ROLES}><BulkImportPage /></RoleProtectedRoute>} />
          <Route path="/contract-intelligence/risks" element={<RoleProtectedRoute roles={CONTRACT_INTELLIGENCE_ROLES}><RiskInsightsPage /></RoleProtectedRoute>} />
          <Route path="/contract-intelligence/duplicates" element={<RoleProtectedRoute roles={CONTRACT_INTELLIGENCE_ROLES}><DuplicateReviewPage /></RoleProtectedRoute>} />
          <Route path="/contract-intelligence/reports" element={<RoleProtectedRoute roles={CONTRACT_INTELLIGENCE_ROLES}><IntelligenceReportsPage /></RoleProtectedRoute>} />
          <Route path="/locations" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><LocationsListPage /></RoleProtectedRoute>} />
          <Route path="/locations/reports" element={<RoleProtectedRoute roles={REPORT_ROLES}><LocationReportsPage /></RoleProtectedRoute>} />
          <Route path="/locations/geo-dashboard" element={<RoleProtectedRoute roles={REPORT_ROLES}><GeoDashboardPage /></RoleProtectedRoute>} />
          <Route path="/locations/:id" element={<RoleProtectedRoute roles={INTERNAL_ROLES}><LocationDetailPage /></RoleProtectedRoute>} />
          <Route path="/users" element={<RoleProtectedRoute roles={['project_director']}><UsersPage /></RoleProtectedRoute>} />
          <Route path="/reports" element={<RoleProtectedRoute roles={REPORT_ROLES}><ReportsPage /></RoleProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;
