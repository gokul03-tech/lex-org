import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Scale, Lock, Mail, User, Briefcase, Loader2, ShieldCheck } from 'lucide-react';
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

  const inputCls =
    'w-full rounded-lg border border-input bg-card py-2.5 pl-10 pr-4 text-sm text-foreground shadow-sm transition placeholder:text-muted-foreground/70 focus:border-brass/60 focus:outline-none focus:ring-2 focus:ring-brass/20';

  return (
    <div className="flex min-h-screen w-screen overflow-hidden bg-background text-foreground">
      {/* LEFT: Brand panel */}
      <div className="relative hidden w-[46%] flex-col justify-between overflow-hidden bg-primary p-12 text-primary-foreground lg:flex">
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              'radial-gradient(900px 500px at 90% -10%, hsl(35 45% 45% / 0.25), transparent 60%), radial-gradient(700px 400px at -10% 110%, hsl(40 27% 97% / 0.06), transparent 55%)',
          }}
        />

        <div className="relative flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-brass-light/40 bg-white/5">
            <Scale className="h-5 w-5 text-brass-light" strokeWidth={1.7} />
          </div>
          <div className="flex flex-col leading-tight">
            <span className="font-serif text-xl font-semibold tracking-tight">LexOrch-KG</span>
            <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-primary-foreground/60">
              Legal Intelligence Engine
            </span>
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="relative max-w-md space-y-5"
        >
          <p className="eyebrow !text-brass-light">Join the Chambers</p>
          <h1 className="font-serif text-4xl font-semibold leading-tight tracking-tight">
            Step into the future of legal advisory.
          </h1>
          <p className="text-[15px] leading-relaxed text-primary-foreground/75">
            Build case dossiers, run hybrid semantic search, visualize statutory graphs, and
            leverage dual-agent IRAC reasoning.
          </p>
          <div className="flex flex-wrap gap-x-5 gap-y-2 pt-2 text-[13px] text-primary-foreground/85">
            <span className="inline-flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-brass-light" strokeWidth={1.7} />
              Multi-tenant security
            </span>
            <span className="inline-flex items-center gap-2">
              <Scale className="h-4 w-4 text-brass-light" strokeWidth={1.7} />
              Encrypted dossiers
            </span>
          </div>
        </motion.div>

        <p className="relative font-mono text-[11px] text-primary-foreground/50">
          © 2026 LexOrch-KG Legal Technologies
        </p>
      </div>

      {/* RIGHT: Form */}
      <div className="flex w-full items-center justify-center p-6 sm:p-12 lg:w-[54%]">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="card-elevated w-full max-w-md rounded-xl p-8 md:p-10"
        >
          <div className="space-y-1.5">
            <p className="eyebrow">New Member</p>
            <h2 className="font-serif text-2xl font-semibold tracking-tight">Create your account</h2>
            <p className="text-sm text-muted-foreground">Set up your advisor credentials to get started.</p>
          </div>

          {error && (
            <div className="mt-5 rounded-lg border border-destructive/25 bg-destructive/10 p-3 text-center text-[13px] font-medium text-destructive">
              {error}
            </div>
          )}

          {success && (
            <div className="mt-5 rounded-lg border border-sage/30 bg-sage/10 p-3 text-center text-[13px] font-medium text-sage">
              {success}
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-7 space-y-5">
            <div className="space-y-1.5">
              <label className="eyebrow block">Full Name</label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" strokeWidth={1.7} />
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className={inputCls}
                  placeholder="Advocate Rajesh Kumar"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="eyebrow block">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" strokeWidth={1.7} />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={inputCls}
                  placeholder="rajesh@lawchambers.in"
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label className="eyebrow block">Role</label>
                <div className="relative">
                  <Briefcase className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" strokeWidth={1.7} />
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    className={`${inputCls} cursor-pointer`}
                  >
                    <option value="Advocate">Advocate</option>
                    <option value="Legal Researcher">Legal Researcher</option>
                    <option value="Law Student">Law Student</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="eyebrow block">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" strokeWidth={1.7} />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className={inputCls}
                    placeholder="••••••••"
                  />
                </div>
              </div>
            </div>

            <Button type="submit" disabled={loading} size="lg" className="mt-1 w-full rounded-lg font-semibold">
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Creating account…
                </>
              ) : (
                'Complete Registration'
              )}
            </Button>

            <p className="pt-1 text-center text-[13px] text-muted-foreground">
              Already have an account?{' '}
              <Link to="/login" className="font-medium text-primary underline-offset-2 hover:underline">
                Sign in
              </Link>
            </p>
          </form>
        </motion.div>
      </div>
    </div>
  );
}
