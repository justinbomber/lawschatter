import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import './i18n';
import AppRouter from './routes/AppRouter.jsx';
import { AuthProvider } from './contexts/AuthContext.jsx';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <AuthProvider>
      <AppRouter />
    </AuthProvider>
  </React.StrictMode>
);
