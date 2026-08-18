import React, { useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useDropzone } from 'react-dropzone';
import {
  Brain, MapPin, GraduationCap, Briefcase, CheckCircle,
  Upload, FileText, XCircle, AlertCircle,
} from 'lucide-react';
import { applyApi } from '../api';
import { Button, Input, Spinner } from '../components/ui';

interface JobInfo {
  id: number;
  title: string;
  company?: string;
  description: string;
  required_skills: string[];
  nice_to_have: string[];
  min_experience: number;
  education_req?: string;
  location_req?: string;
}

export function ApplyPage() {
  const { token = '' } = useParams();
  const [form, setForm] = useState({ full_name: '', email: '', phone: '' });
  const [file, setFile] = useState<File | null>(null);
  const [submitted, setSubmitted] = useState<{ candidate_id: number; message: string } | null>(null);
  const [error, setError] = useState('');

  const { data: job, isLoading, isError } = useQuery<JobInfo>({
    queryKey: ['apply-job', token],
    queryFn: () => applyApi.getJob(token),
    retry: false,
  });

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxFiles: 1,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
    },
  });

  const submitMutation = useMutation({
    mutationFn: async () => {
      const fd = new FormData();
      fd.append('full_name', form.full_name);
      fd.append('email', form.email);
      if (form.phone) fd.append('phone', form.phone);
      fd.append('cv_file', file as File);
      return applyApi.submit(token, fd);
    },
    onSuccess: (res) => setSubmitted(res),
    onError: (err: any) => setError(err?.response?.data?.detail || 'Something went wrong. Please try again.'),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!file) {
      setError('Please attach your CV');
      return;
    }
    submitMutation.mutate();
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Spinner size={28} />
      </div>
    );
  }

  if (isError || !job) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
        <div className="text-center max-w-sm">
          <div className="w-14 h-14 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <AlertCircle size={24} className="text-slate-400" />
          </div>
          <h1 className="text-lg font-semibold text-slate-800 mb-1">Job not found</h1>
          <p className="text-sm text-slate-500">
            This link may have expired, or the position is no longer accepting applications.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-slate-900 text-white">
        <div className="max-w-3xl mx-auto px-4 py-6 flex items-center gap-3">
          <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center flex-shrink-0">
            <Brain size={18} className="text-white" />
          </div>
          <span className="font-bold">TalentAI</span>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-8">
        {submitted ? (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-10 text-center">
            <div className="w-14 h-14 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle size={26} className="text-emerald-600" />
            </div>
            <h1 className="text-xl font-bold text-slate-800 mb-2">Application received!</h1>
            <p className="text-slate-500 max-w-sm mx-auto">{submitted.message}</p>
          </div>
        ) : (
          <>
            {/* Job info */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-6">
              <h1 className="text-xl font-bold text-slate-800 mb-1">{job.title}</h1>
              {job.company && <p className="text-slate-500 mb-4">{job.company}</p>}

              <div className="flex flex-wrap gap-4 text-sm text-slate-500 mb-5">
                {job.location_req && (
                  <span className="flex items-center gap-1.5"><MapPin size={14} />{job.location_req}</span>
                )}
                {job.min_experience > 0 && (
                  <span className="flex items-center gap-1.5"><Briefcase size={14} />{job.min_experience}+ years experience</span>
                )}
                {job.education_req && (
                  <span className="flex items-center gap-1.5"><GraduationCap size={14} />{job.education_req}</span>
                )}
              </div>

              <p className="text-sm text-slate-600 whitespace-pre-wrap leading-relaxed mb-5">{job.description}</p>

              {job.required_skills.length > 0 && (
                <div className="mb-3">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Required skills</p>
                  <div className="flex flex-wrap gap-1.5">
                    {job.required_skills.map(s => (
                      <span key={s} className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-lg">{s}</span>
                    ))}
                  </div>
                </div>
              )}

              {job.nice_to_have.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Nice to have</p>
                  <div className="flex flex-wrap gap-1.5">
                    {job.nice_to_have.map(s => (
                      <span key={s} className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded-lg">{s}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Application form */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
              <h2 className="text-base font-semibold text-slate-800 mb-5">Apply for this position</h2>

              {error && (
                <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg mb-4">
                  <AlertCircle size={16} />
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <Input
                  label="Full name"
                  value={form.full_name}
                  onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
                  placeholder="Your full name"
                  required
                />
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="Email"
                    type="email"
                    value={form.email}
                    onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                    placeholder="you@email.com"
                    required
                  />
                  <Input
                    label="Phone (optional)"
                    value={form.phone}
                    onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                    placeholder="+20 100 000 0000"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium text-slate-700 mb-1 block">Your CV *</label>
                  {file ? (
                    <div className="flex items-center gap-3 p-3 border border-slate-200 rounded-lg bg-slate-50">
                      <FileText size={18} className="text-blue-600 flex-shrink-0" />
                      <span className="flex-1 text-sm text-slate-700 truncate">{file.name}</span>
                      <span className="text-xs text-slate-400">{(file.size / 1024).toFixed(0)}KB</span>
                      <button type="button" onClick={() => setFile(null)}>
                        <XCircle size={16} className="text-slate-400 hover:text-red-500" />
                      </button>
                    </div>
                  ) : (
                    <div
                      {...getRootProps()}
                      className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors
                        ${isDragActive ? 'border-blue-400 bg-blue-50' : 'border-slate-200 hover:border-blue-300 hover:bg-slate-50'}`}
                    >
                      <input {...getInputProps()} />
                      <Upload size={22} className="mx-auto text-slate-400 mb-2" />
                      <p className="text-sm font-medium text-slate-600">
                        {isDragActive ? 'Drop your CV here' : 'Drag & drop your CV, or click to browse'}
                      </p>
                      <p className="text-xs text-slate-400 mt-1">PDF, DOC, DOCX, JPG, PNG — up to 10MB</p>
                    </div>
                  )}
                </div>

                <Button type="submit" className="w-full justify-center" loading={submitMutation.isPending} size="lg">
                  Submit application
                </Button>
              </form>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
