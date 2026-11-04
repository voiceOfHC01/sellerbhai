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

// Single-Owner Private Direct Access (No login screen friction)
class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean; error: any }> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }
  componentDidCatch(error: any, info: any) {
    console.error("UI Error Caught:", error, info);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-900 text-white flex flex-col items-center justify-center p-6 text-center">
          <div className="w-12 h-12 rounded-xl bg-blue-600 flex items-center justify-center mb-4 text-xl font-bold">SB</div>
          <h2 className="text-xl font-bold mb-2">SellerBhai Dashboard</h2>
          <p className="text-slate-400 mb-4 text-sm">A temporary issue occurred while rendering this view.</p>
          <button
            onClick={() => { localStorage.clear(); window.location.href = '/'; }}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm font-semibold transition-all shadow-lg shadow-blue-500/20"
          >
            Reset Session & Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const ProtectedLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Single-Owner Private Direct Access (No login screen friction)
  try {
    const rawUser = localStorage.getItem('replybd_user');
    if (!rawUser || rawUser === 'undefined' || rawUser === 'null') {
      localStorage.setItem('replybd_user', JSON.stringify({ email: 'owner@sellerbhai.com', name: 'Store Owner' }));
    }
  } catch {
    // Ignore storage issues
  }
  if (!localStorage.getItem('replybd_token')) {
    localStorage.setItem('replybd_token', 'sellerbhai_owner_direct_token');
  }
  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
        <Navbar />
        <main className="flex-1">{children}</main>
      </div>
    </ErrorBoundary>
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
