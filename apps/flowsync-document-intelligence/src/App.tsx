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
import { WorkflowStudioPage } from "./pages/WorkflowStudioPage";
import { WorkflowDetailPage } from "./pages/WorkflowDetailPage";
import { WorkflowEditorPage } from "./pages/WorkflowEditorPage";
import { UploadsPage } from "./pages/UploadsPage";
import { RequireAuth } from "./auth/RequireAuth";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<RequireAuth />}>
          <Route element={<AppShell />}>
          <Route index element={<Navigate to="/documents" replace />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="uploads" element={<UploadsPage />} />
          <Route path="documents/:documentId" element={<DocumentDetailPage />} />
          <Route path="documents/:documentId/validation" element={<DocumentValidationPage />} />
          <Route path="documents/:documentId/matching" element={<DocumentMatchingPage />} />
          <Route path="review" element={<ReviewCasesPage />} />
          <Route path="review/:reviewCaseId" element={<ReviewCaseDetailPage />} />
          <Route path="workflows" element={<WorkflowStudioPage />} />
          <Route path="workflows/new" element={<WorkflowStudioPage />} />
          <Route path="workflows/:workflowId" element={<WorkflowDetailPage />} />
          <Route path="workflows/:workflowId/versions/:versionId/edit" element={<WorkflowEditorPage />} />
          <Route path="workflow-runs" element={<WorkflowsPage />} />
          <Route path="audit" element={<AuditPage />} />
          <Route path="settings/runtime-preview" element={<RuntimePreviewPage />} />
          <Route path="unauthorized" element={<UnauthorizedPage />} />
          <Route path="unavailable" element={<UnavailablePage />} />
          <Route path="*" element={<Navigate to="/documents" replace />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
