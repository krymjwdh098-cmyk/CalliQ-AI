import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Briefcase, Users, BarChart3, Settings,
  LogOut, Menu, X, ChevronRight, Bell, Brain,
} from 'lucide-react';
import { useAuthStore } from '../../store/auth';

const NAV = [
  { to: '/dashboard', icon: <LayoutDashboard size={18} />, label: 'Dashboard' },
  { to: '/jobs', icon: <Briefcase size={18} />, label: 'Jobs' },
  { to: '/candidates', icon: <Users size={18} />, label: 'Candidates' },
  { to: '/reports', icon: <BarChart3 size={18} />, label: 'Reports' },
  { to: '/settings', icon: <Settings size={18} />, label: 'Settings' },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const initials = user?.name?.split(' ').map(n => n[0]).join('').slice(0, 2) || 'U';

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={() => setMobileOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:relative z-50 h-full bg-slate-900 flex flex-col transition-all duration-200
        ${collapsed ? 'w-16' : 'w-64'}
        ${mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-5 border-b border-slate-700/50">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
            <Brain size={16} className="text-white" />
          </div>
          {!collapsed && <span className="text-white font-bold text-base">TalentAI</span>}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 overflow-y-auto scrollbar-thin">
          {NAV.map(item => {
            const active = location.pathname.startsWith(item.to);
            return (
              <Link
                key={item.to}
                to={item.to}
                onClick={() => setMobileOpen(false)}
                className={`flex items-center gap-3 mx-2 px-3 py-2.5 rounded-lg mb-0.5 transition-colors
                  ${active
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
              >
                <span className="flex-shrink-0">{item.icon}</span>
                {!collapsed && <span className="text-sm font-medium">{item.label}</span>}
                {!collapsed && active && <ChevronRight size={14} className="ml-auto" />}
              </Link>
            );
          })}
        </nav>

        {/* User footer */}
        <div className="border-t border-slate-700/50 p-3">
          {!collapsed ? (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                {initials}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white text-xs font-medium truncate">{user?.name}</p>
                <p className="text-slate-400 text-xs capitalize">{user?.role}</p>
              </div>
              <button onClick={handleLogout} className="text-slate-400 hover:text-white p-1 rounded">
                <LogOut size={15} />
              </button>
            </div>
          ) : (
            <button onClick={handleLogout} className="w-full flex justify-center text-slate-400 hover:text-white p-2 rounded">
              <LogOut size={18} />
            </button>
          )}
        </div>

        {/* Collapse toggle (desktop) */}
        <button
          onClick={() => setCollapsed(c => !c)}
          className="hidden lg:flex absolute -right-3 top-8 w-6 h-6 bg-slate-700 border border-slate-600 rounded-full items-center justify-center text-slate-400 hover:text-white transition-colors"
        >
          <ChevronRight size={12} className={`transition-transform ${collapsed ? '' : 'rotate-180'}`} />
        </button>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="bg-white border-b border-slate-200 px-4 lg:px-6 py-3 flex items-center gap-3">
          <button className="lg:hidden p-1.5 hover:bg-slate-100 rounded-lg" onClick={() => setMobileOpen(true)}>
            <Menu size={20} className="text-slate-600" />
          </button>
          <div className="flex-1" />
          <div className="flex items-center gap-1 text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            {user?.org_name || 'Organization'}
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }: {
  title: string; subtitle?: string; actions?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="text-xl font-bold text-slate-800">{title}</h1>
        {subtitle && <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
