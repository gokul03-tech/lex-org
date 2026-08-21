import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Scale, Lock, Mail, Eye, EyeOff, Loader2, Sparkles, ShieldCheck } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/button';

export default function LoginPage() {
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Redirect if already logged in
  if (isAuthenticated) {
    setTimeout(() => navigate('/dashboard'), 100);
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please fill in all fields.');
      return;
    }
    
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      let errMsg = 'Invalid email or password.';
      if (typeof detail === 'string') {
        errMsg = detail;
      } else if (Array.isArray(detail)) {
        errMsg = detail.map((d: any) => `${d.loc.join('.')}: ${d.msg}`).join(', ');
      } else if (detail && typeof detail === 'object') {
        errMsg = JSON.stringify(detail);
      }
      setError(errMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen w-screen bg-[#FAF9F6] text-slate-900 overflow-hidden relative">
      {/* Soft Aurora Ambient Background Blobs */}
      <div className="aurora-bg">
        <div className="absolute -top-32 -left-32 h-[450px] w-[450px] rounded-full bg-sky-200/40 blur-3xl" />
        <div className="absolute top-1/3 -right-32 h-[400px] w-[400px] rounded-full bg-amber-200/35 blur-3xl" />
        <div className="absolute -bottom-32 left-1/3 h-[450px] w-[450px] rounded-full bg-emerald-200/30 blur-3xl" />
      </div>

      {/* LEFT PANEL: Branding & Visuals */}
      <div className="relative hidden w-1/2 flex-col justify-between border-r border-slate-200/80 bg-white/60 backdrop-blur-xl p-12 lg:flex text-left">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 text-white shadow-sm">
            <Scale className="h-5 w-5" />
          </div>
          <div className="flex flex-col">
            <span className="font-serif text-xl font-bold tracking-tight text-slate-900">
              LexOrch-KG
            </span>
            <span className="font-mono text-[9px] font-semibold text-sky-600 uppercase tracking-wider">
              Legal Intelligence Engine
            </span>
          </div>
        </div>

        <div className="max-w-md space-y-4">
          <div className="inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-50 px-3.5 py-1 text-xs font-semibold text-sky-700 shadow-2xs">
            <Sparkles className="h-3.5 w-3.5" />
            AI-Powered Legal Decision Support
          </div>
          <h1 className="font-serif text-4xl font-bold tracking-tight text-slate-900 leading-tight">
            Trust-Aware Legal Intelligence Platform
          </h1>
          <p className="text-slate-600 text-sm leading-relaxed font-sans">
            Verify arguments, search judicial precedents, and analyze statutes using multi-agent reasoning, BGE-M3 hybrid retrieval, and FalkorDB knowledge graphs.
          </p>
          <div className="pt-2 flex items-center gap-4 text-xs font-mono text-slate-500">
            <span className="flex items-center gap-1.5 font-semibold text-emerald-700">
              <ShieldCheck className="h-4 w-4" /> Grounded Proofs
            </span>
            <span>•</span>
            <span>Zero Hallucinations</span>
            <span>•</span>
            <span>Indian Law (BNS/BNSS/BSA)</span>
          </div>
        </div>

        <div className="text-xs font-mono text-slate-400">
          © 2026 LexOrch-KG Legal Technologies. All rights reserved.
        </div>
      </div>

      {/* RIGHT PANEL: Login Form */}
      <div className="flex w-full items-center justify-center p-6 sm:p-12 lg:w-1/2 text-left">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="w-full max-w-md rounded-3xl border border-slate-200 bg-white/95 p-8 shadow-xl backdrop-blur-xl"
        >
          <div className="space-y-1">
            <h2 className="font-serif text-2xl font-bold text-slate-900">Welcome Back</h2>
            <p className="text-xs text-slate-500 font-sans">Sign in to your legal advisor account to continue.</p>
          </div>

          {error && (
            <div className="mt-4 rounded-2xl bg-rose-50 border border-rose-200 p-3 text-xs font-semibold text-rose-700 text-center">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4 text-xs">
            <div>
              <label className="font-mono text-[10px] font-bold text-slate-600 uppercase tracking-wider block mb-1">
                Email Address
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                  <Mail className="h-4 w-4" />
                </span>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50/60 py-2.5 pl-10 pr-4 text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-100 focus:outline-none transition shadow-2xs"
                  placeholder="advocate@example.com"
                />
              </div>
            </div>

            <div>
              <label className="font-mono text-[10px] font-bold text-slate-600 uppercase tracking-wider block mb-1">
                Password
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                  <Lock className="h-4 w-4" />
                </span>
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50/60 py-2.5 pl-10 pr-10 text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-100 focus:outline-none transition shadow-2xs"
                  placeholder="••••••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 flex items-center pr-3.5 text-slate-400 hover:text-slate-700 cursor-pointer"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="daylight-btn-primary w-full rounded-xl py-3 text-xs font-bold shadow-md cursor-pointer mt-2"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Authenticating...
                </>
              ) : (
                'Sign In'
              )}
            </Button>

            <p className="text-center text-xs text-slate-500 pt-2 font-sans">
              Don't have an account?{' '}
              <Link to="/register" className="font-bold text-sky-700 hover:text-sky-800 hover:underline">
                Register here
              </Link>
            </p>
          </form>
        </motion.div>
      </div>
    </div>
  );
}
