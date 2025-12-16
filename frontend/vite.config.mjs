import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    allowedHosts: [
      'lawschatter.mooo.com',
      'localhost',
      '127.0.0.1'
    ],
    open: false,
    proxy: {
      // 代理 Supabase Auth API 請求
      '/supabase-auth': {
        target: 'https://supalaw.mooo.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/supabase-auth/, '/auth/v1'),
        secure: false,
        configure: (proxy, options) => {
          proxy.on('error', (err, req, res) => {
            console.log('代理錯誤:', err);
          });
          proxy.on('proxyReq', (proxyReq, req, res) => {
            console.log('代理請求:', req.method, req.url);
          });
          proxy.on('proxyRes', (proxyRes, req, res) => {
            console.log('代理回應:', proxyRes.statusCode, req.url);
          });
        }
      },
      // 代理 Supabase REST API 請求
      '/supabase-rest': {
        target: 'https://supalaw.mooo.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/supabase-rest/, '/rest/v1'),
        secure: false
      }
    }
  },
  build: {
    outDir: 'build',
  },
});

