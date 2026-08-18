import React, { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft, Mail, Phone, MapPin, Linkedin, Github, Globe,
  Briefcase, GraduationCap, Award, Languages as LanguagesIcon,
  CheckCircle, XCircle, Flag, Download, RefreshCw, Send,
  AlertTriangle, Clock, Calendar, DollarSign, MessageSquare,
  ThumbsUp, ThumbsDown, ChevronRight, Sparkles, Target, TrendingUp,
} from 'lucide-react';
import { candidatesApi } from '../api';
import { Layout } from '../components/layout/Layout';
import {
  Button, Badge, Card, Modal, Skeleton, useToast, Select,
  Textarea, Tabs, ScoreRing, ProgressBar, Input,
} from '../components/ui';
import {
  getScoreColor, getCategoryBadge, getCategoryLabel, getStatusBadge,
  getRecommendationBadge, initials, avatarColor, formatDate, formatDateTime,
  formatSalary, PIPELINE_STAGES, TERMINAL_STAGES,
} from '../utils';
import type { Candidate } from '../types';

// ── Score breakdown row ─────────────────────────────────────────────
function ScoreRow({ label, value, weight }: { label: string; value: number; weight?: number }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-slate-600">{label}{weight ? ` (${Math.round(weight * 100)}%)` : ''}</span>
        <span className={`text-xs font-semibold ${getScoreColor(value)}`}>{Math.round(value)}</span>
      </div>
      <ProgressBar value={value} color={value >= 80 ? 'bg-emerald-500' : value >= 60 ? 'bg-blue-500' : value >= 40 ? 'bg-amber-500' : 'bg-slate-400'} />
    </div>
  );
}

// ── Decision Modal ───────────────────────────────────────────────────
function DecisionModal({ candidate, decision, open, onClose }: {
  candidate: Candidate; decision: 'APPROVED' | 'REJECTED'; open: boolean; onClose: () => void;
}) {
  const qc = useQueryClient();
  const toast = useToast();
  const [notes, setNotes] = useState('');

  const mutation = useMutation({
    mutationFn: () => candidatesApi.decide(candidate.id, decision, notes || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['candidate', candidate.id] });
      toast(decision === 'APPROVED' ? 'Candidate shortlisted' : 'Candidate rejected', 'success');
      setNotes('');
      onClose();
    },
    onError: () => toast('Failed to record decision', 'error'),
  });

  return (
    <Modal open={open} onClose={onClose} title={decision === 'APPROVED' ? 'Shortlist candidate' : 'Reject candidate'}>
      <div className="space-y-4">
        <p className="text-sm text-slate-600">
          {decision === 'APPROVED'
            ? `Move ${candidate.full_name} to the shortlist. They'll be notified automatically.`
            : `${candidate.full_name} will be notified their application was not successful.`}
        </p>
        <Textarea
          label="Notes (optional)"
          value={notes}
          onChange={e => setNotes(e.target.value)}
          placeholder="Add context for your team..."
          rows={3}
        />
        <div className="flex gap-3">
          <Button variant="outline" onClick={onClose} className="flex-1 justify-center">Cancel</Button>
          <Button
            variant={decision === 'APPROVED' ? 'primary' : 'danger'}
            onClick={() => mutation.mutate()}
            loading={mutation.isPending}
            className="flex-1 justify-center"
          >
            Confirm
          </Button>
        </div>
      </div>
    </Modal>
  );
}

// ── Schedule Interview Modal ─────────────────────────────────────────
function InterviewModal({ candidate, open, onClose }: { candidate: Candidate; open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({
    scheduled_at: '', interview_type: 'video', location: '', link: '', duration_mins: 60, notes: '',
  });

  const mutation = useMutation({
    mutationFn: () => candidatesApi.scheduleInterview(candidate.id, form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['candidate', candidate.id] });
      toast('Interview scheduled and candidate notified', 'success');
      onClose();
    },
    onError: () => toast('Failed to schedule interview', 'error'),
  });

  return (
    <Modal open={open} onClose={onClose} title="Schedule interview">
      <div className="space-y-4">
        <Input
          label="Date & time"
          type="datetime-local"
          value={form.scheduled_at}
          onChange={e => setForm(f => ({ ...f, scheduled_at: e.target.value }))}
          required
        />
        <Select
          label="Type"
          value={form.interview_type}
          onChange={e => setForm(f => ({ ...f, interview_type: e.target.value }))}
          options={[
            { value: 'video', label: 'Video call' },
            { value: 'phone', label: 'Phone' },
            { value: 'technical', label: 'Technical' },
            { value: 'onsite', label: 'Onsite / Final' },
          ]}
        />
        <Input
          label="Meeting link (optional)"
          value={form.link}
          onChange={e => setForm(f => ({ ...f, link: e.target.value }))}
          placeholder="https://meet.google.com/..."
        />
        <Input
          label="Location (optional)"
          value={form.location}
          onChange={e => setForm(f => ({ ...f, location: e.target.value }))}
          placeholder="Office address"
        />
        <Input
          label="Duration (minutes)"
          type="number"
          value={form.duration_mins}
          onChange={e => setForm(f => ({ ...f, duration_mins: +e.target.value }))}
        />
        <Textarea
          label="Notes"
          value={form.notes}
          onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
          rows={2}
        />
        <Button
          className="w-full justify-center"
          onClick={() => mutation.mutate()}
          loading={mutation.isPending}
          disabled={!form.scheduled_at}
        >
          Schedule & notify candidate
        </Button>
      </div>
    </Modal>
  );
}

// ── Send Offer Modal ──────────────────────────────────────────────────
function OfferModal({ candidate, open, onClose }: { candidate: Candidate; open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({ amount: candidate.salary_expectation || 0, currency: 'EGP', deadline_days: 7, notes: '' });

  const mutation = useMutation({
    mutationFn: () => candidatesApi.sendOffer(candidate.id, form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['candidate', candidate.id] });
      toast('Offer sent to candidate', 'success');
      onClose();
    },
    onError: () => toast('Failed to send offer', 'error'),
  });

  return (
    <Modal open={open} onClose={onClose} title="Send offer">
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Amount"
            type="number"
            value={form.amount}
            onChange={e => setForm(f => ({ ...f, amount: +e.target.value }))}
          />
          <Select
            label="Currency"
            value={form.currency}
            onChange={e => setForm(f => ({ ...f, currency: e.target.value }))}
            options={[{ value: 'EGP', label: 'EGP' }, { value: 'USD', label: 'USD' }, { value: 'EUR', label: 'EUR' }]}
          />
        </div>
        <Input
          label="Response deadline (days)"
          type="number"
          value={form.deadline_days}
          onChange={e => setForm(f => ({ ...f, deadline_days: +e.target.value }))}
        />
        <Textarea
          label="Notes"
          value={form.notes}
          onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
          rows={2}
        />
        <Button
          className="w-full justify-center"
          onClick={() => mutation.mutate()}
          loading={mutation.isPending}
          disabled={!form.amount}
        >
          Send offer & notify candidate
        </Button>
      </div>
    </Modal>
  );
}

// ── Chat Panel ────────────────────────────────────────────────────────
function ChatPanel({ candidate }: { candidate: Candidate }) {
  const qc = useQueryClient();
  const [message, setMessage] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  const mutation = useMutation({
    mutationFn: (msg: string) => candidatesApi.chat(candidate.id, msg),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['candidate', candidate.id] });
      setMessage('');
    },
  });

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [candidate.chat_history.length]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;
    mutation.mutate(message.trim());
  };

  return (
    <Card padding={false} className="flex flex-col h-[520px]">
      <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2">
        <Sparkles size={15} className="text-blue-600" />
        <span className="text-sm font-semibold text-slate-700">Ask the AI about this candidate</span>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
        {candidate.chat_history.length === 0 && (
          <p className="text-sm text-slate-400 text-center py-8">
            Ask things like "What are their strengths?" or "How does their experience match this role?"
          </p>
        )}
        {candidate.chat_history.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${
              m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700'
            }`}>
              {m.content}
            </div>
          </div>
        ))}
        {mutation.isPending && (
          <div className="flex justify-start">
            <div className="bg-slate-100 rounded-xl px-3 py-2 text-sm text-slate-400">Thinking…</div>
          </div>
        )}
      </div>
      <form onSubmit={handleSend} className="p-3 border-t border-slate-100 flex gap-2">
        <input
          value={message}
          onChange={e => setMessage(e.target.value)}
          placeholder="Ask a question..."
          className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <Button type="submit" size="sm" loading={mutation.isPending} disabled={!message.trim()}>
          <Send size={14} />
        </Button>
      </form>
    </Card>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────
export function CandidateDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const toast = useToast();
  const candidateId = Number(id);

  const [tab, setTab] = useState(0);
  const [decisionModal, setDecisionModal] = useState<'APPROVED' | 'REJECTED' | null>(null);
  const [interviewModal, setInterviewModal] = useState(false);
  const [offerModal, setOfferModal] = useState(false);
  const [flagOpen, setFlagOpen] = useState(false);
  const [flagReason, setFlagReason] = useState('');

  const { data: candidate, isLoading } = useQuery({
    queryKey: ['candidate', candidateId],
    queryFn: () => candidatesApi.get(candidateId),
    enabled: !!candidateId,
    refetchInterval: (q) => (['Queued', 'Processing'].includes(q.state.data?.status || '') ? 3000 : false),
  });

  const { data: timeline } = useQuery({
    queryKey: ['candidate-timeline', candidateId],
    queryFn: () => candidatesApi.getTimeline(candidateId),
    enabled: !!candidateId && tab === 2,
  });

  const stageMutation = useMutation({
    mutationFn: (stage: string) => candidatesApi.pipelineMove(candidateId, stage),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['candidate', candidateId] });
      qc.invalidateQueries({ queryKey: ['candidate-timeline', candidateId] });
      toast('Pipeline stage updated', 'success');
    },
  });

  const flagMutation = useMutation({
    mutationFn: () => candidate?.flagged
      ? candidatesApi.unflag(candidateId)
      : candidatesApi.flag(candidateId, flagReason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['candidate', candidateId] });
      toast(candidate?.flagged ? 'Flag removed' : 'Candidate flagged', 'success');
      setFlagOpen(false);
      setFlagReason('');
    },
  });

  const reprocessMutation = useMutation({
    mutationFn: () => candidatesApi.reprocess(candidateId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['candidate', candidateId] });
      toast('Reprocessing started', 'success');
    },
  });

  if (isLoading || !candidate) {
    return (
      <Layout>
        <Skeleton className="h-40 mb-4" />
        <Skeleton className="h-96" />
      </Layout>
    );
  }

  const c = candidate;
  const isProcessing = ['Queued', 'Processing'].includes(c.status);
  const skillEntries = Object.entries(c.technical_skills || {});

  return (
    <Layout>
      {/* Back */}
      <button onClick={() => navigate(-1)} className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-4">
        <ArrowLeft size={14} /> Back
      </button>

      {/* Header card */}
      <Card className="mb-4">
        <div className="flex flex-col md:flex-row gap-6">
          <div className="flex items-start gap-4 flex-1 min-w-0">
            <div className={`w-14 h-14 rounded-full flex items-center justify-center text-white font-bold flex-shrink-0 ${avatarColor(c.full_name)}`}>
              {initials(c.full_name)}
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <h1 className="text-xl font-bold text-slate-800">{c.full_name}</h1>
                {c.is_knocked_out && <Badge className="bg-red-100 text-red-700"><AlertTriangle size={11} className="mr-1" />Knocked out</Badge>}
                {c.flagged && <Badge className="bg-amber-100 text-amber-700"><Flag size={11} className="mr-1" />Flagged</Badge>}
              </div>
              {c.current_position && <p className="text-sm text-slate-500 mb-2">{c.current_position}</p>}
              <div className="flex flex-wrap gap-3 text-sm text-slate-500">
                {c.email && <a href={`mailto:${c.email}`} className="flex items-center gap-1 hover:text-blue-600"><Mail size={13} />{c.email}</a>}
                {c.phone && <a href={`tel:${c.phone}`} className="flex items-center gap-1 hover:text-blue-600"><Phone size={13} />{c.phone}</a>}
                {c.location && <span className="flex items-center gap-1"><MapPin size={13} />{c.location}</span>}
              </div>
              <div className="flex flex-wrap gap-3 mt-2">
                {c.linkedin && <a href={c.linkedin} target="_blank" rel="noreferrer" className="text-slate-400 hover:text-blue-600"><Linkedin size={16} /></a>}
                {c.github && <a href={c.github} target="_blank" rel="noreferrer" className="text-slate-400 hover:text-slate-800"><Github size={16} /></a>}
                {c.portfolio && <a href={c.portfolio} target="_blank" rel="noreferrer" className="text-slate-400 hover:text-blue-600"><Globe size={16} /></a>}
              </div>
            </div>
          </div>

          {/* Score */}
          <div className="flex items-center gap-4 flex-shrink-0">
            {isProcessing ? (
              <div className="flex flex-col items-center gap-1 px-4">
                <div className="w-16 h-16 rounded-full border-4 border-slate-100 border-t-blue-500 animate-spin" />
                <span className="text-xs text-slate-400 mt-1">{c.status}…</span>
              </div>
            ) : (
              <ScoreRing score={c.match_score} size={72} />
            )}
            <div className="flex flex-col gap-1.5">
              <Badge className={getStatusBadge(c.status)}>{c.status}</Badge>
              {c.category && <Badge className={getCategoryBadge(c.category)}>{getCategoryLabel(c.category)}</Badge>}
              {c.recommendation && <Badge className={getRecommendationBadge(c.recommendation)}>{c.recommendation}</Badge>}
            </div>
          </div>
        </div>

        {/* Action bar */}
        <div className="flex flex-wrap gap-2 mt-5 pt-5 border-t border-slate-100">
          <Button size="sm" icon={<ThumbsUp size={14} />} onClick={() => setDecisionModal('APPROVED')} disabled={c.recruiter_decision === 'APPROVED'}>
            Shortlist
          </Button>
          <Button size="sm" variant="danger" icon={<ThumbsDown size={14} />} onClick={() => setDecisionModal('REJECTED')} disabled={c.recruiter_decision === 'REJECTED'}>
            Reject
          </Button>
          <Button size="sm" variant="outline" icon={<Calendar size={14} />} onClick={() => setInterviewModal(true)}>
            Schedule interview
          </Button>
          <Button size="sm" variant="outline" icon={<DollarSign size={14} />} onClick={() => setOfferModal(true)}>
            Send offer
          </Button>
          <Select
            value={c.pipeline_stage || c.status}
            onChange={e => stageMutation.mutate(e.target.value)}
            options={[...PIPELINE_STAGES, ...TERMINAL_STAGES].map(s => ({ value: s, label: s }))}
            className="!py-1.5 text-xs w-40"
          />
          <div className="flex-1" />
          <a href={candidatesApi.downloadCV(c.id)} target="_blank" rel="noreferrer">
            <Button size="sm" variant="ghost" icon={<Download size={14} />}>CV</Button>
          </a>
          <Button size="sm" variant="ghost" icon={<RefreshCw size={14} />} onClick={() => reprocessMutation.mutate()} loading={reprocessMutation.isPending}>
            Reprocess
          </Button>
          <Button size="sm" variant="ghost" icon={<Flag size={14} className={c.flagged ? 'text-amber-500' : ''} />} onClick={() => c.flagged ? flagMutation.mutate() : setFlagOpen(true)}>
            {c.flagged ? 'Unflag' : 'Flag'}
          </Button>
        </div>
      </Card>

      {/* Tabs */}
      <Tabs
        tabs={[
          { label: 'Overview', icon: <Briefcase size={14} /> },
          { label: 'AI Analysis', icon: <Target size={14} /> },
          { label: 'Timeline', icon: <Clock size={14} /> },
          { label: 'Chat', icon: <MessageSquare size={14} /> },
        ]}
        active={tab}
        onChange={setTab}
      />

      <div className="mt-4">
        {/* ── Overview ────────────────────────────────────────────── */}
        {tab === 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2 space-y-4">
              {c.ai_summary && (
                <Card>
                  <h3 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-1.5">
                    <Sparkles size={14} className="text-blue-600" /> AI Summary
                  </h3>
                  <p className="text-sm text-slate-600 leading-relaxed">{c.ai_summary}</p>
                </Card>
              )}

              {c.previous_positions.length > 0 && (
                <Card>
                  <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-1.5">
                    <Briefcase size={14} /> Experience — {c.years_experience} years
                  </h3>
                  <div className="space-y-3">
                    {c.previous_positions.map((p, i) => (
                      <div key={i} className="flex gap-3 pb-3 border-b border-slate-50 last:border-0 last:pb-0">
                        <div className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 flex-shrink-0" />
                        <div>
                          <p className="text-sm font-medium text-slate-700">{p.title}</p>
                          <p className="text-xs text-slate-500">{p.company} {p.start && `· ${p.start} – ${p.end || 'Present'}`}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {c.education.length > 0 && (
                <Card>
                  <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-1.5">
                    <GraduationCap size={14} /> Education
                  </h3>
                  <div className="space-y-3">
                    {c.education.map((e, i) => (
                      <div key={i}>
                        <p className="text-sm font-medium text-slate-700">{e.degree} {e.field && `in ${e.field}`}</p>
                        <p className="text-xs text-slate-500">{e.institution} {e.year && `· ${e.year}`}</p>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {skillEntries.length > 0 && (
                <Card>
                  <h3 className="text-sm font-semibold text-slate-700 mb-3">Skills</h3>
                  <div className="space-y-3">
                    {skillEntries.map(([cat, skills]) => (
                      <div key={cat}>
                        <p className="text-xs text-slate-400 uppercase tracking-wide mb-1.5">{cat}</p>
                        <div className="flex flex-wrap gap-1.5">
                          {skills.map(s => (
                            <span key={s} className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded-lg">{s}</span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {c.certifications.length > 0 && (
                <Card>
                  <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-1.5">
                    <Award size={14} /> Certifications
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {c.certifications.map((cert, i) => (
                      <Badge key={i} className="bg-slate-100 text-slate-600">
                        {cert.name}{cert.year ? ` · ${cert.year}` : ''}
                      </Badge>
                    ))}
                  </div>
                </Card>
              )}
            </div>

            <div className="space-y-4">
              <Card>
                <h3 className="text-sm font-semibold text-slate-700 mb-3">Preferences</h3>
                <div className="space-y-2.5 text-sm">
                  <div className="flex justify-between"><span className="text-slate-500">Salary expectation</span><span className="font-medium text-slate-700">{formatSalary(c.salary_expectation, c.salary_currency)}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Notice period</span><span className="font-medium text-slate-700">{c.notice_period_days != null ? `${c.notice_period_days} days` : '—'}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Availability</span><span className="font-medium text-slate-700">{c.availability_date || '—'}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Remote preference</span><span className="font-medium text-slate-700">{c.remote_preference || '—'}</span></div>
                </div>
              </Card>

              {c.languages.length > 0 && (
                <Card>
                  <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-1.5">
                    <LanguagesIcon size={14} /> Languages
                  </h3>
                  <div className="space-y-1.5">
                    {c.languages.map((l, i) => (
                      <div key={i} className="flex justify-between text-sm">
                        <span className="text-slate-600">{l.language}</span>
                        <span className="text-slate-400 text-xs">{l.level}</span>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              <Card>
                <h3 className="text-sm font-semibold text-slate-700 mb-3">Application</h3>
                <div className="space-y-2.5 text-sm">
                  <div className="flex justify-between"><span className="text-slate-500">Source</span><span className="font-medium text-slate-700 capitalize">{c.source}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Applied</span><span className="font-medium text-slate-700">{formatDate(c.applied_at)}</span></div>
                  {c.job_id && <div className="flex justify-between"><span className="text-slate-500">Job</span><Link to={`/candidates?job_id=${c.job_id}`} className="text-blue-600 hover:underline">View job</Link></div>}
                </div>
              </Card>

              {c.is_knocked_out && c.knockout_flags.length > 0 && (
                <Card className="border-red-200 bg-red-50">
                  <h3 className="text-sm font-semibold text-red-700 mb-2 flex items-center gap-1.5">
                    <AlertTriangle size={14} /> Knockout reasons
                  </h3>
                  <ul className="space-y-1 text-sm text-red-700">
                    {c.knockout_flags.map((f, i) => <li key={i}>· {f}</li>)}
                  </ul>
                </Card>
              )}
            </div>
          </div>
        )}

        {/* ── AI Analysis ─────────────────────────────────────────── */}
        {tab === 1 && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2 space-y-4">
              <Card>
                <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-1.5">
                  <TrendingUp size={14} /> Score breakdown
                </h3>
                <div className="space-y-3">
                  <ScoreRow label="Skill match" value={c.skill_match} weight={0.35} />
                  <ScoreRow label="Experience match" value={c.experience_match} weight={0.25} />
                  <ScoreRow label="Education match" value={c.education_match} weight={0.15} />
                  <ScoreRow label="Seniority match" value={c.seniority_match} weight={0.1} />
                  <ScoreRow label="Keyword match" value={c.keyword_match} weight={0.1} />
                  <ScoreRow label="Location match" value={c.location_match} weight={0.05} />
                </div>
                <div className="grid grid-cols-2 gap-3 mt-4 pt-4 border-t border-slate-100">
                  <div className="text-center bg-slate-50 rounded-lg py-3">
                    <p className="text-lg font-bold text-slate-800">{Math.round(c.ats_score)}</p>
                    <p className="text-xs text-slate-500">ATS Score</p>
                  </div>
                  <div className="text-center bg-slate-50 rounded-lg py-3">
                    <p className="text-lg font-bold text-slate-800">{Math.round(c.ai_confidence)}%</p>
                    <p className="text-xs text-slate-500">AI Confidence</p>
                  </div>
                </div>
              </Card>

              {c.recommendation_reason && (
                <Card>
                  <h3 className="text-sm font-semibold text-slate-700 mb-2">Recommendation rationale</h3>
                  <p className="text-sm text-slate-600 leading-relaxed">{c.recommendation_reason}</p>
                </Card>
              )}

              <div className="grid grid-cols-2 gap-4">
                {c.strengths.length > 0 && (
                  <Card>
                    <h3 className="text-sm font-semibold text-emerald-700 mb-2">Strengths</h3>
                    <ul className="space-y-1.5 text-sm text-slate-600">
                      {c.strengths.map((s, i) => <li key={i} className="flex gap-1.5"><CheckCircle size={13} className="text-emerald-500 flex-shrink-0 mt-0.5" />{s}</li>)}
                    </ul>
                  </Card>
                )}
                {c.weaknesses.length > 0 && (
                  <Card>
                    <h3 className="text-sm font-semibold text-red-700 mb-2">Weaknesses</h3>
                    <ul className="space-y-1.5 text-sm text-slate-600">
                      {c.weaknesses.map((s, i) => <li key={i} className="flex gap-1.5"><XCircle size={13} className="text-red-400 flex-shrink-0 mt-0.5" />{s}</li>)}
                    </ul>
                  </Card>
                )}
              </div>

              {c.skill_gap_analysis && (
                <Card>
                  <h3 className="text-sm font-semibold text-slate-700 mb-2">Skill gap analysis</h3>
                  <p className="text-sm text-slate-600 leading-relaxed">{c.skill_gap_analysis}</p>
                </Card>
              )}
            </div>

            <div className="space-y-4">
              {c.missing_skills.length > 0 && (
                <Card>
                  <h3 className="text-sm font-semibold text-slate-700 mb-2">Missing skills</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {c.missing_skills.map(s => <Badge key={s} className="bg-red-50 text-red-600">{s}</Badge>)}
                  </div>
                </Card>
              )}
              {c.missing_certs.length > 0 && (
                <Card>
                  <h3 className="text-sm font-semibold text-slate-700 mb-2">Missing certifications</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {c.missing_certs.map(s => <Badge key={s} className="bg-amber-50 text-amber-700">{s}</Badge>)}
                  </div>
                </Card>
              )}
              {c.ats_issues.length > 0 && (
                <Card>
                  <h3 className="text-sm font-semibold text-slate-700 mb-2">ATS issues</h3>
                  <ul className="space-y-1 text-sm text-slate-600">
                    {c.ats_issues.map((s, i) => <li key={i}>· {s}</li>)}
                  </ul>
                </Card>
              )}
              {c.ats_suggestions.length > 0 && (
                <Card>
                  <h3 className="text-sm font-semibold text-slate-700 mb-2">ATS suggestions</h3>
                  <ul className="space-y-1 text-sm text-slate-600">
                    {c.ats_suggestions.map((s, i) => <li key={i}>· {s}</li>)}
                  </ul>
                </Card>
              )}
            </div>
          </div>
        )}

        {/* ── Timeline ─────────────────────────────────────────────── */}
        {tab === 2 && (
          <Card>
            <h3 className="text-sm font-semibold text-slate-700 mb-4">Activity timeline</h3>
            {!timeline ? (
              <Skeleton className="h-40" />
            ) : timeline.timeline.length === 0 ? (
              <p className="text-sm text-slate-400 text-center py-8">No activity recorded yet.</p>
            ) : (
              <div className="space-y-0">
                {timeline.timeline.map((ev, i) => (
                  <div key={i} className="flex gap-3 pb-4 last:pb-0">
                    <div className="flex flex-col items-center">
                      <div className="w-2.5 h-2.5 rounded-full bg-blue-500 flex-shrink-0 mt-1" />
                      {i < timeline.timeline.length - 1 && <div className="w-px flex-1 bg-slate-200 mt-1" />}
                    </div>
                    <div className="pb-1">
                      <p className="text-sm font-medium text-slate-700">{ev.label}</p>
                      <p className="text-xs text-slate-400">{formatDateTime(ev.at)} {ev.by && `· ${ev.by}`}</p>
                      {ev.notes && <p className="text-xs text-slate-500 mt-0.5">{ev.notes}</p>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        )}

        {/* ── Chat ─────────────────────────────────────────────────── */}
        {tab === 3 && <ChatPanel candidate={c} />}
      </div>

      {/* Modals */}
      {decisionModal && (
        <DecisionModal candidate={c} decision={decisionModal} open={!!decisionModal} onClose={() => setDecisionModal(null)} />
      )}
      <InterviewModal candidate={c} open={interviewModal} onClose={() => setInterviewModal(false)} />
      <OfferModal candidate={c} open={offerModal} onClose={() => setOfferModal(false)} />

      <Modal open={flagOpen} onClose={() => setFlagOpen(false)} title="Flag candidate">
        <div className="space-y-4">
          <Textarea
            label="Reason"
            value={flagReason}
            onChange={e => setFlagReason(e.target.value)}
            placeholder="Why is this candidate being flagged?"
            rows={3}
          />
          <Button
            className="w-full justify-center"
            onClick={() => flagMutation.mutate()}
            loading={flagMutation.isPending}
            disabled={!flagReason.trim()}
          >
            Flag candidate
          </Button>
        </div>
      </Modal>
    </Layout>
  );
}
