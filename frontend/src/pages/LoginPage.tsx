import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Scale, Lock, Mail, Eye, EyeOff, Loader2, ShieldCheck, BookOpen, Network } from 'lucide-react';
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
          <p className="eyebrow !text-brass-light">Counsel, Augmented</p>
          <h1 className="font-serif text-4xl font-semibold leading-tight tracking-tight">
            Trust-aware intelligence for the modern chambers.
          </h1>
          <p className="text-[15px] leading-relaxed text-primary-foreground/75">
            Verify arguments, search judicial precedent, and analyze statutes through multi-agent
            reasoning, hybrid retrieval, and knowledge graphs.
          </p>
          <ul className="space-y-2.5 pt-2 text-sm text-primary-foreground/85">
            {[
              { icon: ShieldCheck, text: 'Grounded proofs — every claim traceable to source' },
              { icon: BookOpen, text: 'Indian law corpus · BNS · BNSS · BSA · IT Act' },
              { icon: Network, text: 'Evidence graphs across Qdrant & FalkorDB' },
            ].map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-2.5">
                <Icon className="h-4 w-4 shrink-0 text-brass-light" strokeWidth={1.7} />
                {text}
              </li>
            ))}
          </ul>
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
            <p className="eyebrow">Member Access</p>
            <h2 className="font-serif text-2xl font-semibold tracking-tight">Welcome back</h2>
            <p className="text-sm text-muted-foreground">Sign in to your advisory account to continue.</p>
          </div>

          {error && (
            <div className="mt-5 rounded-lg border border-destructive/25 bg-destructive/10 p-3 text-center text-[13px] font-medium text-destructive">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-7 space-y-5">
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
                  placeholder="advocate@example.com"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="eyebrow block">Password</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" strokeWidth={1.7} />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={`${inputCls} pr-11`}
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 flex cursor-pointer items-center pr-3.5 text-muted-foreground transition hover:text-foreground"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" strokeWidth={1.7} /> : <Eye className="h-4 w-4" strokeWidth={1.7} />}
                </button>
              </div>
            </div>

            <Button type="submit" disabled={loading} size="lg" className="mt-1 w-full rounded-lg font-semibold">
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Authenticating…
                </>
              ) : (
                'Sign In'
              )}
            </Button>

            <p className="pt-1 text-center text-[13px] text-muted-foreground">
              Don't have an account?{' '}
              <Link to="/register" className="font-medium text-primary underline-offset-2 hover:underline">
                Register here
              </Link>
            </p>
          </form>
        </motion.div>
      </div>
    </div>
  );
}
