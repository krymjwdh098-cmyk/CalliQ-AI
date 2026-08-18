import { Link } from 'react-router-dom';
import { Brain } from 'lucide-react';
import { Button } from '../components/ui';

export function NotFoundPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-14 h-14 bg-slate-100 rounded-2xl mb-4">
          <Brain size={26} className="text-slate-400" />
        </div>
        <h1 className="text-2xl font-bold text-slate-800 mb-1">Page not found</h1>
        <p className="text-slate-500 mb-6">The page you're looking for doesn't exist or has moved.</p>
        <Link to="/dashboard">
          <Button>Back to dashboard</Button>
        </Link>
      </div>
    </div>
  );
}
