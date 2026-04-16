import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import { Suspense, lazy } from 'react';
import { apiService } from '@/services/api';
import { useAuth } from '@/hooks/useAuth';
import type { UserRole } from '@/hooks/useAuth';

// Lazy-loaded page components
const LoginPage = lazy(() => import('@/pages/LoginPage'));
const DashboardPage = lazy(() => import('@/pages/DashboardPage'));
const ComplaintsListPage = lazy(() => import('@/pages/ComplaintsListPage'));
const ComplaintDetailsPage = lazy(() => import('@/pages/ComplaintDetailsPage'));
const ComplaintSubmitPage = lazy(() => import('@/pages/ComplaintSubmitPage'));
const ComplaintTrackPage = lazy(() => import('@/pages/ComplaintTrackPage'));
const TasksListPage = lazy(() => import('@/pages/TasksListPage'));
const TaskDetailsPage = lazy(() => import('@/pages/TaskDetailsPage'));
const ContractsListPage = lazy(() => import('@/pages/ContractsListPage'));
const ContractDetailsPage = lazy(() => import('@/pages/ContractDetailsPage'));
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

  return <Navigate to="/dashboard" replace />;
}

function App() {
  return (
    <BrowserRouter>
      <Toaster />
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/complaints/new" element={<ComplaintSubmitPage />} />
          <Route path="/complaints/track" element={<ComplaintTrackPage />} />
          
          <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/complaints" element={<ProtectedRoute><ComplaintsListPage /></ProtectedRoute>} />
          <Route path="/complaints/:id" element={<ProtectedRoute><ComplaintDetailsPage /></ProtectedRoute>} />
          <Route path="/tasks" element={<ProtectedRoute><TasksListPage /></ProtectedRoute>} />
          <Route path="/tasks/:id" element={<ProtectedRoute><TaskDetailsPage /></ProtectedRoute>} />
          <Route path="/contracts" element={<ProtectedRoute><ContractsListPage /></ProtectedRoute>} />
          <Route path="/contracts/:id" element={<ProtectedRoute><ContractDetailsPage /></ProtectedRoute>} />
          <Route path="/locations" element={<ProtectedRoute><LocationsListPage /></ProtectedRoute>} />
          <Route path="/users" element={<RoleProtectedRoute roles={['project_director']}><UsersPage /></RoleProtectedRoute>} />
          <Route path="/reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;