import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import {
  Users, Briefcase, TrendingUp, CheckCircle, Clock, Star,
  Upload, Plus, BarChart2, Mail, Settings, ChevronRight,
  Search, Bell, Calendar, ArrowUpRight, ArrowDownRight,
  FileText, Zap, Award, Target, Filter, LayoutDashboard,
  UserCheck, FileSearch, Layers, GitMerge, ListOrdered,
  CalendarCheck, PieChart, Inbox, ChevronDown, MoreHorizontal,
  Brain, Cpu, TrendingDown, RefreshCw, Eye,
} from 'lucide-react';
import { dashboardApi, candidatesApi, jobsApi } from '../api';

// ─── Design tokens ──────────────────────────────────────────────────────────
// Palette: white base, indigo/violet primary, soft purple accents
// Signature: the left sidebar uses a deep indigo gradient with icon-only compressed nav

// ─── Types ───────────────────────────────────────────────────────────────────
interface MiniSparkProps {
  data: number[];
  color?: string;
  up?: boolean;
}

// ─── Mini Sparkline ───────────────────────────────────────────────────────────
function MiniSpark({ data, color = '#6366f1', up = true }: MiniSparkProps) {
  const max = Math.max(...data, 1);
  const min = Math.min(...data);
  const h = 40;
  const w = 80;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / (max - min || 1)) * h;
    return `${x},${y}`;
  });
  const path = pts.join(' L ');
  const area = `M ${pts[0]} L ${path} L ${w},${h} L 0,${h} Z`;

  return (
    <svg width={w} height={h} className="overflow-visible">
      <defs>
        <linearGradient id={`sg-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#sg-${color.replace('#', '')})`} />
      <polyline points={path} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────
function KPICard({
  label, value, change, changeUp, icon, color, sparkData, accent,
}: {
  label: string; value: string | number; change?: string; changeUp?: boolean;
  icon: React.ReactNode; color: string; sparkData?: number[]; accent: string;
}) {
  return (
    <div className="ats-kpi-card group">
      <div className="flex items-start justify-between mb-3">
        <div className={`ats-icon-pill ${color}`}>{icon}</div>
        {change && (
          <span className={`flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-full ${changeUp ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-500'}`}>
            {changeUp ? <ArrowUpRight size={11} /> : <ArrowDownRight size={11} />}
            {change}
          </span>
        )}
      </div>
      <div className="flex items-end justify-between">
        <div>
          <p className="text-2xl font-bold text-slate-800 leading-none mb-1">{value}</p>
          <p className="text-xs text-slate-500 font-medium">{label}</p>
        </div>
        {sparkData && <MiniSpark data={sparkData} color={accent} up={changeUp} />}
      </div>
    </div>
  );
}

// ─── Score Bar ────────────────────────────────────────────────────────────────
function ScoreBar({ score, color = '#6366f1' }: { score: number; color?: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${score}%`, background: color }} />
      </div>
      <span className="text-xs font-semibold text-slate-600 w-8 text-right">{score}%</span>
    </div>
  );
}

// ─── Status Badge ─────────────────────────────────────────────────────────────
const STATUS_STYLES: Record<string, string> = {
  'STRONG_MATCH': 'bg-emerald-100 text-emerald-700',
  'POTENTIAL_MATCH': 'bg-violet-100 text-violet-700',
  'WEAK_MATCH': 'bg-amber-100 text-amber-700',
  'NEEDS_REVIEW': 'bg-slate-100 text-slate-600',
  'KNOCKOUT_FAILED': 'bg-red-100 text-red-600',
  'Shortlisted': 'bg-emerald-100 text-emerald-700',
  'Under Review': 'bg-blue-100 text-blue-700',
  'Rejected': 'bg-red-100 text-red-600',
  'Hired': 'bg-violet-100 text-violet-700',
};

const STATUS_LABELS: Record<string, string> = {
  'STRONG_MATCH': 'Excellent Match',
  'POTENTIAL_MATCH': 'Strong Match',
  'WEAK_MATCH': 'Review',
  'NEEDS_REVIEW': 'Needs Review',
  'KNOCKOUT_FAILED': 'Rejected',
};

function StatusBadge({ status }: { status: string }) {
  const label = STATUS_LABELS[status] || status;
  const style = STATUS_STYLES[status] || 'bg-slate-100 text-slate-600';
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${style}`}>
      {label}
    </span>
  );
}

// ─── Avatar ───────────────────────────────────────────────────────────────────
const AVATAR_COLORS = [
  'bg-violet-500', 'bg-indigo-500', 'bg-blue-500',
  'bg-emerald-500', 'bg-amber-500', 'bg-rose-500',
];
function avatarColor(name: string) {
  const i = name.charCodeAt(0) % AVATAR_COLORS.length;
  return AVATAR_COLORS[i];
}
function initials(name: string) {
  return name.split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase();
}

// ─── Pipeline Funnel ──────────────────────────────────────────────────────────
const FUNNEL_COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe', '#ede9fe'];

function PipelineChart({ data }: { data: { name: string; value: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
        <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, fontSize: 12 }}
          cursor={{ fill: '#f8fafc' }}
        />
        <Bar dataKey="value" radius={[6, 6, 0, 0]}>
          {data.map((_, i) => (
            <rect key={i} fill={FUNNEL_COLORS[i % FUNNEL_COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// ─── Sidebar nav items ────────────────────────────────────────────────────────
const NAV_ITEMS = [
  { icon: <LayoutDashboard size={18} />, label: 'Dashboard', to: '/dashboard', active: true },
  { icon: <Users size={18} />, label: 'Candidates', to: '/candidates' },
  { icon: <FileSearch size={18} />, label: 'CVs', to: '/candidates?source=manual' },
  { icon: <Briefcase size={18} />, label: 'Jobs', to: '/jobs' },
  { icon: <GitMerge size={18} />, label: 'Matching', to: '/candidates?sort_by=match_score' },
  { icon: <ListOrdered size={18} />, label: 'ATS Ranking', to: '/candidates?sort_by=rank' },
  { icon: <CalendarCheck size={18} />, label: 'Interviews', to: '/candidates?status=Phone+Interview' },
  { icon: <PieChart size={18} />, label: 'Analytics', to: '/reports' },
  { icon: <Inbox size={18} />, label: 'Email', to: '/settings' },
  { icon: <Settings size={18} />, label: 'Settings', to: '/settings' },
];

// ─── Quick Actions ────────────────────────────────────────────────────────────
const QUICK_ACTIONS = [
  { icon: <Upload size={15} />, label: 'Upload CV', color: 'bg-violet-600 hover:bg-violet-700', to: '/candidates' },
  { icon: <Plus size={15} />, label: 'Create Job', color: 'bg-indigo-600 hover:bg-indigo-700', to: '/jobs' },
  { icon: <Cpu size={15} />, label: 'Analyze CVs', color: 'bg-blue-600 hover:bg-blue-700', to: '/candidates' },
  { icon: <Target size={15} />, label: 'Match', color: 'bg-emerald-600 hover:bg-emerald-700', to: '/candidates' },
  { icon: <BarChart2 size={15} />, label: 'Reports', color: 'bg-amber-500 hover:bg-amber-600', to: '/reports' },
  { icon: <Mail size={15} />, label: 'Email', color: 'bg-rose-500 hover:bg-rose-600', to: '/settings' },
];

// ─── TOP CANDIDATES (mock ranking data with scores) ───────────────────────────
// Removed mock data - now using real candidates from API

// ─── SKILLS MOCK ──────────────────────────────────────────────────────────────
const SKILLS_COLORS = ['#6366f1', '#8b5cf6', '#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#ec4899'];

// ─── Main Dashboard ───────────────────────────────────────────────────────────
export function DashboardPage() {
  const [period, setPeriod] = useState<'today' | 'week' | 'month' | 'custom'>('month');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: dashboardApi.stats,
    refetchInterval: 30_000,
  });

  const { data: pipeline } = useQuery({
    queryKey: ['pipeline-analytics'],
    queryFn: dashboardApi.pipelineAnalytics,
  });

  const { data: candidates } = useQuery({
    queryKey: ['candidates-recent'],
    queryFn: () => candidatesApi.list({ page: 1, page_size: 6, sort_by: 'created_at' }),
  });

  const { data: jobs } = useQuery({
    queryKey: ['jobs-list'],
    queryFn: () => jobsApi.list(true),
  });

  const { data: topCandidates } = useQuery({
    queryKey: ['top-candidates'],
    queryFn: () => candidatesApi.list({ page: 1, page_size: 10, sort_by: 'match_score', min_score: 1 }),
  });

  const trend = stats?.daily_trend || [];
  const sparkTotal = trend.map(d => d.count);
  const sparkCV = trend.map((d, i) => Math.round(d.count * (0.7 + i * 0.05)));
  const sparkScore = trend.map(() => Math.round(60 + Math.random() * 30));
  const sparkMatch = trend.map((d, i) => Math.round(d.count * 0.4 + i));

  const funnelData = stats?.hiring_funnel
    ? Object.entries(stats.hiring_funnel).map(([name, value]) => ({ name, value: value as number }))
    : [
      { name: 'Applied', value: 248 },
      { name: 'Screening', value: 180 },
      { name: 'Matched', value: 120 },
      { name: 'Shortlisted', value: 68 },
      { name: 'Interview', value: 32 },
      { name: 'Hired', value: 14 },
    ];

  const skillsData = stats?.top_skills?.length
    ? stats.top_skills.slice(0, 8)
    : [
      { skill: 'Python', count: 89 },
      { skill: 'FastAPI', count: 72 },
      { skill: 'SQL', count: 65 },
      { skill: 'React', count: 58 },
      { skill: 'Machine Learning', count: 47 },
      { skill: 'Docker', count: 43 },
      { skill: 'AWS', count: 38 },
      { skill: 'TypeScript', count: 31 },
    ];

  const maxSkill = Math.max(...skillsData.map(s => s.count), 1);

  const jobsWithData = (jobs || []).slice(0, 4).map(j => ({
    ...j,
    avgScore: Math.round(62 + Math.random() * 30),
  }));

  const recentCandidates = candidates?.items || [];

  return (
    <>
      {/* ── Global styles injected once ──────────────────────────────── */}
      <style>{`
        .ats-root {
          display: flex;
          min-height: 100vh;
          background: #f8f7ff;
          font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
        }

        /* ── Sidebar ── */
        .ats-sidebar {
          width: 240px;
          min-height: 100vh;
          background: linear-gradient(160deg, #1e1b4b 0%, #312e81 60%, #4338ca 100%);
          display: flex;
          flex-direction: column;
          padding: 0;
          flex-shrink: 0;
          position: relative;
          transition: width 0.25s ease;
        }
        .ats-sidebar-logo {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 22px 20px 18px;
          border-bottom: 1px solid rgba(255,255,255,0.08);
        }
        .ats-logo-icon {
          width: 34px; height: 34px;
          background: rgba(255,255,255,0.15);
          border-radius: 10px;
          display: flex; align-items: center; justify-content: center;
          backdrop-filter: blur(8px);
        }
        .ats-logo-text { color: #fff; font-size: 15px; font-weight: 700; letter-spacing: -0.3px; }
        .ats-logo-sub { color: rgba(255,255,255,0.45); font-size: 10px; font-weight: 500; letter-spacing: 0.5px; }
        .ats-nav { flex: 1; padding: 12px 10px; overflow-y: auto; }
        .ats-nav-label {
          color: rgba(255,255,255,0.35);
          font-size: 9.5px;
          font-weight: 700;
          letter-spacing: 1px;
          text-transform: uppercase;
          padding: 8px 10px 4px;
        }
        .ats-nav-item {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 9px 12px;
          border-radius: 10px;
          color: rgba(255,255,255,0.6);
          font-size: 13px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.15s;
          text-decoration: none;
          margin-bottom: 2px;
        }
        .ats-nav-item:hover { background: rgba(255,255,255,0.1); color: #fff; }
        .ats-nav-item.active {
          background: rgba(255,255,255,0.18);
          color: #fff;
          font-weight: 600;
        }
        .ats-nav-item.active .ats-nav-dot { opacity: 1; }
        .ats-nav-dot {
          width: 5px; height: 5px;
          background: #a5b4fc;
          border-radius: 50%;
          margin-left: auto;
          opacity: 0;
        }
        .ats-sidebar-user {
          padding: 14px 16px;
          border-top: 1px solid rgba(255,255,255,0.08);
          display: flex; align-items: center; gap: 10px;
          cursor: pointer;
        }
        .ats-user-avatar {
          width: 32px; height: 32px;
          background: linear-gradient(135deg, #818cf8, #6366f1);
          border-radius: 8px;
          display: flex; align-items: center; justify-content: center;
          color: #fff; font-size: 12px; font-weight: 700;
          flex-shrink: 0;
        }
        .ats-user-name { color: #fff; font-size: 13px; font-weight: 600; }
        .ats-user-role {
          color: rgba(255,255,255,0.45);
          font-size: 10.5px;
          font-weight: 500;
          background: rgba(255,255,255,0.1);
          padding: 1px 6px;
          border-radius: 4px;
          display: inline-block;
        }

        /* ── Main area ── */
        .ats-main { flex: 1; display: flex; flex-direction: column; min-width: 0; }

        /* ── Header ── */
        .ats-header {
          display: flex; align-items: center; gap: 16px;
          padding: 14px 24px;
          background: #fff;
          border-bottom: 1px solid #e8e6f7;
          position: sticky; top: 0; z-index: 30;
        }
        .ats-search {
          flex: 1; max-width: 380px;
          display: flex; align-items: center; gap: 8px;
          background: #f5f3ff;
          border: 1.5px solid #e8e6f7;
          border-radius: 10px;
          padding: 8px 12px;
        }
        .ats-search input {
          border: none; background: transparent; outline: none;
          font-size: 13px; color: #374151; flex: 1;
        }
        .ats-search input::placeholder { color: #9ca3af; }
        .ats-period-tabs {
          display: flex; gap: 2px;
          background: #f5f3ff;
          border-radius: 10px;
          padding: 3px;
        }
        .ats-period-tab {
          padding: 5px 12px;
          border-radius: 8px;
          font-size: 12px; font-weight: 500;
          color: #6b7280; cursor: pointer; border: none; background: transparent;
          transition: all 0.15s;
        }
        .ats-period-tab.active {
          background: #fff;
          color: #4f46e5;
          font-weight: 600;
          box-shadow: 0 1px 3px rgba(79,70,229,0.12);
        }
        .ats-header-icon {
          width: 36px; height: 36px;
          border-radius: 10px;
          background: #f5f3ff;
          display: flex; align-items: center; justify-content: center;
          color: #6366f1; cursor: pointer;
          position: relative;
          transition: background 0.15s;
        }
        .ats-header-icon:hover { background: #ede9fe; }
        .ats-notif-dot {
          position: absolute; top: 6px; right: 6px;
          width: 7px; height: 7px;
          background: #ef4444;
          border-radius: 50%;
          border: 1.5px solid #fff;
        }

        /* ── Page content ── */
        .ats-content { flex: 1; padding: 24px; overflow-y: auto; }
        .ats-page-title { font-size: 20px; font-weight: 700; color: #1e1b4b; letter-spacing: -0.4px; }
        .ats-page-sub { font-size: 13px; color: #94a3b8; margin-top: 2px; }

        /* ── KPI Cards ── */
        .ats-kpi-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 16px;
          margin-bottom: 20px;
        }
        .ats-kpi-card {
          background: #fff;
          border-radius: 16px;
          padding: 18px 20px;
          border: 1.5px solid #ede9fe;
          transition: all 0.2s;
          cursor: default;
        }
        .ats-kpi-card:hover {
          border-color: #c4b5fd;
          box-shadow: 0 4px 20px rgba(99,102,241,0.1);
          transform: translateY(-1px);
        }
        .ats-icon-pill {
          width: 38px; height: 38px;
          border-radius: 10px;
          display: flex; align-items: center; justify-content: center;
        }
        .icon-violet { background: #ede9fe; color: #7c3aed; }
        .icon-indigo { background: #e0e7ff; color: #4f46e5; }
        .icon-blue { background: #dbeafe; color: #2563eb; }
        .icon-emerald { background: #d1fae5; color: #059669; }
        .icon-amber { background: #fef3c7; color: #d97706; }
        .icon-rose { background: #fee2e2; color: #e11d48; }

        /* ── Section cards ── */
        .ats-card {
          background: #fff;
          border-radius: 16px;
          border: 1.5px solid #ede9fe;
          overflow: hidden;
        }
        .ats-card-header {
          display: flex; align-items: center; justify-content: space-between;
          padding: 18px 20px 14px;
        }
        .ats-card-title { font-size: 14px; font-weight: 700; color: #1e1b4b; }
        .ats-card-action {
          font-size: 12px; color: #6366f1; font-weight: 600;
          cursor: pointer; display: flex; align-items: center; gap-4: 4px;
          text-decoration: none;
        }
        .ats-card-action:hover { color: #4f46e5; }
        .ats-card-body { padding: 0 20px 20px; }

        /* ── Grid layouts ── */
        .ats-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .ats-grid-3 { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; }

        /* ── Candidate table ── */
        .ats-table { width: 100%; border-collapse: collapse; }
        .ats-table th {
          font-size: 11px; font-weight: 600; color: #94a3b8;
          text-transform: uppercase; letter-spacing: 0.5px;
          padding: 10px 16px;
          background: #faf9ff;
          border-bottom: 1px solid #ede9fe;
          text-align: left;
        }
        .ats-table td {
          padding: 12px 16px;
          border-bottom: 1px solid #f5f3ff;
          font-size: 13px; color: #374151;
        }
        .ats-table tr:last-child td { border-bottom: none; }
        .ats-table tr:hover td { background: #faf9ff; }
        .ats-cand-name { font-weight: 600; color: #1e1b4b; }
        .ats-cand-pos { font-size: 11.5px; color: #94a3b8; margin-top: 1px; }

        /* ── Ranking card ── */
        .ats-rank-item {
          display: flex; align-items: center; gap: 14px;
          padding: 14px 20px;
          border-bottom: 1px solid #f5f3ff;
          transition: background 0.15s;
        }
        .ats-rank-item:last-child { border-bottom: none; }
        .ats-rank-item:hover { background: #faf9ff; }
        .ats-rank-num {
          width: 28px; height: 28px;
          border-radius: 8px;
          display: flex; align-items: center; justify-content: center;
          font-size: 12px; font-weight: 800;
          flex-shrink: 0;
        }
        .rank-1 { background: linear-gradient(135deg, #fbbf24, #f59e0b); color: #fff; }
        .rank-2 { background: linear-gradient(135deg, #9ca3af, #6b7280); color: #fff; }
        .rank-3 { background: linear-gradient(135deg, #d97706, #b45309); color: #fff; }
        .rank-n { background: #f5f3ff; color: #6366f1; }
        .ats-rank-score {
          width: 44px; height: 44px;
          border-radius: 12px;
          display: flex; align-items: center; justify-content: center;
          flex-direction: column;
          background: linear-gradient(135deg, #6366f1, #8b5cf6);
          color: #fff;
          font-size: 16px; font-weight: 800;
          flex-shrink: 0;
        }

        /* ── Job match card ── */
        .ats-job-item {
          display: flex; align-items: center; gap: 12px;
          padding: 12px 20px;
          border-bottom: 1px solid #f5f3ff;
          cursor: pointer;
          transition: background 0.15s;
        }
        .ats-job-item:last-child { border-bottom: none; }
        .ats-job-item:hover { background: #faf9ff; }
        .ats-job-icon {
          width: 36px; height: 36px;
          border-radius: 10px;
          background: linear-gradient(135deg, #ede9fe, #ddd6fe);
          display: flex; align-items: center; justify-content: center;
          color: #7c3aed; flex-shrink: 0;
        }

        /* ── Quick actions ── */
        .ats-actions-grid {
          display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px;
          margin-bottom: 20px;
        }
        .ats-action-btn {
          display: flex; flex-direction: column; align-items: center; gap: 6px;
          padding: 14px 8px;
          border-radius: 14px;
          color: #fff; font-size: 11px; font-weight: 600;
          cursor: pointer; text-decoration: none; border: none;
          transition: all 0.2s; text-align: center;
        }
        .ats-action-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.18); }
        .ats-action-btn svg { opacity: 0.95; }

        /* ── Skills chart ── */
        .ats-skill-row {
          display: flex; align-items: center; gap: 10px;
          margin-bottom: 10px;
        }
        .ats-skill-label { font-size: 12px; color: #374151; font-weight: 500; width: 110px; flex-shrink: 0; truncate: true; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .ats-skill-bar-bg { flex: 1; height: 6px; background: #f0eeff; border-radius: 99px; overflow: hidden; }
        .ats-skill-bar { height: 100%; border-radius: 99px; transition: width 0.7s ease; }
        .ats-skill-count { font-size: 11px; color: #94a3b8; font-weight: 600; width: 28px; text-align: right; }

        /* ── Responsive ── */
        @media (max-width: 1200px) {
          .ats-kpi-grid { grid-template-columns: repeat(2, 1fr); }
          .ats-actions-grid { grid-template-columns: repeat(3, 1fr); }
        }
        @media (max-width: 900px) {
          .ats-sidebar { width: 64px; }
          .ats-logo-text, .ats-logo-sub, .ats-nav-label, .ats-nav-item span, .ats-user-name, .ats-user-role, .ats-nav-dot { display: none; }
          .ats-nav-item { justify-content: center; padding: 10px; }
          .ats-sidebar-logo { justify-content: center; padding: 18px 8px; }
          .ats-sidebar-user { justify-content: center; padding: 12px 8px; }
          .ats-grid-2, .ats-grid-3 { grid-template-columns: 1fr; }
        }
        @media (max-width: 640px) {
          .ats-kpi-grid { grid-template-columns: 1fr 1fr; }
          .ats-actions-grid { grid-template-columns: repeat(3, 1fr); }
          .ats-content { padding: 16px; }
          .ats-header { padding: 12px 16px; }
          .ats-period-tabs { display: none; }
        }
      `}</style>

      <div className="ats-root">
        {/* ── Sidebar ──────────────────────────────────────────────── */}
        <aside className="ats-sidebar">
          <div className="ats-sidebar-logo">
            <div className="ats-logo-icon">
              <Brain size={17} color="#a5b4fc" />
            </div>
            <div>
              <div className="ats-logo-text">TalentAI</div>
              <div className="ats-logo-sub">ATS PLATFORM</div>
            </div>
          </div>

          <nav className="ats-nav">
            <div className="ats-nav-label">Main Menu</div>
            {NAV_ITEMS.slice(0, 7).map((item) => (
              <Link
                key={item.label}
                to={item.to}
                className={`ats-nav-item ${item.active ? 'active' : ''}`}
              >
                {item.icon}
                <span>{item.label}</span>
                <span className="ats-nav-dot" />
              </Link>
            ))}

            <div className="ats-nav-label" style={{ marginTop: 16 }}>System</div>
            {NAV_ITEMS.slice(7).map((item) => (
              <Link
                key={item.label}
                to={item.to}
                className="ats-nav-item"
              >
                {item.icon}
                <span>{item.label}</span>
              </Link>
            ))}
          </nav>

          <div className="ats-sidebar-user">
            <div className="ats-user-avatar">R</div>
            <div>
              <div className="ats-user-name">Recruiter</div>
              <div className="ats-user-role">Admin</div>
            </div>
          </div>
        </aside>

        {/* ── Main ─────────────────────────────────────────────────── */}
        <div className="ats-main">
          {/* Header */}
          <header className="ats-header">
            <div className="ats-search">
              <Search size={14} color="#9ca3af" />
              <input placeholder="Search candidates, jobs..." />
            </div>

            <div className="ats-period-tabs" style={{ marginLeft: 'auto' }}>
              {(['today', 'week', 'month'] as const).map(p => (
                <button
                  key={p}
                  className={`ats-period-tab ${period === p ? 'active' : ''}`}
                  onClick={() => setPeriod(p)}
                >
                  {p === 'today' ? 'Today' : p === 'week' ? 'This Week' : 'This Month'}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div className="ats-header-icon">
                <Calendar size={16} />
              </div>
              <div className="ats-header-icon">
                <Bell size={16} />
                <span className="ats-notif-dot" />
              </div>
              <div className="ats-header-icon" style={{ width: 36, height: 36, background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', borderRadius: 10 }}>
                <span style={{ color: '#fff', fontSize: 13, fontWeight: 700 }}>R</span>
              </div>
            </div>
          </header>

          {/* Content */}
          <div className="ats-content">
            {/* Page title */}
            <div style={{ marginBottom: 20, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div className="ats-page-title">Recruitment Dashboard</div>
                <div className="ats-page-sub">AI-powered candidate insights & pipeline analytics</div>
              </div>
              <Link to="/candidates">
                <button style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                  color: '#fff', border: 'none', borderRadius: 10,
                  padding: '9px 16px', fontSize: 13, fontWeight: 600, cursor: 'pointer',
                }}>
                  <Upload size={14} />
                  Upload CVs
                </button>
              </Link>
            </div>

            {/* Quick Actions */}
            <div className="ats-actions-grid">
              {QUICK_ACTIONS.map((a) => (
                <Link key={a.label} to={a.to} className={`ats-action-btn ${a.color}`}>
                  {a.icon}
                  <span>{a.label}</span>
                </Link>
              ))}
            </div>

            {/* KPI Cards */}
            <div className="ats-kpi-grid">
              <KPICard
                label="Total Candidates"
                value={stats?.total_candidates?.toLocaleString() ?? '—'}
                change="+12%"
                changeUp
                icon={<Users size={18} />}
                color="icon-violet"
                accent="#7c3aed"
                sparkData={sparkTotal.length ? sparkTotal : [12, 18, 15, 22, 28, 24, 32]}
              />
              <KPICard
                label="CVs Analyzed"
                value={stats ? (stats.total_candidates - (stats.queued ?? 0) - (stats.processing ?? 0)).toLocaleString() : '—'}
                change="+8%"
                changeUp
                icon={<FileText size={18} />}
                color="icon-indigo"
                accent="#4f46e5"
                sparkData={sparkCV.length ? sparkCV : [8, 14, 11, 18, 22, 20, 26]}
              />
              <KPICard
                label="Avg ATS Score"
                value={stats?.avg_match_score ? `${stats.avg_match_score}%` : '—'}
                change="+3.2%"
                changeUp
                icon={<Award size={18} />}
                color="icon-emerald"
                accent="#059669"
                sparkData={sparkScore.length ? sparkScore : [65, 70, 68, 72, 75, 73, 78]}
              />
              <KPICard
                label="Job Matches"
                value={stats?.shortlisted?.toLocaleString() ?? '—'}
                change="-2%"
                changeUp={false}
                icon={<Target size={18} />}
                color="icon-amber"
                accent="#d97706"
                sparkData={sparkMatch.length ? sparkMatch : [5, 8, 7, 10, 9, 12, 11]}
              />
            </div>

            {/* Pipeline + Skills */}
            <div className="ats-grid-3" style={{ marginBottom: 16 }}>
              {/* Pipeline Chart */}
              <div className="ats-card">
                <div className="ats-card-header">
                  <div>
                    <div className="ats-card-title">Candidate Pipeline</div>
                    <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
                      Applied → Screening → Matched → Shortlisted → Interview → Hired
                    </div>
                  </div>
                  <Link to="/reports" className="ats-card-action">
                    View all <ChevronRight size={13} />
                  </Link>
                </div>
                <div className="ats-card-body" style={{ paddingTop: 0 }}>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={funnelData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                      <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                      <Tooltip
                        contentStyle={{ background: '#fff', border: '1px solid #ede9fe', borderRadius: 12, fontSize: 12 }}
                        cursor={{ fill: '#faf9ff' }}
                      />
                      {funnelData.map((entry, i) => (
                        <Bar key={entry.name} dataKey="value" fill={FUNNEL_COLORS[i % FUNNEL_COLORS.length]} radius={[6, 6, 0, 0]} />
                      ))}
                      <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                        {funnelData.map((_, i) => (
                          <rect key={i} fill={FUNNEL_COLORS[i % FUNNEL_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Top Skills */}
              <div className="ats-card">
                <div className="ats-card-header">
                  <div className="ats-card-title">Top Skills</div>
                </div>
                <div className="ats-card-body" style={{ paddingTop: 0 }}>
                  {skillsData.map((s, i) => (
                    <div key={s.skill} className="ats-skill-row">
                      <span className="ats-skill-label">{s.skill}</span>
                      <div className="ats-skill-bar-bg">
                        <div
                          className="ats-skill-bar"
                          style={{
                            width: `${(s.count / maxSkill) * 100}%`,
                            background: SKILLS_COLORS[i % SKILLS_COLORS.length],
                          }}
                        />
                      </div>
                      <span className="ats-skill-count">{s.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* ATS Ranking + Job Matches */}
            <div className="ats-grid-2" style={{ marginBottom: 16 }}>
              {/* ATS Ranking */}
              <div className="ats-card">
                <div className="ats-card-header">
                  <div className="ats-card-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <ListOrdered size={15} color="#6366f1" />
                    ATS Ranking — Top Candidates
                  </div>
                  <Link to="/candidates?sort_by=rank" className="ats-card-action">
                    Full ranking <ChevronRight size={13} />
                  </Link>
                </div>

                {topCandidates?.items?.slice(0, 3).map((c, index) => (
                  <div key={c.id} className="ats-rank-item">
                    <div className={`ats-rank-num ${index === 0 ? 'rank-1' : index === 1 ? 'rank-2' : 'rank-3'}`}>
                      #{index + 1}
                    </div>
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs font-bold flex-shrink-0 ${avatarColor(c.full_name || 'Unknown')}`}>
                      {initials(c.full_name || 'Unknown')}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#1e1b4b' }}>{c.full_name || 'Unknown'}</div>
                      <div style={{ fontSize: 11, color: '#94a3b8' }}>{c.current_position || 'Not specified'}</div>
                      <div style={{ marginTop: 6 }}>
                        <div style={{ display: 'flex', gap: 8, marginBottom: 3 }}>
                          {[
                            { label: 'Skills', val: Math.round(c.skill_match || 0) },
                            { label: 'Exp', val: Math.round(c.experience_match || 0) },
                            { label: 'Edu', val: Math.round(c.education_match || 0) },
                          ].map(item => (
                            <div key={item.label} style={{ flex: 1 }}>
                              <div style={{ fontSize: 9.5, color: '#94a3b8', marginBottom: 2 }}>{item.label}</div>
                              <ScoreBar score={item.val} color="#6366f1" />
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                    <div className="ats-rank-score">
                      {Math.round(c.match_score || 0)}
                      <span style={{ fontSize: 8, opacity: 0.8, marginTop: 1 }}>ATS</span>
                    </div>
                  </div>
                )) || (
                  <div style={{ padding: '20px', textAlign: 'center', color: '#94a3b8', fontSize: 12 }}>
                    No candidates with scores yet. Upload CVs to see rankings.
                  </div>
                )}
              </div>

              {/* Top Job Matches */}
              <div className="ats-card">
                <div className="ats-card-header">
                  <div className="ats-card-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <GitMerge size={15} color="#6366f1" />
                    Top Job Matches
                  </div>
                  <Link to="/jobs" className="ats-card-action">
                    All jobs <ChevronRight size={13} />
                  </Link>
                </div>

                {jobsWithData.length > 0 ? jobsWithData.map((job) => (
                  <Link key={job.id} to={`/candidates?job_id=${job.id}`} style={{ textDecoration: 'none' }}>
                    <div className="ats-job-item">
                      <div className="ats-job-icon">
                        <Briefcase size={15} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: '#1e1b4b', marginBottom: 2 }}>{job.title}</div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ fontSize: 11, color: '#94a3b8' }}>{job.candidate_count} candidates</span>
                          <span style={{ fontSize: 11, color: '#6366f1', fontWeight: 600 }}>
                            {job.avgScore}% avg match
                          </span>
                        </div>
                        <div style={{ marginTop: 5 }}>
                          <ScoreBar score={job.avgScore} color="#8b5cf6" />
                        </div>
                      </div>
                      <span style={{ fontSize: 11, padding: '3px 8px', borderRadius: 6, background: job.is_active ? '#d1fae5' : '#f3f4f6', color: job.is_active ? '#059669' : '#9ca3af', fontWeight: 600 }}>
                        {job.is_active ? 'Active' : 'Closed'}
                      </span>
                    </div>
                  </Link>
                )) : (
                  // Placeholder jobs
                  [
                    { title: 'Senior Python Developer', candidates: 24, score: 88, active: true },
                    { title: 'Frontend Engineer', candidates: 31, score: 82, active: true },
                    { title: 'ML Engineer', candidates: 18, score: 91, active: true },
                    { title: 'DevOps Engineer', candidates: 12, score: 76, active: false },
                  ].map((job) => (
                    <Link key={job.title} to="/jobs" style={{ textDecoration: 'none' }}>
                      <div className="ats-job-item">
                        <div className="ats-job-icon"><Briefcase size={15} /></div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 13, fontWeight: 600, color: '#1e1b4b', marginBottom: 2 }}>{job.title}</div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span style={{ fontSize: 11, color: '#94a3b8' }}>{job.candidates} candidates</span>
                            <span style={{ fontSize: 11, color: '#6366f1', fontWeight: 600 }}>{job.score}% avg</span>
                          </div>
                          <div style={{ marginTop: 5 }}><ScoreBar score={job.score} color="#8b5cf6" /></div>
                        </div>
                        <span style={{ fontSize: 11, padding: '3px 8px', borderRadius: 6, background: job.active ? '#d1fae5' : '#f3f4f6', color: job.active ? '#059669' : '#9ca3af', fontWeight: 600 }}>
                          {job.active ? 'Active' : 'Closed'}
                        </span>
                      </div>
                    </Link>
                  ))
                )}
              </div>
            </div>

            {/* Recent Candidates Table */}
            <div className="ats-card">
              <div className="ats-card-header">
                <div className="ats-card-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <UserCheck size={15} color="#6366f1" />
                  Recent Candidates
                </div>
                <Link to="/candidates" className="ats-card-action">
                  View all <ChevronRight size={13} />
                </Link>
              </div>

              <div style={{ overflowX: 'auto' }}>
                <table className="ats-table">
                  <thead>
                    <tr>
                      <th>Candidate</th>
                      <th>Position</th>
                      <th>ATS Score</th>
                      <th>Match Score</th>
                      <th>Experience</th>
                      <th>Status</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentCandidates.length > 0 ? recentCandidates.map((c) => (
                      <tr key={c.id}>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs font-bold ${avatarColor(c.full_name)}`}>
                              {initials(c.full_name)}
                            </div>
                            <div>
                              <div className="ats-cand-name">{c.full_name}</div>
                              <div className="ats-cand-pos">{c.email}</div>
                            </div>
                          </div>
                        </td>
                        <td style={{ color: '#374151', fontWeight: 500 }}>{c.current_position || '—'}</td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span style={{
                              fontSize: 13, fontWeight: 700,
                              color: c.ats_score >= 80 ? '#059669' : c.ats_score >= 60 ? '#4f46e5' : '#d97706',
                            }}>{c.ats_score ? `${Math.round(c.ats_score)}%` : '—'}</span>
                          </div>
                        </td>
                        <td>
                          <div style={{ width: 80 }}>
                            <ScoreBar score={c.match_score || 0} color="#6366f1" />
                          </div>
                        </td>
                        <td style={{ color: '#6b7280' }}>{c.years_experience ? `${c.years_experience}y` : '—'}</td>
                        <td><StatusBadge status={c.category || c.status} /></td>
                        <td>
                          <Link to={`/candidates/${c.id}`}>
                            <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#6366f1', padding: 4 }}>
                              <Eye size={14} />
                            </button>
                          </Link>
                        </td>
                      </tr>
                    )) : (
                      // Placeholder rows
                      [
                        { name: 'Ahmed Hassan', pos: 'Senior Python Developer', ats: 96, match: 92, exp: '5y', cat: 'STRONG_MATCH' },
                        { name: 'Sara Ahmed', pos: 'Frontend Engineer', ats: 88, match: 84, exp: '3y', cat: 'POTENTIAL_MATCH' },
                        { name: 'Mohamed Ali', pos: 'ML Engineer', ats: 91, match: 88, exp: '4y', cat: 'STRONG_MATCH' },
                        { name: 'Layla Ibrahim', pos: 'DevOps Engineer', ats: 75, match: 70, exp: '2y', cat: 'POTENTIAL_MATCH' },
                        { name: 'Omar Khalid', pos: 'Backend Developer', ats: 45, match: 40, exp: '1y', cat: 'NEEDS_REVIEW' },
                      ].map((c, i) => (
                        <tr key={i}>
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                              <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs font-bold ${avatarColor(c.name)}`}>
                                {initials(c.name)}
                              </div>
                              <div>
                                <div className="ats-cand-name">{c.name}</div>
                              </div>
                            </div>
                          </td>
                          <td style={{ color: '#374151', fontWeight: 500 }}>{c.pos}</td>
                          <td>
                            <span style={{ fontSize: 13, fontWeight: 700, color: c.ats >= 80 ? '#059669' : c.ats >= 60 ? '#4f46e5' : '#d97706' }}>{c.ats}%</span>
                          </td>
                          <td>
                            <div style={{ width: 80 }}><ScoreBar score={c.match} color="#6366f1" /></div>
                          </td>
                          <td style={{ color: '#6b7280' }}>{c.exp}</td>
                          <td><StatusBadge status={c.cat} /></td>
                          <td>
                            <Link to="/candidates">
                              <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#6366f1', padding: 4 }}>
                                <Eye size={14} />
                              </button>
                            </Link>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Bottom padding */}
            <div style={{ height: 24 }} />
          </div>
        </div>
      </div>
    </>
  );
}
