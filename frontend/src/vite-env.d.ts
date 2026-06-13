/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly PROD: boolean
  // 다른 환경 변수들...
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}





