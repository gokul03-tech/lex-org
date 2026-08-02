import { motion } from 'framer-motion';
import { Briefcase, FileText, CheckCircle2, Cpu } from 'lucide-react';

export default function DashboardPage() {
  const stats = [
    { label: 'Active Cases', val: '2', desc: 'Case directories in progress', icon: Briefcase, color: 'text-primary' },
    { label: 'Reports Generated', val: '5', desc: 'Synthesized advisory briefs', icon: FileText, color: 'text-cyan-400' },
    { label: 'Documents Processed', val: '12', desc: 'Statutes and pdf files indexed', icon: CheckCircle2, color: 'text-emerald-400' },
  ];

  return (
    <div className="container mx-auto p-6 lg:p-8 space-y-8 text-left">
      {/* Background glow shadow */}
      <div className="absolute left-[20%] top-[20%] h-96 w-96 rounded-full bg-primary/5 blur-[120px] pointer-events-none"></div>

      {/* Greeting Banner Card */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-2xl border border-white/5 bg-card/40 backdrop-blur-md p-8 shadow-lg"
      >
        <div className="max-w-2xl space-y-3">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
            <Cpu className="h-3.5 w-3.5" />
            LexOrch-KG Framework
          </span>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">
            Dashboard
          </h1>
          <p className="text-muted-foreground text-sm leading-relaxed">
            Welcome to LexOrch-KG, your explainable multi-agent legal advisory platform. Access cases, run dual-agent analysis models, and compile reports.
          </p>
        </div>
      </motion.div>

      {/* Metric Cards Row */}
      <div className="grid gap-6 sm:grid-cols-3">
        {stats.map((stat, idx) => {
          const Icon = stat.icon;
          return (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
              className="glass-card rounded-xl p-6 border border-white/5 flex flex-col justify-between"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">{stat.label}</span>
                <Icon className={`h-5 w-5 ${stat.color}`} />
              </div>
              <div className="mt-4">
                <span className="text-3xl font-extrabold text-white tracking-tight">{stat.val}</span>
                <p className="text-xs text-muted-foreground mt-1">{stat.desc}</p>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
