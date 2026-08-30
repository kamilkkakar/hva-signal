/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_HVA_PUBLIC_CONTEXT?: string;
  readonly VITE_HVA_JUDGE_SHELL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
