import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Navbar } from './components/layout/Navbar';
import { LoginPage } from './pages/LoginPage';
import { CatalogPage } from './pages/CatalogPage';
import { KnowledgePage } from './pages/KnowledgePage';
import { TestChatPage } from './pages/TestChatPage';
import { SettingsPage } from './pages/SettingsPage';
import { InboxPage } from './pages/InboxPage';
import { OrdersPage } from './pages/OrdersPage';
import { CommentsPage } from './pages/CommentsPage';
import { WhatsAppPage } from './pages/WhatsAppPage';
import { PostsPage } from './pages/PostsPage';
import { BroadcastPage } from './pages/BroadcastPage';
import { DashboardPage } from './pages/DashboardPage';
import { AIReviewPage } from './pages/AIReviewPage';
import { PrivacyPolicyPage } from './pages/PrivacyPolicyPage';

const ProtectedLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Single-Owner Private Direct Access (No login screen friction)
  if (!localStorage.getItem('replybd_token')) {
    localStorage.setItem('replybd_token', 'sellerbhai_owner_direct_token');
    localStorage.setItem('replybd_user', JSON.stringify({ email: 'owner@sellerbhai.com', name: 'Store Owner' }));
  }
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar />
      <main className="flex-1">{children}</main>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Navigate to="/dashboard" replace />} />
        <Route path="/privacy" element={<PrivacyPolicyPage />} />
        
        <Route
          path="/dashboard"
          element={
            <ProtectedLayout>
              <DashboardPage />
            </ProtectedLayout>
          }
        />
        <Route
          path="/"
          element={
            <ProtectedLayout>
              <CatalogPage />
            </ProtectedLayout>
          }
        />
        <Route
          path="/orders"
          element={
            <ProtectedLayout>
              <OrdersPage />
            </ProtectedLayout>
          }
        />
        <Route
          path="/knowledge"
          element={
            <ProtectedLayout>
              <KnowledgePage />
            </ProtectedLayout>
          }
        />
        <Route
          path="/inbox"
          element={
            <ProtectedLayout>
              <InboxPage />
            </ProtectedLayout>
          }
        />
        <Route
          path="/comments"
          element={
            <ProtectedLayout>
              <CommentsPage />
            </ProtectedLayout>
          }
        />
        <Route
          path="/whatsapp"
          element={
            <ProtectedLayout>
              <WhatsAppPage />
            </ProtectedLayout>
          }
        />
        <Route
          path="/posts"
          element={
            <ProtectedLayout>
              <PostsPage />
            </ProtectedLayout>
          }
        />
        <Route
          path="/broadcasts"
          element={
            <ProtectedLayout>
              <BroadcastPage />
            </ProtectedLayout>
          }
        />
        <Route
          path="/test-chat"
          element={
            <ProtectedLayout>
              <TestChatPage />
            </ProtectedLayout>
          }
        />
        <Route
          path="/ai-review"
          element={
            <ProtectedLayout>
              <AIReviewPage />
            </ProtectedLayout>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedLayout>
              <SettingsPage />
            </ProtectedLayout>
          }
        />
        
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
