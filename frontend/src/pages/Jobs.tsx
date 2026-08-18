import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Plus, Users, Link2, QrCode, Power, Trash2, ChevronRight,
  Briefcase, AlertTriangle, Copy, Check, ExternalLink, Shield,
} from 'lucide-react';
import { jobsApi } from '../api';
import { useAuthStore } from '../store/auth';
import { useToast, Button, Card, Modal, Input, Textarea, TagInput, Badge, EmptyState, Skeleton, Select } from '../components/ui';
import { Layout, PageHeader } from '../components/layout/Layout';
import type { Job, KnockoutRule, JobCreate } from '../types';
import { formatDate } from '../utils';

function JobCard({ job, onManage }: { job: Job; onManage: (j: Job) => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [copied, setCopied] = useState(false);
  const [showQR, setShowQR] = useState(false);
  const [qrData, setQrData] = useState<{ qr_base64: string; apply_url: string } | null>(null);

  const toggleMutation = useMutation({
    mutationFn: () => jobsApi.toggleActive(job.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['jobs'] }); toast(`Job ${job.is_active ? 'deactivated' : 'activated'}`, 'success'); },
  });

  const copyLink = () => {
    navigator.clipboard.writeText(job.apply_url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast('Apply link copied!', 'success');
  };

  const handleQR = async () => {
    if (!qrData) {
      const data = await jobsApi.getQR(job.id);
      setQrData(data);
    }
    setShowQR(true);
  };

  return (
    <Card padding={false} className="overflow-hidden hover:shadow-md transition-shadow">
      <div className="p-4">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-semibold text-slate-800 truncate">{job.title}</h3>
              <span className={`flex-shrink-0 text-xs px-2 py-0.5 rounded-full font-medium ${job.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                {job.is_active ? 'Active' : 'Closed'}
              </span>
            </div>
            {job.company && <p className="text-sm text-slate-500">{job.company}</p>}
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs text-slate-500 mb-4">
          <span className="flex items-center gap-1"><Users size={12} />{job.candidate_count} candidates</span>
          {job.location_req && <span>{job.location_req}</span>}
          {job.min_experience > 0 && <span>{job.min_experience}+ yrs</span>}
          <span>{formatDate(job.created_at)}</span>
        </div>

        {job.required_skills.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-4">
            {job.required_skills.slice(0, 5).map(s => (
              <span key={s} className="px-1.5 py-0.5 bg-slate-100 text-slate-600 text-xs rounded">{s}</span>
            ))}
            {job.required_skills.length > 5 && (
              <span className="px-1.5 py-0.5 text-slate-400 text-xs">+{job.required_skills.length - 5}</span>
            )}
          </div>
        )}

        <div className="flex items-center gap-2 flex-wrap">
          <Link to={`/candidates?job_id=${job.id}`}>
            <Button variant="primary" size="sm" icon={<Users size={13} />}>
              Candidates
            </Button>
          </Link>
          <Button variant="outline" size="sm" icon={copied ? <Check size={13} /> : <Copy size={13} />} onClick={copyLink}>
            {copied ? 'Copied!' : 'Copy Link'}
          </Button>
          <Button variant="outline" size="sm" icon={<QrCode size={13} />} onClick={handleQR}>QR</Button>
          <Button variant="outline" size="sm" icon={<Shield size={13} />} onClick={() => onManage(job)}>Rules</Button>
          <Button
            variant="ghost" size="sm"
            icon={<Power size={13} className={job.is_active ? 'text-amber-500' : 'text-emerald-500'} />}
            onClick={() => toggleMutation.mutate()}
            loading={toggleMutation.isPending}
          />
        </div>
      </div>

      {/* QR Modal */}
      <Modal open={showQR} onClose={() => setShowQR(false)} title="QR Code — Apply Link">
        {qrData && (
          <div className="flex flex-col items-center gap-4">
            <img src={`data:image/png;base64,${qrData.qr_base64}`} alt="QR Code" className="w-48 h-48" />
            <div className="w-full p-3 bg-slate-50 rounded-lg flex items-center gap-2 text-sm text-slate-600">
              <span className="truncate flex-1">{qrData.apply_url}</span>
              <a href={qrData.apply_url} target="_blank" rel="noreferrer"><ExternalLink size={14} /></a>
            </div>
          </div>
        )}
      </Modal>
    </Card>
  );
}

function CreateJobModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState<JobCreate>({
    title: '', company: '', description: '', required_skills: [], nice_to_have: [],
    min_experience: 0,
  });

  const mutation = useMutation({
    mutationFn: () => jobsApi.create(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['jobs'] });
      toast('Job created!', 'success');
      onClose();
    },
    onError: () => toast('Failed to create job', 'error'),
  });

  const set = (k: keyof JobCreate, v: unknown) => setForm(f => ({ ...f, [k]: v }));

  return (
    <Modal open={open} onClose={onClose} title="Create New Job" width="max-w-2xl">
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <Input label="Job Title *" value={form.title} onChange={e => set('title', e.target.value)} placeholder="e.g. Senior Python Developer" />
          <Input label="Company" value={form.company || ''} onChange={e => set('company', e.target.value)} placeholder="Acme Corp" />
        </div>
        <Textarea label="Job Description *" value={form.description} onChange={e => set('description', e.target.value)} rows={5} placeholder="Describe the role, responsibilities, and requirements..." />
        <TagInput label="Required Skills" tags={form.required_skills} onChange={v => set('required_skills', v)} placeholder="Python, FastAPI... press Enter" />
        <TagInput label="Nice to Have" tags={form.nice_to_have} onChange={v => set('nice_to_have', v)} placeholder="Docker, Kubernetes..." />
        <div className="grid grid-cols-3 gap-4">
          <Input label="Min Experience (years)" type="number" min={0} value={form.min_experience} onChange={e => set('min_experience', +e.target.value)} />
          <Input label="Location" value={form.location_req || ''} onChange={e => set('location_req', e.target.value)} placeholder="Cairo, Egypt" />
          <Input label="Education Req." value={form.education_req || ''} onChange={e => set('education_req', e.target.value)} placeholder="Bachelor's degree" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Input label="Salary Min" type="number" value={form.salary_min || ''} onChange={e => set('salary_min', +e.target.value)} placeholder="10000" />
          <Input label="Salary Max" type="number" value={form.salary_max || ''} onChange={e => set('salary_max', +e.target.value)} placeholder="20000" />
        </div>
        <Input label="HR Email (notifications)" type="email" value={form.hr_email || ''} onChange={e => set('hr_email', e.target.value)} />
        <div className="flex gap-3 pt-2">
          <Button variant="outline" onClick={onClose} className="flex-1 justify-center">Cancel</Button>
          <Button onClick={() => mutation.mutate()} loading={mutation.isPending} className="flex-1 justify-center">
            Create Job
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function KnockoutRulesModal({ job, open, onClose }: { job: Job | null; open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({ rule_type: 'experience', description: '', value: '', action: 'flag' });

  const { data: rules = [] } = useQuery({
    queryKey: ['knockout-rules', job?.id],
    queryFn: () => jobsApi.listKnockoutRules(job!.id),
    enabled: !!job?.id,
  });

  const addMutation = useMutation({
    mutationFn: () => jobsApi.addKnockoutRule(job!.id, { ...form, is_mandatory: true }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['knockout-rules', job?.id] }); toast('Rule added', 'success'); setForm({ rule_type: 'experience', description: '', value: '', action: 'flag' }); },
  });

  const delMutation = useMutation({
    mutationFn: (ruleId: number) => jobsApi.deleteKnockoutRule(job!.id, ruleId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['knockout-rules', job?.id] }); toast('Rule deleted', 'success'); },
  });

  return (
    <Modal open={open} onClose={onClose} title={`Knockout Rules — ${job?.title}`} width="max-w-2xl">
      <div className="space-y-4">
        {/* Existing rules */}
        <div className="space-y-2">
          {rules.map((rule: KnockoutRule) => (
            <div key={rule.id} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-700">{rule.description}</p>
                <div className="flex gap-2 mt-1">
                  <Badge className="bg-slate-200 text-slate-600 text-xs">{rule.rule_type}</Badge>
                  {rule.value && <Badge className="bg-blue-100 text-blue-700 text-xs">{rule.value}</Badge>}
                  <Badge className={`text-xs ${rule.action === 'auto_reject' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>
                    {rule.action}
                  </Badge>
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={() => delMutation.mutate(rule.id)} loading={delMutation.isPending}>
                <Trash2 size={14} className="text-red-500" />
              </Button>
            </div>
          ))}
          {rules.length === 0 && <p className="text-sm text-slate-500 text-center py-4">No rules yet. Add one below.</p>}
        </div>

        {/* Add rule */}
        <div className="border-t pt-4">
          <p className="text-sm font-medium text-slate-700 mb-3">Add Rule</p>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <Select
              label="Type" value={form.rule_type}
              onChange={e => setForm(f => ({ ...f, rule_type: e.target.value }))}
              options={[
                { value: 'experience', label: 'Experience' },
                { value: 'location', label: 'Location' },
                { value: 'education', label: 'Education' },
                { value: 'language', label: 'Language' },
                { value: 'skill', label: 'Required Skill' },
              ]}
            />
            <Select
              label="Action" value={form.action}
              onChange={e => setForm(f => ({ ...f, action: e.target.value }))}
              options={[
                { value: 'flag', label: 'Flag for Review' },
                { value: 'auto_reject', label: 'Auto Reject' },
              ]}
            />
          </div>
          <Input label="Description" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="Must have 3+ years experience" className="mb-3" />
          <Input label="Value / Threshold" value={form.value} onChange={e => setForm(f => ({ ...f, value: e.target.value }))} placeholder="3 (for experience) | Cairo (for location)" className="mb-3" />
          <Button onClick={() => addMutation.mutate()} loading={addMutation.isPending} icon={<Plus size={14} />}>
            Add Rule
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export function JobsPage() {
  const { user } = useAuthStore();
  const [createOpen, setCreateOpen] = useState(false);
  const [rulesJob, setRulesJob] = useState<Job | null>(null);

  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => jobsApi.list(),
  });

  const canCreate = user?.role !== 'viewer';

  return (
    <Layout>
      <PageHeader
        title="Jobs"
        subtitle={`${jobs.length} jobs total`}
        actions={
          canCreate && (
            <Button icon={<Plus size={16} />} onClick={() => setCreateOpen(true)}>New Job</Button>
          )
        }
      />

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array(6).fill(0).map((_, i) => <Skeleton key={i} className="h-52" />)}
        </div>
      ) : jobs.length === 0 ? (
        <EmptyState
          icon={<Briefcase size={32} />}
          title="No jobs yet"
          description="Create your first job to start receiving applications and matching candidates with AI."
          action={canCreate && <Button icon={<Plus size={14} />} onClick={() => setCreateOpen(true)}>Create first job</Button>}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {jobs.map(job => (
            <JobCard key={job.id} job={job} onManage={j => setRulesJob(j)} />
          ))}
        </div>
      )}

      <CreateJobModal open={createOpen} onClose={() => setCreateOpen(false)} />
      <KnockoutRulesModal job={rulesJob} open={!!rulesJob} onClose={() => setRulesJob(null)} />
    </Layout>
  );
}
