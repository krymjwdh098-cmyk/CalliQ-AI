import React from 'react';
import { Loader2, X, AlertCircle, CheckCircle, Info } from 'lucide-react';

// ── Button ────────────────────────────────────────────────────────────
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  icon?: React.ReactNode;
}

export function Button({
  variant = 'primary', size = 'md', loading, icon, children, className = '', disabled, ...rest
}: ButtonProps) {
  const base = 'inline-flex items-center gap-2 font-medium rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed';
  const variants = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
    secondary: 'bg-slate-100 text-slate-700 hover:bg-slate-200 focus:ring-slate-400',
    danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
    ghost: 'text-slate-600 hover:bg-slate-100 focus:ring-slate-300',
    outline: 'border border-slate-200 text-slate-700 hover:bg-slate-50 focus:ring-slate-300',
  };
  const sizes = { sm: 'px-3 py-1.5 text-sm', md: 'px-4 py-2 text-sm', lg: 'px-5 py-2.5 text-base' };

  return (
    <button
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? <Loader2 size={16} className="animate-spin" /> : icon}
      {children}
    </button>
  );
}

// ── Badge ─────────────────────────────────────────────────────────────
export function Badge({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${className}`}>
      {children}
    </span>
  );
}

// ── Card ──────────────────────────────────────────────────────────────
export function Card({ children, className = '', padding = true }: {
  children: React.ReactNode; className?: string; padding?: boolean;
}) {
  return (
    <div className={`bg-white rounded-xl border border-slate-200 shadow-sm ${padding ? 'p-6' : ''} ${className}`}>
      {children}
    </div>
  );
}

// ── Input ─────────────────────────────────────────────────────────────
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export function Input({ label, error, hint, className = '', ...rest }: InputProps) {
  return (
    <div className="flex flex-col gap-1">
      {label && <label className="text-sm font-medium text-slate-700">{label}</label>}
      <input
        className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
          ${error ? 'border-red-400 bg-red-50' : 'border-slate-200 bg-white'} ${className}`}
        {...rest}
      />
      {error && <p className="text-xs text-red-600">{error}</p>}
      {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

// ── Textarea ──────────────────────────────────────────────────────────
interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export function Textarea({ label, error, className = '', ...rest }: TextareaProps) {
  return (
    <div className="flex flex-col gap-1">
      {label && <label className="text-sm font-medium text-slate-700">{label}</label>}
      <textarea
        className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none
          ${error ? 'border-red-400 bg-red-50' : 'border-slate-200 bg-white'} ${className}`}
        rows={4}
        {...rest}
      />
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

// ── Select ────────────────────────────────────────────────────────────
interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: { value: string; label: string }[];
}

export function Select({ label, error, options, className = '', ...rest }: SelectProps) {
  return (
    <div className="flex flex-col gap-1">
      {label && <label className="text-sm font-medium text-slate-700">{label}</label>}
      <select
        className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white
          ${error ? 'border-red-400' : 'border-slate-200'} ${className}`}
        {...rest}
      >
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────
export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse bg-slate-100 rounded-lg ${className}`} />;
}

// ── Spinner ───────────────────────────────────────────────────────────
export function Spinner({ size = 20 }: { size?: number }) {
  return <Loader2 size={size} className="animate-spin text-blue-600" />;
}

// ── Modal ─────────────────────────────────────────────────────────────
export function Modal({ open, onClose, title, children, width = 'max-w-lg' }: {
  open: boolean; onClose: () => void; title: string;
  children: React.ReactNode; width?: string;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className={`relative bg-white rounded-2xl shadow-2xl w-full ${width} max-h-[90vh] flex flex-col`}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h2 className="text-base font-semibold text-slate-800">{title}</h2>
          <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded-lg transition-colors">
            <X size={18} className="text-slate-500" />
          </button>
        </div>
        <div className="overflow-y-auto flex-1 p-6">{children}</div>
      </div>
    </div>
  );
}

// ── Toast ─────────────────────────────────────────────────────────────
interface ToastProps {
  message: string;
  type?: 'success' | 'error' | 'info';
  onClose: () => void;
}

export function Toast({ message, type = 'info', onClose }: ToastProps) {
  const styles = {
    success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
    error: 'bg-red-50 border-red-200 text-red-800',
    info: 'bg-blue-50 border-blue-200 text-blue-800',
  };
  const icons = {
    success: <CheckCircle size={16} className="text-emerald-600" />,
    error: <AlertCircle size={16} className="text-red-600" />,
    info: <Info size={16} className="text-blue-600" />,
  };
  return (
    <div className={`flex items-center gap-2 px-4 py-3 border rounded-lg shadow-lg text-sm ${styles[type]}`}>
      {icons[type]}
      <span>{message}</span>
      <button onClick={onClose} className="ml-2 opacity-70 hover:opacity-100"><X size={14} /></button>
    </div>
  );
}

// ── Toast Container ───────────────────────────────────────────────────
let _addToast: ((msg: string, type?: 'success' | 'error' | 'info') => void) | null = null;

export function useToast() {
  return (msg: string, type: 'success' | 'error' | 'info' = 'info') => {
    if (_addToast) _addToast(msg, type);
  };
}

export function ToastContainer() {
  const [toasts, setToasts] = React.useState<{ id: number; msg: string; type: 'success' | 'error' | 'info' }[]>([]);
  let counter = React.useRef(0);

  React.useEffect(() => {
    _addToast = (msg, type = 'info') => {
      const id = ++counter.current;
      setToasts(t => [...t, { id, msg, type }]);
      setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 4000);
    };
  }, []);

  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2">
      {toasts.map(t => (
        <Toast key={t.id} message={t.msg} type={t.type} onClose={() => setToasts(ts => ts.filter(x => x.id !== t.id))} />
      ))}
    </div>
  );
}

// ── Tabs ──────────────────────────────────────────────────────────────
interface TabsProps {
  tabs: { label: string; icon?: React.ReactNode }[];
  active: number;
  onChange: (i: number) => void;
}

export function Tabs({ tabs, active, onChange }: TabsProps) {
  return (
    <div className="flex gap-1 border-b border-slate-200">
      {tabs.map((tab, i) => (
        <button
          key={i}
          onClick={() => onChange(i)}
          className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors
            ${active === i
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'}`}
        >
          {tab.icon}
          {tab.label}
        </button>
      ))}
    </div>
  );
}

// ── Progress Bar ──────────────────────────────────────────────────────
export function ProgressBar({ value, color = 'bg-blue-500', className = '' }: {
  value: number; color?: string; className?: string;
}) {
  return (
    <div className={`h-1.5 bg-slate-100 rounded-full overflow-hidden ${className}`}>
      <div
        className={`h-full rounded-full transition-all ${color}`}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}

// ── Score Ring ────────────────────────────────────────────────────────
export function ScoreRing({ score, size = 80 }: { score: number; size?: number }) {
  const r = (size - 8) / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(100, Math.max(0, score));
  const offset = circ * (1 - pct / 100);

  let color = '#94a3b8';
  if (score >= 80) color = '#10b981';
  else if (score >= 60) color = '#3b82f6';
  else if (score >= 40) color = '#f59e0b';

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90" viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth={8} />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke={color} strokeWidth={8}
          strokeDasharray={circ} strokeDashoffset={offset}
          strokeLinecap="round" className="transition-all duration-500"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-lg font-bold" style={{ color }}>{Math.round(score)}</span>
      </div>
    </div>
  );
}

// ── Empty State ───────────────────────────────────────────────────────
export function EmptyState({ icon, title, description, action }: {
  icon: React.ReactNode; title: string; description?: string; action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center text-slate-400 mb-4">
        {icon}
      </div>
      <h3 className="text-base font-semibold text-slate-700 mb-1">{title}</h3>
      {description && <p className="text-sm text-slate-500 max-w-sm mb-4">{description}</p>}
      {action}
    </div>
  );
}

// ── Tag Input ─────────────────────────────────────────────────────────
export function TagInput({ label, tags, onChange, placeholder }: {
  label?: string; tags: string[]; onChange: (tags: string[]) => void; placeholder?: string;
}) {
  const [val, setVal] = React.useState('');

  const add = () => {
    const trimmed = val.trim();
    if (trimmed && !tags.includes(trimmed)) onChange([...tags, trimmed]);
    setVal('');
  };

  const remove = (t: string) => onChange(tags.filter(x => x !== t));

  return (
    <div className="flex flex-col gap-1">
      {label && <label className="text-sm font-medium text-slate-700">{label}</label>}
      <div className="flex flex-wrap gap-1.5 p-2 border border-slate-200 rounded-lg min-h-[40px] bg-white">
        {tags.map(t => (
          <span key={t} className="flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded-full">
            {t}
            <button type="button" onClick={() => remove(t)} className="hover:text-blue-900"><X size={10} /></button>
          </span>
        ))}
        <input
          value={val}
          onChange={e => setVal(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); add(); } }}
          onBlur={add}
          placeholder={placeholder || 'Add and press Enter'}
          className="flex-1 min-w-24 outline-none text-sm bg-transparent"
        />
      </div>
    </div>
  );
}
