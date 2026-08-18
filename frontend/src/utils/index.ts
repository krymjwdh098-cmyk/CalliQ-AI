import type { CandidateCategory, Recommendation } from '../types';

export const PIPELINE_STAGES = [
  'Under Review', 'Screening', 'Phone Interview', 'Technical',
  'Final Interview', 'Shortlisted', 'Offer Sent', 'Hired',
];

export const TERMINAL_STAGES = ['Rejected', 'Withdrew', 'Ghosted'];

export function getScoreColor(score: number): string {
  if (score >= 80) return 'text-emerald-600';
  if (score >= 60) return 'text-blue-600';
  if (score >= 40) return 'text-amber-600';
  return 'text-slate-500';
}

export function getScoreBg(score: number): string {
  if (score >= 80) return 'bg-emerald-50 text-emerald-700 border-emerald-200';
  if (score >= 60) return 'bg-blue-50 text-blue-700 border-blue-200';
  if (score >= 40) return 'bg-amber-50 text-amber-700 border-amber-200';
  return 'bg-slate-100 text-slate-600 border-slate-200';
}

export function getScoreRingColor(score: number): string {
  if (score >= 80) return '#10b981';
  if (score >= 60) return '#3b82f6';
  if (score >= 40) return '#f59e0b';
  return '#94a3b8';
}

export function getCategoryLabel(cat: CandidateCategory): string {
  const map: Record<CandidateCategory, string> = {
    STRONG_MATCH: 'Strong Match',
    POTENTIAL_MATCH: 'Potential Match',
    WEAK_MATCH: 'Weak Match',
    NEEDS_REVIEW: 'Needs Review',
    KNOCKOUT_FAILED: 'Knockout Failed',
  };
  return map[cat] || cat;
}

export function getCategoryBadge(cat: CandidateCategory): string {
  const map: Record<CandidateCategory, string> = {
    STRONG_MATCH: 'bg-emerald-100 text-emerald-700',
    POTENTIAL_MATCH: 'bg-blue-100 text-blue-700',
    WEAK_MATCH: 'bg-amber-100 text-amber-700',
    NEEDS_REVIEW: 'bg-slate-100 text-slate-600',
    KNOCKOUT_FAILED: 'bg-red-100 text-red-700',
  };
  return map[cat] || 'bg-slate-100 text-slate-600';
}

export function getRecommendationBadge(rec: Recommendation | undefined): string {
  if (!rec) return 'bg-slate-100 text-slate-600';
  const map: Partial<Record<Recommendation, string>> = {
    'Strong Hire': 'bg-emerald-100 text-emerald-700',
    'Hire': 'bg-blue-100 text-blue-700',
    'Consider': 'bg-amber-100 text-amber-700',
    'Reject': 'bg-red-100 text-red-700',
  };
  return map[rec] || 'bg-slate-100 text-slate-600';
}

export function getStatusBadge(status: string): string {
  if (['Hired', 'Shortlisted'].includes(status)) return 'bg-emerald-100 text-emerald-700';
  if (['Rejected', 'Knockout Failed', 'Withdrew', 'Ghosted'].includes(status)) return 'bg-red-100 text-red-700';
  if (['Queued', 'Processing'].includes(status)) return 'bg-blue-100 text-blue-700';
  if (status === 'Duplicate') return 'bg-purple-100 text-purple-700';
  if (status === 'Error') return 'bg-red-100 text-red-700';
  return 'bg-slate-100 text-slate-600';
}

export function initials(name: string): string {
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
}

export function avatarColor(name: string): string {
  const colors = [
    'bg-blue-500', 'bg-purple-500', 'bg-emerald-500', 'bg-amber-500',
    'bg-pink-500', 'bg-indigo-500', 'bg-teal-500', 'bg-orange-500',
  ];
  const idx = name.charCodeAt(0) % colors.length;
  return colors[idx];
}

export function formatDate(dt?: string | null): string {
  if (!dt) return '—';
  return new Date(dt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function formatDateTime(dt?: string | null): string {
  if (!dt) return '—';
  return new Date(dt).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  });
}

export function daysSince(dt?: string | null): number {
  if (!dt) return 0;
  return Math.floor((Date.now() - new Date(dt).getTime()) / 86400000);
}

export function formatSalary(amount?: number, currency = 'EGP'): string {
  if (!amount) return '—';
  return `${amount.toLocaleString()} ${currency}`;
}

export function truncate(str: string, n = 60): string {
  return str.length > n ? str.slice(0, n) + '…' : str;
}
