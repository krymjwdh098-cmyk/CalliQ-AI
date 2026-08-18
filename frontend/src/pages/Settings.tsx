import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Users, Webhook, Plus, Trash2, Send, Copy, Check,
  UserCog, Shield, Zap, Eye, EyeOff,
} from 'lucide-react';
import { usersApi, webhooksApi } from '../api';
import { useAuthStore } from '../store/auth';
import { Layout, PageHeader } from '../components/layout/Layout';
import {
  Button, Card, Modal, Input, Select, Badge, EmptyState,
  useToast, Skeleton, Tabs,
} from '../components/ui';
import { formatDate } from '../utils';
import type { TeamUser, WebhookEndpoint } from '../types';

const ROLES = [
  { value: 'admin', label: 'Admin' },
  { value: 'recruiter', label: 'Recruiter' },
  { value: 'viewer', label: 'Viewer' },
];

// ── Team Tab ────────────────────────────────────────────────────────
function InviteUserModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({ name: '', email: '', password: '', role: 'recruiter' });

  const mutation = useMutation({
    mutationFn: () => usersApi.create(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['team'] });
      toast('Team member added', 'success');
      onClose();
      setForm({ name: '', email: '', password: '', role: 'recruiter' });
    },
    onError: (e: any) => toast(e?.response?.data?.detail || 'Failed to add member', 'error'),
  });

  return (
    <Modal open={open} onClose={onClose} title="Add team member">
      <div className="space-y-4">
        <Input label="Full name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
        <Input label="Email" type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
        <Input label="Temporary password" type="text" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} hint="At least 8 characters" />
        <Select label="Role" value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))} options={ROLES} />
        <Button className="w-full justify-center" onClick={() => mutation.mutate()} loading={mutation.isPending}>
          Add member
        </Button>
      </div>
    </Modal>
  );
}

function TeamTab() {
  const { user } = useAuthStore();
  const qc = useQueryClient();
  const toast = useToast();
  const [inviteOpen, setInviteOpen] = useState(false);

  const { data: team = [], isLoading } = useQuery({ queryKey: ['team'], queryFn: usersApi.list });

  const toggleActiveMutation = useMutation({
    mutationFn: (u: TeamUser) => usersApi.update(u.id, { is_active: !u.is_active }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['team'] }); toast('Member updated', 'success'); },
  });

  const roleMutation = useMutation({
    mutationFn: ({ id, role }: { id: number; role: string }) => usersApi.update(id, { role }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['team'] }); toast('Role updated', 'success'); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => usersApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['team'] }); toast('Member removed', 'success'); },
    onError: (e: any) => toast(e?.response?.data?.detail || 'Failed to remove member', 'error'),
  });

  const canManage = user?.role === 'admin' || user?.role === 'owner';

  return (
    <div>
      {canManage && (
        <div className="flex justify-end mb-4">
          <Button icon={<Plus size={14} />} onClick={() => setInviteOpen(true)}>Add member</Button>
        </div>
      )}

      <Card padding={false}>
        {isLoading ? (
          <div className="p-4 space-y-3">{Array(3).fill(0).map((_, i) => <Skeleton key={i} className="h-12" />)}</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {team.map((m: TeamUser) => (
              <div key={m.id} className="flex items-center gap-4 p-4">
                <div className="w-9 h-9 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold flex-shrink-0">
                  {m.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">{m.name}</p>
                  <p className="text-xs text-slate-500 truncate">{m.email}</p>
                </div>
                {canManage && m.role !== 'owner' ? (
                  <Select
                    value={m.role}
                    onChange={e => roleMutation.mutate({ id: m.id, role: e.target.value })}
                    options={ROLES}
                    className="!py-1.5 text-xs w-32"
                  />
                ) : (
                  <Badge className="bg-slate-100 text-slate-600 capitalize">{m.role}</Badge>
                )}
                <Badge className={m.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}>
                  {m.is_active ? 'Active' : 'Disabled'}
                </Badge>
                {canManage && m.role !== 'owner' && (
                  <div className="flex gap-1">
                    <Button variant="ghost" size="sm" onClick={() => toggleActiveMutation.mutate(m)}>
                      {m.is_active ? <EyeOff size={14} /> : <Eye size={14} />}
                    </Button>
                    {m.id !== user?.id && (
                      <Button variant="ghost" size="sm" onClick={() => deleteMutation.mutate(m.id)}>
                        <Trash2 size={14} className="text-red-500" />
                      </Button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      <InviteUserModal open={inviteOpen} onClose={() => setInviteOpen(false)} />
    </div>
  );
}

// ── Webhooks Tab ────────────────────────────────────────────────────
function CreateWebhookModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({ url: '', description: '', events: ['*'] as string[] });
  const [created, setCreated] = useState<{ secret: string } | null>(null);
  const [copied, setCopied] = useState(false);

  const { data: eventsData } = useQuery({ queryKey: ['webhook-events'], queryFn: webhooksApi.listEvents });

  const mutation = useMutation({
    mutationFn: () => webhooksApi.createEndpoint(form),
    onSuccess: (res: any) => {
      qc.invalidateQueries({ queryKey: ['webhooks'] });
      setCreated(res);
      toast('Webhook created', 'success');
    },
    onError: (e: any) => toast(e?.response?.data?.detail || 'Failed to create webhook', 'error'),
  });

  const toggleEvent = (ev: string) => {
    setForm(f => {
      if (ev === '*') return { ...f, events: ['*'] };
      const withoutStar = f.events.filter(e => e !== '*');
      return { ...f, events: withoutStar.includes(ev) ? withoutStar.filter(e => e !== ev) : [...withoutStar, ev] };
    });
  };

  const handleClose = () => {
    setCreated(null);
    setForm({ url: '', description: '', events: ['*'] });
    onClose();
  };

  return (
    <Modal open={open} onClose={handleClose} title="Register webhook" width="max-w-lg">
      {created ? (
        <div className="space-y-4">
          <p className="text-sm text-slate-600">Save this signing secret now — it won't be shown again.</p>
          <div className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg font-mono text-xs break-all">
            <span className="flex-1">{created.secret}</span>
            <button onClick={() => { navigator.clipboard.writeText(created.secret); setCopied(true); setTimeout(() => setCopied(false), 2000); }}>
              {copied ? <Check size={14} className="text-emerald-600" /> : <Copy size={14} className="text-slate-400" />}
            </button>
          </div>
          <Button className="w-full justify-center" onClick={handleClose}>Done</Button>
        </div>
      ) : (
        <div className="space-y-4">
          <Input label="Endpoint URL" value={form.url} onChange={e => setForm(f => ({ ...f, url: e.target.value }))} placeholder="https://your-app.com/webhooks/talentai" />
          <Input label="Description" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="Slack notifications" />
          <div>
            <label className="text-sm font-medium text-slate-700 mb-2 block">Events</label>
            <div className="flex flex-wrap gap-2">
              {(eventsData?.events || ['*']).map(ev => (
                <button
                  key={ev}
                  type="button"
                  onClick={() => toggleEvent(ev)}
                  className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors
                    ${form.events.includes(ev) ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'}`}
                >
                  {ev}
                </button>
              ))}
            </div>
          </div>
          <Button className="w-full justify-center" onClick={() => mutation.mutate()} loading={mutation.isPending} disabled={!form.url}>
            Create webhook
          </Button>
        </div>
      )}
    </Modal>
  );
}

function WebhookDeliveriesModal({ webhook, open, onClose }: { webhook: WebhookEndpoint | null; open: boolean; onClose: () => void }) {
  const { data: deliveries = [] } = useQuery({
    queryKey: ['webhook-deliveries', webhook?.id],
    queryFn: () => webhooksApi.getDeliveries(webhook!.id),
    enabled: !!webhook?.id,
  });

  return (
    <Modal open={open} onClose={onClose} title={`Recent deliveries — ${webhook?.description || webhook?.url}`} width="max-w-2xl">
      {deliveries.length === 0 ? (
        <p className="text-sm text-slate-400 text-center py-8">No deliveries yet.</p>
      ) : (
        <div className="space-y-2">
          {deliveries.map(d => (
            <div key={d.id} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg text-sm">
              <Badge className={d.success ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}>
                {d.status_code || 'Failed'}
              </Badge>
              <span className="flex-1 text-slate-600">{d.event}</span>
              <span className="text-xs text-slate-400">attempt {d.attempt}</span>
              <span className="text-xs text-slate-400">{formatDate(d.created_at)}</span>
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}

function WebhooksTab() {
  const qc = useQueryClient();
  const toast = useToast();
  const [createOpen, setCreateOpen] = useState(false);
  const [deliveriesFor, setDeliveriesFor] = useState<WebhookEndpoint | null>(null);

  const { data: webhooks = [], isLoading } = useQuery({ queryKey: ['webhooks'], queryFn: webhooksApi.listEndpoints });

  const testMutation = useMutation({
    mutationFn: (id: number) => webhooksApi.testEndpoint(id),
    onSuccess: () => toast('Test ping sent', 'success'),
  });

  const toggleMutation = useMutation({
    mutationFn: (w: WebhookEndpoint) => webhooksApi.updateEndpoint(w.id, { is_active: !w.is_active }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['webhooks'] }); toast('Webhook updated', 'success'); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => webhooksApi.deleteEndpoint(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['webhooks'] }); toast('Webhook deleted', 'success'); },
  });

  return (
    <div>
      <div className="flex justify-end mb-4">
        <Button icon={<Plus size={14} />} onClick={() => setCreateOpen(true)}>Register webhook</Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">{Array(2).fill(0).map((_, i) => <Skeleton key={i} className="h-20" />)}</div>
      ) : webhooks.length === 0 ? (
        <EmptyState
          icon={<Webhook size={28} />}
          title="No webhooks yet"
          description="Register an endpoint to receive real-time events like candidate.shortlisted or job.created."
          action={<Button icon={<Plus size={14} />} onClick={() => setCreateOpen(true)}>Register webhook</Button>}
        />
      ) : (
        <div className="space-y-3">
          {webhooks.map(w => (
            <Card key={w.id} className="flex items-center gap-4">
              <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${w.is_active ? 'bg-blue-50 text-blue-600' : 'bg-slate-100 text-slate-400'}`}>
                <Zap size={16} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-800 truncate">{w.description || w.url}</p>
                <p className="text-xs text-slate-500 truncate">{w.url}</p>
                <div className="flex gap-1 mt-1.5 flex-wrap">
                  {w.events.map(e => <Badge key={e} className="bg-slate-100 text-slate-500 text-xs">{e}</Badge>)}
                </div>
              </div>
              <Badge className={w.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}>
                {w.is_active ? 'Active' : 'Disabled'}
              </Badge>
              <div className="flex gap-1 flex-shrink-0">
                <Button variant="ghost" size="sm" onClick={() => setDeliveriesFor(w)}>Logs</Button>
                <Button variant="ghost" size="sm" icon={<Send size={13} />} onClick={() => testMutation.mutate(w.id)} loading={testMutation.isPending} />
                <Button variant="ghost" size="sm" onClick={() => toggleMutation.mutate(w)}>{w.is_active ? 'Disable' : 'Enable'}</Button>
                <Button variant="ghost" size="sm" onClick={() => deleteMutation.mutate(w.id)}><Trash2 size={14} className="text-red-500" /></Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <CreateWebhookModal open={createOpen} onClose={() => setCreateOpen(false)} />
      <WebhookDeliveriesModal webhook={deliveriesFor} open={!!deliveriesFor} onClose={() => setDeliveriesFor(null)} />
    </div>
  );
}

// ── Account Tab ─────────────────────────────────────────────────────
function AccountTab() {
  const { user } = useAuthStore();
  return (
    <Card className="max-w-lg">
      <div className="flex items-center gap-4 mb-6">
        <div className="w-14 h-14 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold text-lg">
          {user?.name?.split(' ').map(n => n[0]).join('').slice(0, 2)}
        </div>
        <div>
          <p className="font-semibold text-slate-800">{user?.name}</p>
          <p className="text-sm text-slate-500">{user?.email}</p>
        </div>
      </div>
      <div className="space-y-3 text-sm">
        <div className="flex justify-between py-2 border-b border-slate-100">
          <span className="text-slate-500">Organization</span>
          <span className="font-medium text-slate-700">{user?.org_name || '—'}</span>
        </div>
        <div className="flex justify-between py-2 border-b border-slate-100">
          <span className="text-slate-500">Role</span>
          <Badge className="bg-blue-100 text-blue-700 capitalize">{user?.role}</Badge>
        </div>
      </div>
    </Card>
  );
}

export function SettingsPage() {
  const [tab, setTab] = useState(0);

  return (
    <Layout>
      <PageHeader title="Settings" subtitle="Manage your team, integrations, and account" />

      <Tabs
        tabs={[
          { label: 'Team', icon: <Users size={14} /> },
          { label: 'Webhooks', icon: <Webhook size={14} /> },
          { label: 'Account', icon: <UserCog size={14} /> },
        ]}
        active={tab}
        onChange={setTab}
      />

      <div className="mt-5">
        {tab === 0 && <TeamTab />}
        {tab === 1 && <WebhooksTab />}
        {tab === 2 && <AccountTab />}
      </div>
    </Layout>
  );
}
