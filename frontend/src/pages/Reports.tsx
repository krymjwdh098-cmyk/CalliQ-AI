import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { Clock, TrendingUp, ListChecks, Shield } from 'lucide-react';
import { dashboardApi } from '../api';
import { useAuthStore } from '../store/auth';
import { Layout, PageHeader } from '../components/layout/Layout';
import { Card, Skeleton, Badge, Select, EmptyState } from '../components/ui';
import { formatDate } from '../utils';

export function ReportsPage() {
  const { user } = useAuthStore();
  const [daysBack, setDaysBack] = useState(90);
  const isAdmin = user?.role === 'admin' || user?.role === 'owner';

  const { data: timeToHire, isLoading: t2hLoading } = useQuery({
    queryKey: ['time-to-hire', daysBack],
    queryFn: () => dashboardApi.timeToHire(daysBack),
  });

  const { data: pipeline, isLoading: pipelineLoading } = useQuery({
    queryKey: ['pipeline-analytics'],
    queryFn: dashboardApi.pipelineAnalytics,
  });

  const { data: auditLog } = useQuery({
    queryKey: ['audit-log'],
    queryFn: () => dashboardApi.auditLog({ page: 1, page_size: 20 }),
    enabled: isAdmin,
  });

  const byJobChart = (timeToHire?.by_job || []).map(j => ({ name: j.job_title, days: j.avg_days }));

  return (
    <Layout>
      <PageHeader
        title="Reports"
        subtitle="Hiring performance, source quality, and pipeline analytics"
        actions={
          <Select
            value={String(daysBack)}
            onChange={e => setDaysBack(Number(e.target.value))}
            options={[
              { value: '30', label: 'Last 30 days' },
              { value: '90', label: 'Last 90 days' },
              { value: '180', label: 'Last 6 months' },
              { value: '365', label: 'Last year' },
            ]}
          />
        }
      />

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        <Card className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center"><Clock size={18} /></div>
          <div>
            <p className="text-xl font-bold text-slate-800">{timeToHire?.overall_avg_days ?? '—'}</p>
            <p className="text-xs text-slate-500">Avg days to hire</p>
          </div>
        </Card>
        <Card className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center"><ListChecks size={18} /></div>
          <div>
            <p className="text-xl font-bold text-slate-800">{timeToHire?.total_hired ?? 0}</p>
            <p className="text-xs text-slate-500">Total hired</p>
          </div>
        </Card>
        <Card className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center"><TrendingUp size={18} /></div>
          <div>
            <p className="text-xl font-bold text-slate-800">{pipeline?.offer_stats.acceptance_rate_pct ?? 0}%</p>
            <p className="text-xs text-slate-500">Offer acceptance</p>
          </div>
        </Card>
        <Card className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center"><TrendingUp size={18} /></div>
          <div>
            <p className="text-xl font-bold text-slate-800">{(pipeline?.funnel as any)?.conversion_rate ?? 0}%</p>
            <p className="text-xs text-slate-500">Overall conversion</p>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        {/* Time to hire by job */}
        <Card>
          <h3 className="text-sm font-semibold text-slate-700 mb-4">Time to hire by job</h3>
          {t2hLoading ? (
            <Skeleton className="h-56" />
          ) : byJobChart.length === 0 ? (
            <EmptyState icon={<Clock size={24} />} title="No hires yet" description="This report fills in once candidates are marked Hired." />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={byJobChart} layout="vertical" margin={{ left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis dataKey="name" type="category" width={110} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="days" fill="#3b82f6" radius={[0, 4, 4, 0]} name="Avg days" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Source quality */}
        <Card>
          <h3 className="text-sm font-semibold text-slate-700 mb-4">Source quality</h3>
          {pipelineLoading ? (
            <Skeleton className="h-56" />
          ) : (
            <div className="space-y-3">
              {Object.entries(pipeline?.source_quality || {}).map(([source, data]) => (
                <div key={source} className="border-b border-slate-50 pb-3 last:border-0">
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-sm font-medium text-slate-700 capitalize">{source}</span>
                    <span className="text-xs text-slate-400">{data.total} applied</span>
                  </div>
                  <div className="flex gap-4 text-xs">
                    <span className="text-blue-600">{data.shortlist_rate}% shortlisted</span>
                    <span className="text-emerald-600">{data.hire_rate}% hired</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Funnel + Stage durations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <Card>
          <h3 className="text-sm font-semibold text-slate-700 mb-4">Conversion funnel</h3>
          <div className="space-y-2">
            {Object.entries(pipeline?.funnel || {}).filter(([k]) => k !== 'conversion_rate').map(([stage, data]: [string, any]) => (
              <div key={stage} className="flex items-center gap-3">
                <span className="text-xs text-slate-500 w-32 truncate">{stage}</span>
                <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 rounded-full" style={{ width: `${data.pct_of_total}%` }} />
                </div>
                <span className="text-xs text-slate-600 w-16 text-right">{data.count} ({data.pct_of_total}%)</span>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <h3 className="text-sm font-semibold text-slate-700 mb-4">Avg days per stage</h3>
          <div className="space-y-2">
            {Object.entries(pipeline?.avg_stage_days || {}).map(([stage, days]) => (
              <div key={stage} className="flex justify-between text-sm">
                <span className="text-slate-600">{stage}</span>
                <span className="font-medium text-slate-800">{days} days</span>
              </div>
            ))}
            {Object.keys(pipeline?.avg_stage_days || {}).length === 0 && (
              <p className="text-sm text-slate-400 text-center py-6">Not enough pipeline history yet.</p>
            )}
          </div>
        </Card>
      </div>

      {/* Audit log — admin only */}
      {isAdmin && (
        <Card padding={false}>
          <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
            <Shield size={15} className="text-slate-500" />
            <h3 className="text-sm font-semibold text-slate-700">Recent activity (audit log)</h3>
          </div>
          {!auditLog?.items?.length ? (
            <p className="text-sm text-slate-400 text-center py-8">No activity recorded yet.</p>
          ) : (
            <div className="divide-y divide-slate-50">
              {auditLog.items.map((e: any) => (
                <div key={e.id} className="flex items-center gap-3 px-5 py-3 text-sm">
                  <Badge className="bg-slate-100 text-slate-600 text-xs">{e.action}</Badge>
                  <span className="text-slate-500 flex-1">
                    {e.entity_type} #{e.entity_id}{e.notes ? ` — ${e.notes}` : ''}
                  </span>
                  <span className="text-xs text-slate-400">{formatDate(e.created_at)}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </Layout>
  );
}
