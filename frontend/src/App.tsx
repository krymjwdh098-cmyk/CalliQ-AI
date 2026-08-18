import { Routes, Route, Navigate } from 'react-router-dom';
import { ProtectedRoute } from './components/ProtectedRoute';

import { LoginPage, ForgotPasswordPage } from './pages/Login';
import { RegisterPage } from './pages/Register';
import { ResetPasswordPage } from './pages/ResetPassword';
import { DashboardPage } from './pages/Dashboard';
import { JobsPage } from './pages/Jobs';
import { CandidatesPage } from './pages/Candidates';
import { CandidateDetailPage } from './pages/CandidateDetail';
import { ApplyPage } from './pages/Apply';
import { SettingsPage } from './pages/Settings';
import { ReportsPage } from './pages/Reports';
import { NotFoundPage } from './pages/NotFound';

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/apply/:token" element={<ApplyPage />} />

      {/* Protected */}
      <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/jobs" element={<ProtectedRoute><JobsPage /></ProtectedRoute>} />
      <Route path="/candidates" element={<ProtectedRoute><CandidatesPage /></ProtectedRoute>} />
      <Route path="/candidates/:id" element={<ProtectedRoute><CandidateDetailPage /></ProtectedRoute>} />
      <Route path="/reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />

      {/* Redirects */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
