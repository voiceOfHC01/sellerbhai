import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Package, BookOpen, MessageSquare, Settings as SettingsIcon, LogOut, Sparkles, ShoppingBag, Inbox, MessageCircle, Phone, Calendar, Send, BarChart3, CheckSquare } from 'lucide-react';

export const Navbar: React.FC = () => {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem('replybd_user') || '{"email": "admin@replybd.com"}');

  const handleLogout = () => {
    localStorage.removeItem('replybd_token');
    localStorage.removeItem('replybd_user');
    navigate('/login');
  };

  const navItemClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
      isActive
        ? 'bg-blue-50 text-blue-700 shadow-sm'
        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
    }`;

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo */}
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <ShoppingBag className="w-5 h-5" />
            </div>
            <div>
              <span className="text-lg font-bold text-slate-900 tracking-tight">reply.bd</span>
              <span className="ml-1.5 px-1.5 py-0.5 rounded text-[10px] font-semibold tracking-wide bg-blue-100 text-blue-700">AI AGENT</span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1.5">
            <NavLink to="/dashboard" className={navItemClass}>
              <BarChart3 className="w-4 h-4 text-blue-600" />
              <span>Dashboard</span>
            </NavLink>
            <NavLink to="/" className={navItemClass}>
              <Package className="w-4 h-4" />
              <span>Catalog</span>
            </NavLink>
            <NavLink to="/orders" className={navItemClass}>
              <ShoppingBag className="w-4 h-4" />
              <span>Orders</span>
            </NavLink>
            <NavLink to="/inbox" className={navItemClass}>
              <Inbox className="w-4 h-4" />
              <span>Unified Inbox</span>
            </NavLink>
            <NavLink to="/comments" className={navItemClass}>
              <MessageCircle className="w-4 h-4" />
              <span>Comments</span>
            </NavLink>
            <NavLink to="/whatsapp" className={navItemClass}>
              <Phone className="w-4 h-4 text-emerald-600" />
              <span>WhatsApp</span>
            </NavLink>
            <NavLink to="/posts" className={navItemClass}>
              <Calendar className="w-4 h-4 text-purple-600" />
              <span>Posts & Calendar</span>
            </NavLink>
            <NavLink to="/broadcasts" className={navItemClass}>
              <Send className="w-4 h-4 text-teal-600" />
              <span>Broadcast</span>
            </NavLink>
            <NavLink to="/knowledge" className={navItemClass}>
              <BookOpen className="w-4 h-4" />
              <span>Knowledge Base</span>
            </NavLink>
            <NavLink to="/test-chat" className={navItemClass}>
              <MessageSquare className="w-4 h-4" />
              <span>Test Chat</span>
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-100 text-emerald-800 font-semibold">Live AI</span>
            </NavLink>
            <NavLink to="/ai-review" className={navItemClass}>
              <CheckSquare className="w-4 h-4 text-purple-600" />
              <span>AI Review</span>
            </NavLink>
            <NavLink to="/settings" className={navItemClass}>
              <SettingsIcon className="w-4 h-4" />
              <span>Settings</span>
            </NavLink>
          </nav>
        </div>

        {/* Right Info & Logout */}
        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100 border border-slate-200 text-xs text-slate-600">
            <Sparkles className="w-3.5 h-3.5 text-blue-600" />
            <span>Bangla • Banglish • English</span>
          </div>

          <div className="flex items-center gap-3 pl-2 border-l border-slate-200">
            <div className="hidden lg:block text-right">
              <p className="text-xs font-semibold text-slate-800 leading-tight">Admin Owner</p>
              <p className="text-[11px] text-slate-400">{user.email}</p>
            </div>
            <button
              onClick={handleLogout}
              title="Sign Out"
              className="p-2 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
