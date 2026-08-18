import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Brain, AlertCircle, CheckCircle } from 'lucide-react';
import { authApi } from '../api';
import { Button, Input } from '../components/ui';

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') || '';

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!token) {
      setError('This reset link is missing its token. Request a new one.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      await authApi.resetPassword(token, password);
      setDone(true);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'This reset link is invalid or has expired.');
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
        </div>

        <div className="bg-white rounded-2xl shadow-2xl p-8">
          {done ? (
            <div className="text-center py-4">
              <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <CheckCircle size={20} className="text-emerald-600" />
              </div>
              <h2 className="text-lg font-semibold text-slate-800 mb-2">Password reset</h2>
              <p className="text-slate-500 text-sm mb-6">Sign in with your new password.</p>
              <Button className="w-full justify-center" onClick={() => navigate('/login')}>
                Go to sign in
              </Button>
            </div>
          ) : (
            <>
              <h2 className="text-lg font-semibold text-slate-800 mb-6">Set a new password</h2>

              {error && (
                <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg mb-4">
                  <AlertCircle size={16} />
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <Input
                  label="New password"
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  required
                />
                <Input
                  label="Confirm password"
                  type="password"
                  value={confirm}
                  onChange={e => setConfirm(e.target.value)}
                  placeholder="Re-enter password"
                  required
                />
                <Button type="submit" className="w-full justify-center" loading={loading}>
                  Reset password
                </Button>
              </form>

              <div className="mt-6 text-center">
                <Link to="/login" className="text-sm text-blue-600 hover:underline">← Back to login</Link>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
