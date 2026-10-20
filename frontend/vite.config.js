import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {fileURLToPath} from 'node:url';
export default defineConfig({
  root:fileURLToPath(new URL('.',import.meta.url)),plugins:[react()],
  build:{outDir:'../public',emptyOutDir:false,chunkSizeWarningLimit:1200},
  server:{port:5173,proxy:{'/api':'http://127.0.0.1:4173','/docs':'http://127.0.0.1:4173'}}
});
