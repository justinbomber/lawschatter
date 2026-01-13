import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// 本地開發配置
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
    open: true,
    proxy: {
      // 代理 Supabase Auth API 到線上服務
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
      // 代理 Supabase REST API 到線上服務
      '/supabase-rest': {
        target: 'https://supalaw.mooo.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/supabase-rest/, '/rest/v1'),
        secure: false
      },
      // 代理 RAG API 到本地服務
      '/chat': {
        target: 'http://127.0.0.1:9500',
        changeOrigin: true
      },
      // 代理其他 RAG 路徑
      '/rag': {
        target: 'http://127.0.0.1:9500',
        changeOrigin: true
      },
      '/search': {
        target: 'http://127.0.0.1:9500',
        changeOrigin: true
      }
    }
  },
  define: {
    'import.meta.env.VITE_API_BASE_URL': JSON.stringify('http://localhost:8090'),
    'import.meta.env.VITE_CHAT_API_URL': JSON.stringify('http://127.0.0.1:9500'),
    'import.meta.env.VITE_MODE': JSON.stringify('local'),
    'import.meta.env.VITE_SUPABASE_ANON_KEY': JSON.stringify('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyAgCiAgICAicm9sZSI6ICJhbm9uIiwKICAgICJpc3MiOiAic3VwYWJhc2UtZGVtbyIsCiAgICAiaWF0IjogMTY0MTc2OTIwMCwKICAgICJleHAiOiAxNzk5NTM1NjAwCn0.dc_X5iR_VP_qT0zsiyj_I_OZ2T9FtRU2BBNWN8Bu4GE'),
  },
  build: {
    outDir: 'build',
  },
});

