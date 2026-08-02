import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';
import Layout from '@/components/layout/Layout';
import DashboardPage from '@/pages/DashboardPage';
import ChatPage from '@/pages/ChatPage';
import LegalResearchPage from '@/pages/LegalResearchPage';
import DocumentAnalysisPage from '@/pages/DocumentAnalysisPage';
import KnowledgeGraphPage from '@/pages/KnowledgeGraphPage';
import CasesPage from '@/pages/CasesPage';
import CaseDetailPage from '@/pages/CaseDetailPage';
import AnalysisPage from '@/pages/AnalysisPage';
import ReportPage from '@/pages/ReportPage';
import StatutesPage from '@/pages/StatutesPage';
import JudgmentsPage from '@/pages/JudgmentsPage';
import AnalyticsPage from '@/pages/AnalyticsPage';
import SettingsPage from '@/pages/SettingsPage';
import ProfilePage from '@/pages/ProfilePage';
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
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/research" element={<LegalResearchPage />} />
          <Route path="/document-analysis" element={<DocumentAnalysisPage />} />
          <Route path="/graph" element={<KnowledgeGraphPage />} />
          <Route path="/cases" element={<CasesPage />} />
          <Route path="/cases/:caseId" element={<CaseDetailPage />} />
          <Route path="/cases/:caseId/analysis" element={<AnalysisPage />} />
          <Route path="/cases/:caseId/report" element={<ReportPage />} />
          <Route path="/statutes" element={<StatutesPage />} />
          <Route path="/judgments" element={<JudgmentsPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/admin" element={<AdminPage />} />
        </Route>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
      <Toaster />
    </>
  );
}
