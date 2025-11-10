import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import Login from '../components/Login.jsx';
import Register from '../components/Register.jsx';
import ChatRoute from './ChatRoute.jsx';
import ShareRoute from './ShareRoute.jsx';

function AppRouter() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="app loading-screen">
        <div className="loading-spinner"></div>
        <p>載入中...</p>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/share/:shareId" element={<ShareRoute />} />
        
        {!isAuthenticated ? (
          <>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </>
        ) : (
          <>
            <Route path="/c/new" element={<ChatRoute />} />
            <Route path="/c/:conversationId" element={<ChatRoute />} />
            <Route path="/" element={<Navigate to="/c/new" replace />} />
            <Route path="*" element={<Navigate to="/c/new" replace />} />
          </>
        )}
      </Routes>
    </BrowserRouter>
  );
}

export default AppRouter;

