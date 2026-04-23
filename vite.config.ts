import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react-swc";
import { defineConfig } from "vite";
import { resolve } from 'path'

const projectRoot = process.env.PROJECT_ROOT || import.meta.dirname

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': resolve(projectRoot, 'src')
    }
  },
  server: {
    proxy: {
      // API calls: frontend uses VITE_API_BASE_URL=/api (same-origin). In dev
      // we proxy it to the backend and strip the /api prefix to match the
      // FastAPI routes (which are mounted at the root, not /api).
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      // Uploads: the backend returns root-relative paths like
      // "/uploads/contracts/foo.pdf". Proxy them verbatim so dev file links
      // work the same way they do in production (nginx serves public uploads
      // and proxies sensitive categories to the backend).
      '/uploads': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
