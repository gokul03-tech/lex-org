import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';
import Layout from '@/components/layout/Layout';
import DashboardPage from '@/pages/DashboardPage';
import CasesPage from '@/pages/CasesPage';
import CaseWorkspaceLayout from '@/pages/case/CaseWorkspaceLayout';
import OverviewPage from '@/pages/case/OverviewPage';
import StatutesPage from '@/pages/case/StatutesPage';
import EvidencePage from '@/pages/case/EvidencePage';
import GraphPage from '@/pages/case/GraphPage';
import RiskPage from '@/pages/case/RiskPage';
import ReportPage from '@/pages/ReportPage';
import LoginPage from '@/pages/LoginPage';
import RegisterPage from '@/pages/RegisterPage';
import AdminPage from '@/pages/AdminPage';
import NotFoundPage from '@/pages/NotFoundPage';

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/cases" element={<CasesPage />} />

          {/* Separate-page case workspace */}
          <Route path="/cases/:caseId" element={<CaseWorkspaceLayout />}>
            <Route index element={<OverviewPage />} />
            <Route path="statutes" element={<StatutesPage />} />
            <Route path="evidence" element={<EvidencePage />} />
            <Route path="graph" element={<GraphPage />} />
            <Route path="risk" element={<RiskPage />} />
          </Route>

          <Route path="/cases/:caseId/report" element={<ReportPage />} />
          <Route path="/admin" element={<AdminPage />} />
        </Route>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
      <Toaster />
    </>
  );
}
