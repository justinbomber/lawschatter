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
        target: 'https://jeceqvadobfarfmwkacw.supabase.co',
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
        target: 'https://jeceqvadobfarfmwkacw.supabase.co',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/supabase-rest/, '/rest/v1'),
        secure: false
      }
    }
  },
  define: {
    // 'import.meta.env.VITE_SUPABASE_ANON_KEY': JSON.stringify('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyAgCiAgICAicm9sZSI6ICJhbm9uIiwKICAgICJpc3MiOiAic3VwYWJhc2UtZGVtbyIsCiAgICAiaWF0IjogMTY0MTc2OTIwMCwKICAgICJleHAiOiAxNzk5NTM1NjAwCn0.dc_X5iR_VP_qT0zsiyj_I_OZ2T9FtRU2BBNWN8Bu4GE'),
    'import.meta.env.VITE_SUPABASE_ANON_KEY': JSON.stringify('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImplY2VxdmFkb2JmYXJmbXdrYWN3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjcxOTEzNTksImV4cCI6MjA4Mjc2NzM1OX0.oE8awZDtTqndOWPrGLG9Q2IybpR2smYrPsY5VgLXh1A'),
  },
  build: {
    outDir: 'build',
  },
});

