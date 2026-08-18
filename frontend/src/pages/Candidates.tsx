import React, { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import {
  Upload, Search, Filter, ChevronRight, Users, AlertTriangle,
  CheckCircle, XCircle, Clock, MoreHorizontal, RefreshCw,
} from 'lucide-react';
import { candidatesApi, jobsApi } from '../api';
import { Button, Badge, Card, Modal, Skeleton, EmptyState, useToast, Select, Spinner } from '../components/ui';
import { Layout, PageHeader } from '../components/layout/Layout';
import { ScoreRing } from '../components/ui';
import {
  getScoreBg, getCategoryBadge, getCategoryLabel, getStatusBadge,
  initials, avatarColor, daysSince, formatDate,
} from '../utils';
import type { Candidate } from '../types';
import { useAuthStore } from '../store/auth';

const PIPELINE_STAGES = [
  'Under Review', 'Screening', 'Phone Interview', 'Technical',
  'Final Interview', 'Shortlisted', 'Offer Sent', 'Hired',
  'Rejected', 'Withdrew', 'Ghosted',
];

function CandidateRow({ candidate }: { candidate: Candidate }) {
  const days = daysSince(candidate.applied_at);
  const isProcessing = ['Queued', 'Processing'].includes(candidate.status);

  return (
    <Link
      to={`/candidates/${candidate.id}`}
      className="flex items-center gap-4 p-4 hover:bg-slate-50 transition-colors border-b border-slate-100 last:border-0"
    >
      {/* Avatar */}
      <div className={`w-9 h-9 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0 ${avatarColor(candidate.full_name)}`}>
        {initials(candidate.full_name)}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="font-medium text-slate-800 text-sm truncate">{candidate.full_name}</span>
          {candidate.is_knocked_out && <AlertTriangle size={13} className="text-red-500 flex-shrink-0" />}
          {candidate.flagged && <span className="text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded">Flagged</span>}
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-500">
          {candidate.current_position && <span className="truncate max-w-32">{candidate.current_position}</span>}
          {candidate.years_experience > 0 && <span>{candidate.years_experience}y exp</span>}
          {candidate.location && <span>{candidate.location}</span>}
        </div>
      </div>

      {/* Score */}
      <div className="flex-shrink-0 text-center">
        {isProcessing ? (
          <div className="flex flex-col items-center gap-1">
            <Spinner size={16} />
            <span className="text-xs text-slate-400">{candidate.status}</span>
          </div>
        ) : (
          <ScoreRing score={candidate.match_score} size={48} />
        )}
      </div>

      {/* Status */}
      <div className="flex-shrink-0 hidden sm:flex flex-col items-end gap-1">
        <Badge className={getStatusBadge(candidate.status)}>{candidate.status}</Badge>
        {candidate.category && (
          <Badge className={`${getCategoryBadge(candidate.category)} text-xs`}>
            {getCategoryLabel(candidate.category)}
          </Badge>
        )}
        {days > 7 && <span className="text-xs text-amber-600">{days}d in pipeline</span>}
      </div>

      <ChevronRight size={16} className="text-slate-300 flex-shrink-0" />
    </Link>
  );
}

function BulkUploadModal({ open, onClose, jobId }: { open: boolean; onClose: () => void; jobId?: number }) {
  const toast = useToast();
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{ queued: number; rejected_files: number } | null>(null);

  const onDrop = useCallback((accepted: File[]) => {
    setFiles(f => [...f, ...accepted].slice(0, 100));
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { 'application/pdf': ['.pdf'], 'application/msword': ['.doc'], 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'] },
  });

  const handleUpload = async () => {
    if (files.length === 0) return;
    setUploading(true);
    try {
      const fd = new FormData();
      files.forEach(f => fd.append('files', f));
      if (jobId) fd.append('job_id', String(jobId));
      const res = await candidatesApi.bulkUpload(fd);
      setResult(res);
      toast(`${res.queued} CVs queued for processing`, 'success');
    } catch {
      toast('Upload failed', 'error');
    } finally {
      setUploading(false);
    }
  };

  const handleClose = () => { setFiles([]); setResult(null); onClose(); };

  return (
    <Modal open={open} onClose={handleClose} title="Bulk Upload CVs" width="max-w-lg">
      {result ? (
        <div className="text-center py-6">
          <CheckCircle size={40} className="text-emerald-500 mx-auto mb-3" />
          <p className="text-lg font-semibold text-slate-800 mb-1">{result.queued} CVs queued</p>
          <p className="text-sm text-slate-500">{result.rejected_files} files rejected</p>
          <Button className="mt-4" onClick={handleClose}>Done</Button>
        </div>
      ) : (
        <div className="space-y-4">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors
              ${isDragActive ? 'border-blue-400 bg-blue-50' : 'border-slate-200 hover:border-blue-300 hover:bg-slate-50'}`}
          >
            <input {...getInputProps()} />
            <Upload size={28} className="mx-auto text-slate-400 mb-2" />
            <p className="text-sm font-medium text-slate-600">{isDragActive ? 'Drop files here' : 'Drag & drop CVs here'}</p>
            <p className="text-xs text-slate-400 mt-1">PDF, DOC, DOCX — up to 100 files</p>
          </div>

          {files.length > 0 && (
            <div className="max-h-40 overflow-y-auto space-y-1">
              {files.map((f, i) => (
                <div key={i} className="flex items-center gap-2 text-sm text-slate-600 bg-slate-50 px-3 py-1.5 rounded-lg">
                  <span className="flex-1 truncate">{f.name}</span>
                  <span className="text-xs text-slate-400">{(f.size / 1024).toFixed(0)}KB</span>
                  <button onClick={() => setFiles(files.filter((_, j) => j !== i))}>
                    <XCircle size={14} className="text-slate-400 hover:text-red-500" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="flex gap-3">
            <Button variant="outline" onClick={handleClose} className="flex-1 justify-center">Cancel</Button>
            <Button onClick={handleUpload} loading={uploading} className="flex-1 justify-center" disabled={files.length === 0}>
              Upload {files.length > 0 ? `${files.length} files` : ''}
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}

export function CandidatesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState('');
  const [bulkOpen, setBulkOpen] = useState(false);
  const { user } = useAuthStore();

  const page = Number(searchParams.get('page') || 1);
  const jobId = searchParams.get('job_id') ? Number(searchParams.get('job_id')) : undefined;
  const status = searchParams.get('status') || undefined;
  const minScore = searchParams.get('min_score') ? Number(searchParams.get('min_score')) : undefined;

  const { data: jobs } = useQuery({ queryKey: ['jobs'], queryFn: () => jobsApi.list() });

  const { data, isLoading } = useQuery({
    queryKey: ['candidates', { page, jobId, status, minScore, search }],
    queryFn: () => candidatesApi.list({ page, page_size: 20, job_id: jobId, status, min_score: minScore, search: search || undefined }),
  });

  const setParam = (key: string, val: string | null) => {
    const p = new URLSearchParams(searchParams);
    if (val) p.set(key, val); else p.delete(key);
    p.delete('page');
    setSearchParams(p);
  };

  return (
    <Layout>
      <PageHeader
        title="Candidates"
        subtitle={data ? `${data.total} total` : ''}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" icon={<Upload size={14} />} onClick={() => setBulkOpen(true)}>Bulk Upload</Button>
          </div>
        }
      />

      {/* Filters */}
      <Card className="mb-4 p-4">
        <div className="flex flex-wrap gap-3">
          <div className="relative flex-1 min-w-40">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search by name, email..."
              className="w-full pl-9 pr-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <select
            value={jobId || ''}
            onChange={e => setParam('job_id', e.target.value || null)}
            className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="">All Jobs</option>
            {jobs?.map(j => <option key={j.id} value={j.id}>{j.title}</option>)}
          </select>
          <select
            value={status || ''}
            onChange={e => setParam('status', e.target.value || null)}
            className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="">All Stages</option>
            {PIPELINE_STAGES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select
            value={minScore || ''}
            onChange={e => setParam('min_score', e.target.value || null)}
            className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="">Any Score</option>
            <option value="80">80+ Strong Match</option>
            <option value="60">60+ Potential</option>
            <option value="40">40+ Weak Match</option>
          </select>
        </div>
      </Card>

      {/* Candidate list */}
      <Card padding={false} className="overflow-hidden">
        {isLoading ? (
          <div className="divide-y divide-slate-100">
            {Array(8).fill(0).map((_, i) => (
              <div key={i} className="flex items-center gap-4 p-4">
                <Skeleton className="w-9 h-9 rounded-full flex-shrink-0" />
                <Skeleton className="flex-1 h-10" />
                <Skeleton className="w-12 h-12 rounded-full flex-shrink-0" />
              </div>
            ))}
          </div>
        ) : !data?.items.length ? (
          <EmptyState
            icon={<Users size={32} />}
            title="No candidates found"
            description="Try adjusting your filters or upload some CVs to get started."
          />
        ) : (
          <>
            <div className="divide-y divide-slate-50">
              {data.items.map(c => <CandidateRow key={c.id} candidate={c} />)}
            </div>
            {/* Pagination */}
            {data.pages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100">
                <p className="text-xs text-slate-500">
                  {((page - 1) * 20) + 1}–{Math.min(page * 20, data.total)} of {data.total}
                </p>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setParam('page', String(page - 1))}>Prev</Button>
                  <Button variant="outline" size="sm" disabled={page >= data.pages} onClick={() => setParam('page', String(page + 1))}>Next</Button>
                </div>
              </div>
            )}
          </>
        )}
      </Card>

      <BulkUploadModal open={bulkOpen} onClose={() => setBulkOpen(false)} jobId={jobId} />
    </Layout>
  );
}
