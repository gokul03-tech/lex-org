import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Scale, Lock, Mail, User, Briefcase, Loader2, Sparkles, ShieldCheck } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/button';

export default function RegisterPage() {
  const navigate = useNavigate();
  const register = useAuthStore((state) => state.register);

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('Advocate');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName || !email || !password) {
      setError('Please fill in all fields.');
      return;
    }

    setError('');
    setLoading(true);
    try {
      let backendRole = 'advocate';
      if (role === 'Legal Researcher') backendRole = 'researcher';
      if (role === 'Law Student') backendRole = 'student';

      await register(email, password, fullName, backendRole);
      setSuccess('Account created successfully! Redirecting to login...');
      setTimeout(() => navigate('/login'), 1500);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      let errMsg = 'Failed to register account. User may already exist.';
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
            Empowering Legal Practitioners
          </div>
          <h1 className="font-serif text-4xl font-bold tracking-tight text-slate-900 leading-tight">
            Step Into the Future of Legal Advisory
          </h1>
          <p className="text-slate-600 text-sm leading-relaxed font-sans">
            Create an account to build case dossiers, run hybrid semantic searches, visualize statutory graphs, and leverage dual-agent IRAC reasoning.
          </p>
          <div className="pt-2 flex items-center gap-4 text-xs font-mono text-slate-500">
            <span className="flex items-center gap-1.5 font-semibold text-emerald-700">
              <ShieldCheck className="h-4 w-4" /> Multi-Tenant Security
            </span>
            <span>•</span>
            <span>Fast Ingestion</span>
            <span>•</span>
            <span>Encrypted Dossiers</span>
          </div>
        </div>

        <div className="text-xs font-mono text-slate-400">
          © 2026 LexOrch-KG Legal Technologies. All rights reserved.
        </div>
      </div>

      {/* RIGHT PANEL: Register Form */}
      <div className="flex w-full items-center justify-center p-6 sm:p-12 lg:w-1/2 text-left">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="w-full max-w-md rounded-3xl border border-slate-200 bg-white/95 p-8 shadow-xl backdrop-blur-xl"
        >
          <div className="space-y-1">
            <h2 className="font-serif text-2xl font-bold text-slate-900">Create Account</h2>
            <p className="text-xs text-slate-500 font-sans">Get started by setting up your advisor credentials.</p>
          </div>

          {error && (
            <div className="mt-4 rounded-2xl bg-rose-50 border border-rose-200 p-3 text-xs font-semibold text-rose-700 text-center">
              {error}
            </div>
          )}

          {success && (
            <div className="mt-4 rounded-2xl bg-emerald-50 border border-emerald-200 p-3 text-xs font-semibold text-emerald-700 text-center">
              {success}
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4 text-xs">
            <div>
              <label className="font-mono text-[10px] font-bold text-slate-600 uppercase tracking-wider block mb-1">
                Full Name
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                  <User className="h-4 w-4" />
                </span>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50/60 py-2.5 pl-10 pr-4 text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-100 focus:outline-none transition shadow-2xs"
                  placeholder="Advocate Rajesh Kumar"
                />
              </div>
            </div>

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
                  placeholder="rajesh@lawchambers.in"
                />
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="font-mono text-[10px] font-bold text-slate-600 uppercase tracking-wider block mb-1">
                  Professional Role
                </label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400">
                    <Briefcase className="h-4 w-4" />
                  </span>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50/60 py-2.5 pl-10 pr-4 text-xs font-medium text-slate-900 focus:bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-100 focus:outline-none transition shadow-2xs cursor-pointer"
                  >
                    <option value="Advocate">Advocate</option>
                    <option value="Legal Researcher">Legal Researcher</option>
                    <option value="Law Student">Law Student</option>
                  </select>
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
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50/60 py-2.5 pl-10 pr-4 text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-100 focus:outline-none transition shadow-2xs"
                    placeholder="••••••••••••"
                  />
                </div>
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
                  Creating Account...
                </>
              ) : (
                'Complete Registration'
              )}
            </Button>

            <p className="text-center text-xs text-slate-500 pt-2 font-sans">
              Already have an account?{' '}
              <Link to="/login" className="font-bold text-sky-700 hover:text-sky-800 hover:underline">
                Sign In
              </Link>
            </p>
          </form>
        </motion.div>
      </div>
    </div>
  );
}
