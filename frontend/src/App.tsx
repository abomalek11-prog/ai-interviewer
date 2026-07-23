import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AuthProvider } from "@/context/AuthContext";
import { ForgotPasswordPage } from "@/pages/auth/ForgotPasswordPage";
import { LoginPage } from "@/pages/auth/LoginPage";
import { OAuthCallbackPage } from "@/pages/auth/OAuthCallbackPage";
import { RegisterPage } from "@/pages/auth/RegisterPage";
import { AnalyticsPage } from "@/pages/AnalyticsPage";
import { CandidatesPage } from "@/pages/CandidatesPage";
import { CandidateReportPage } from "@/pages/CandidateReportPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { InterviewSessionPage } from "@/pages/InterviewSessionPage";
import { InterviewsPage } from "@/pages/InterviewsPage";
import { LiveInterviewPage } from "@/pages/LiveInterviewPage";
import { NewInterviewPage } from "@/pages/NewInterviewPage";
import { ProfilePage } from "@/pages/ProfilePage";

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/auth/callback" element={<OAuthCallbackPage />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/interviews" element={<InterviewsPage />} />
            <Route path="/interviews/new" element={<NewInterviewPage />} />
            <Route path="/interviews/session/:sessionId" element={<InterviewSessionPage />} />
            <Route path="/interviews/live/:sessionId" element={<LiveInterviewPage />} />
            <Route path="/candidates" element={<CandidatesPage />} />
            <Route path="/candidates/:candidateId/report" element={<CandidateReportPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/profile" element={<ProfilePage />} />
          </Route>
        </Route>

        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AuthProvider>
  );
}

export default App;
