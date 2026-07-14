import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./app/AppShell";
import { AuditPage } from "./pages/AuditPage";
import { DocumentDetailPage } from "./pages/DocumentDetailPage";
import { DocumentMatchingPage } from "./pages/DocumentMatchingPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { DocumentValidationPage } from "./pages/DocumentValidationPage";
import { ReviewCaseDetailPage } from "./pages/ReviewCaseDetailPage";
import { ReviewCasesPage } from "./pages/ReviewCasesPage";
import { RuntimePreviewPage } from "./pages/RuntimePreviewPage";
import { UnauthorizedPage } from "./pages/UnauthorizedPage";
import { UnavailablePage } from "./pages/UnavailablePage";
import { WorkflowsPage } from "./pages/WorkflowsPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/documents" replace />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="documents/:documentId" element={<DocumentDetailPage />} />
          <Route path="documents/:documentId/validation" element={<DocumentValidationPage />} />
          <Route path="documents/:documentId/matching" element={<DocumentMatchingPage />} />
          <Route path="review" element={<ReviewCasesPage />} />
          <Route path="review/:reviewCaseId" element={<ReviewCaseDetailPage />} />
          <Route path="workflows" element={<WorkflowsPage />} />
          <Route path="audit" element={<AuditPage />} />
          <Route path="settings/runtime-preview" element={<RuntimePreviewPage />} />
          <Route path="unauthorized" element={<UnauthorizedPage />} />
          <Route path="unavailable" element={<UnavailablePage />} />
          <Route path="*" element={<Navigate to="/documents" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

