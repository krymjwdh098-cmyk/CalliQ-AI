import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Brain, AlertCircle } from 'lucide-react';
import { authApi } from '../api';
import { useAuthStore } from '../store/auth';
import { Button, Input } from '../components/ui';

export function RegisterPage() {
  const navigate = useNavigate();
  const { setToken, setUser } = useAuthStore();
  const [form, setForm] = useState({ name: '', org_name: '', email: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const set = (k: keyof typeof form, v: string) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    setLoading(true);
    try {
      const { access_token } = await authApi.register(form);
      setToken(access_token);
      const user = await authApi.me();
      setUser(user);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-blue-600 rounded-2xl mb-4 shadow-lg shadow-blue-500/30">
            <Brain size={28} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">TalentAI</h1>
          <p className="text-slate-400 text-sm mt-1">Create your organization's workspace</p>
        </div>

        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <h2 className="text-lg font-semibold text-slate-800 mb-6">Create your account</h2>

          {error && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg mb-4">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Your name"
              value={form.name}
              onChange={e => set('name', e.target.value)}
              placeholder="Sarah Ahmed"
              required
            />
            <Input
              label="Organization name"
              value={form.org_name}
              onChange={e => set('org_name', e.target.value)}
              placeholder="Acme Corp"
              required
            />
            <Input
              label="Work email"
              type="email"
              value={form.email}
              onChange={e => set('email', e.target.value)}
              placeholder="you@company.com"
              required
            />
            <Input
              label="Password"
              type="password"
              value={form.password}
              onChange={e => set('password', e.target.value)}
              placeholder="At least 8 characters"
              hint="Use at least 8 characters"
              required
            />

            <Button type="submit" className="w-full justify-center" loading={loading} size="lg">
              Create account
            </Button>
          </form>

          <p className="text-center text-sm text-slate-500 mt-6">
            Already have an account?{' '}
            <Link to="/login" className="text-blue-600 hover:underline font-medium">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
