/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DOCUMENT_INTELLIGENCE_API_BASE_URL?: string;
  readonly VITE_SUPABASE_URL?: string;
  readonly VITE_SUPABASE_PUBLISHABLE_KEY?: string;
  readonly VITE_DEPLOYMENT_ENVIRONMENT?: string;
  readonly VITE_UAT_LABEL?: string;
  readonly VITE_WORKFLOW_STUDIO_PERMISSIONS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

