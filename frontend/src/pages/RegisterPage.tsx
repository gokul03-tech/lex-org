import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Scale, Lock, Mail, User, Briefcase, Loader2 } from 'lucide-react';
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
      await register(email, password, fullName, role);
      setSuccess('Account created successfully! Redirecting to login...');
      setTimeout(() => navigate('/login'), 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to register account. User may already exist.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen w-screen bg-background overflow-hidden">
      {/* LEFT PANEL: Branding & Visuals */}
      <div className="relative hidden w-1/2 flex-col justify-between border-r border-white/5 bg-card/40 p-12 lg:flex">
        <div className="absolute -left-20 -top-20 h-80 w-80 rounded-full bg-blue-500/10 blur-[120px]"></div>
        <div className="absolute -bottom-20 right-10 h-90 w-90 rounded-full bg-cyan-500/10 blur-[120px]"></div>

        <div className="flex items-center gap-3">
          <Scale className="h-8 w-8 text-primary" />
          <span className="text-xl font-bold bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
            LexOrch-KG
          </span>
        </div>

        <div className="max-w-md space-y-4">
          <h1 className="text-4xl font-extrabold tracking-tight text-white leading-tight">
            Step Into the Future of Legal Advisory
          </h1>
          <p className="text-muted-foreground text-sm leading-relaxed">
            Create an account to build cases, run semantic searches, visualize statutes in structural hierarchies, and leverage dual-agent reasoning.
          </p>
        </div>

        <div className="text-xs text-muted-foreground">
          © 2026 LexOrch-KG Team. All rights reserved.
        </div>
      </div>

      {/* RIGHT PANEL: Register Form */}
      <div className="flex w-full items-center justify-center p-8 lg:w-1/2">
        <div className="absolute -right-20 top-10 h-80 w-80 rounded-full bg-primary/5 blur-[120px] lg:hidden"></div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-md rounded-2xl border border-white/5 bg-card/30 backdrop-blur-md p-8 shadow-2xl"
        >
          <div className="flex flex-col items-center text-center lg:items-start lg:text-left">
            <h2 className="text-2xl font-bold tracking-tight text-white">Create Account</h2>
            <p className="text-sm text-muted-foreground mt-1">Get started by setting up your profile details.</p>
          </div>

          {error && (
            <div className="mt-4 rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-xs font-medium text-red-400 text-center">
              {error}
            </div>
          )}

          {success && (
            <div className="mt-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-3 text-xs font-medium text-emerald-400 text-center">
              {success}
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Full Name</label>
              <div className="relative mt-1">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-muted-foreground">
                  <User className="h-4 w-4" />
                </span>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full rounded-lg border border-white/5 bg-muted/50 py-2.5 pl-10 pr-4 text-sm text-white placeholder-muted-foreground focus:border-primary focus:outline-none transition-colors"
                  placeholder="Advocate John Doe"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Email Address</label>
              <div className="relative mt-1">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-muted-foreground">
                  <Mail className="h-4 w-4" />
                </span>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-white/5 bg-muted/50 py-2.5 pl-10 pr-4 text-sm text-white placeholder-muted-foreground focus:border-primary focus:outline-none transition-colors"
                  placeholder="john.doe@court.in"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Password</label>
              <div className="relative mt-1">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-muted-foreground">
                  <Lock className="h-4 w-4" />
                </span>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg border border-white/5 bg-muted/50 py-2.5 pl-10 pr-4 text-sm text-white placeholder-muted-foreground focus:border-primary focus:outline-none transition-colors"
                  placeholder="Create secure password"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Professional Role</label>
              <div className="relative mt-1">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-muted-foreground">
                  <Briefcase className="h-4 w-4" />
                </span>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full rounded-lg border border-white/5 bg-muted/50 py-2.5 pl-10 pr-4 text-sm text-white focus:border-primary focus:outline-none transition-colors appearance-none"
                >
                  <option value="Advocate" className="bg-card">Advocate</option>
                  <option value="Legal Researcher" className="bg-card">Legal Researcher</option>
                  <option value="Law Student" className="bg-card">Law Student</option>
                  <option value="General" className="bg-card">General User</option>
                </select>
              </div>
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-primary py-2.5 text-primary-foreground font-semibold hover:bg-primary/95 transition-all shadow-md shadow-primary/20"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating Account...
                </>
              ) : (
                'Register'
              )}
            </Button>
          </form>

          <p className="mt-6 text-center text-xs text-muted-foreground">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold text-primary hover:underline">
              Sign In
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
