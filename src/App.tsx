import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import ComplaintsListPage from '@/pages/ComplaintsListPage';
import ComplaintDetailsPage from '@/pages/ComplaintDetailsPage';
import ComplaintSubmitPage from '@/pages/ComplaintSubmitPage';
import ComplaintTrackPage from '@/pages/ComplaintTrackPage';
import TasksListPage from '@/pages/TasksListPage';
import TaskDetailsPage from '@/pages/TaskDetailsPage';
import ContractsListPage from '@/pages/ContractsListPage';
import ContractDetailsPage from '@/pages/ContractDetailsPage';
import { apiService } from '@/services/api';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!apiService.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function App() {
  return (
    <BrowserRouter>
      <Toaster />
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
      </Routes>
    </BrowserRouter>
  );
}

export default App;