import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Brain, Eye, EyeOff, AlertCircle } from 'lucide-react';
import { authApi } from '../api';
import { useAuthStore } from '../store/auth';
import { Button, Input } from '../components/ui';

export function LoginPage() {
  const navigate = useNavigate();
  const { setToken, setUser } = useAuthStore();
  const [email, setEmail] = useState('demo@company.com');
  const [password, setPassword] = useState('demo1234');
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const { access_token } = await authApi.login(email, password);
      setToken(access_token);
      const user = await authApi.me();
      setUser(user);
      navigate('/dashboard');
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || 
                          err?.message || 
                          'Login failed. Check your credentials.';
      setError(typeof errorMessage === 'string' ? errorMessage : 'Login failed. Check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-blue-600 rounded-2xl mb-4 shadow-lg shadow-blue-500/30">
            <Brain size={28} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">TalentAI</h1>
          <p className="text-slate-400 text-sm mt-1">AI-Powered Recruitment Platform</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <h2 className="text-lg font-semibold text-slate-800 mb-6">Sign in to your account</h2>

          {error && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg mb-4">
              <AlertCircle size={16} />
              <span>{String(error)}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Email"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@company.com"
              required
            />

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-slate-700">Password</label>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 pr-10"
                  placeholder="••••••••"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPw(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div className="flex justify-end">
              <Link to="/forgot-password" className="text-sm text-blue-600 hover:underline">
                Forgot password?
              </Link>
            </div>

            <Button type="submit" className="w-full justify-center" loading={loading} size="lg">
              Sign in
            </Button>
          </form>

          <div className="mt-6 p-3 bg-slate-50 rounded-lg border border-slate-200">
            <p className="text-xs text-slate-500 text-center">
              Demo: <strong>demo@company.com</strong> / <strong>demo1234</strong>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await authApi.forgotPassword(email);
      setSent(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8">
        <div className="mb-6">
          <Link to="/login" className="text-sm text-blue-600 hover:underline">← Back to login</Link>
        </div>
        <h2 className="text-lg font-semibold text-slate-800 mb-2">Reset your password</h2>
        {sent ? (
          <div className="text-center py-8">
            <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <Brain size={20} className="text-emerald-600" />
            </div>
            <p className="text-slate-600 text-sm">If that email exists, a reset link has been sent.</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4 mt-4">
            <Input
              label="Email"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@company.com"
              required
            />
            <Button type="submit" className="w-full justify-center" loading={loading}>
              Send reset link
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}
