import { useState } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  Briefcase,
  Scale,
  Settings as SettingsIcon,
  LogOut,
  Menu,
  X,
  Bell,
  Cpu,
  User,
  PanelLeftClose,
  PanelRightClose,
  PanelRight,
  Activity,
  CheckCircle2,
  ChevronRight
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/stores/appStore';
import { useAuthStore } from '@/stores/authStore';

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/cases', label: 'Cases', icon: Briefcase },
  { href: '/admin', label: 'Admin', icon: SettingsIcon },
];

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const user = useAuthStore((state) => state.user);

  const {
    sidebarCollapsed,
    setSidebarCollapsed,
    insightPanelOpen,
    setInsightPanelOpen,
    activeModel,
    setActiveModel,
    agentStatus
  } = useAppStore();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  const getAgentStatusText = () => {
    switch (agentStatus) {
      case 'thinking': return 'Agent Thinking...';
      case 'analyzing': return 'Querying Knowledge Graph...';
      case 'verifying': return 'Verifying Evidence...';
      case 'complete': return 'Analysis Complete';
      default: return 'System Idle';
    }
  };

  const getStatusColorClass = () => {
    switch (agentStatus) {
      case 'thinking': return 'bg-amber-500 shadow-amber-500/50';
      case 'analyzing': return 'bg-blue-500 shadow-blue-500/50';
      case 'verifying': return 'bg-purple-500 shadow-purple-500/50';
      case 'complete': return 'bg-emerald-500 shadow-emerald-500/50';
      default: return 'bg-slate-500 shadow-slate-500/20';
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      {/* Mobile Menu Button */}
      <button
        className="fixed left-4 top-4 z-50 rounded-md border border-white/10 bg-card p-2 text-foreground lg:hidden"
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
      >
        {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {/* LEFT PANEL: Sidebar */}
      <motion.aside
        animate={{ width: sidebarCollapsed ? 72 : 256 }}
        transition={{ duration: 0.2 }}
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex flex-col border-r border-white/5 bg-card/60 backdrop-blur-xl transition-transform lg:relative lg:translate-x-0",
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* Brand/Logo */}
        <div className="flex h-16 items-center justify-between border-b border-white/5 px-6">
          <div className="flex items-center gap-3 overflow-hidden">
            <Scale className="h-6 w-6 shrink-0 text-primary" />
            {!sidebarCollapsed && (
              <span className="bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-lg font-bold text-transparent">
                LexOrch-KG
              </span>
            )}
          </div>
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="hidden text-muted-foreground hover:text-foreground lg:block"
          >
            <PanelLeftClose className={cn("h-4 w-4 transition-transform", sidebarCollapsed && "rotate-180")} />
          </button>
        </div>

        {/* Navigation items */}
        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.href || location.pathname.startsWith(item.href + '/');
            return (
              <Link
                key={item.href}
                to={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                  isActive
                    ? "bg-primary/10 text-primary border-l-2 border-primary"
                    : "text-muted-foreground hover:bg-white/5 hover:text-foreground"
                )}
              >
                <Icon className="h-5 w-5 shrink-0" />
                {!sidebarCollapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* User profile / Logout */}
        <div className="border-t border-white/5 p-4 space-y-2">
          <div className="flex items-center gap-3 rounded-lg p-2 text-sm text-muted-foreground hover:bg-white/5 hover:text-foreground">
            <User className="h-5 w-5 shrink-0" />
            {!sidebarCollapsed && (
              <div className="flex flex-col overflow-hidden text-left">
                <span className="truncate font-semibold text-foreground">{user?.full_name || 'Legal Advocate'}</span>
                <span className="truncate text-xs text-muted-foreground">{user?.role || 'Researcher'}</span>
              </div>
            )}
          </div>
          <Button
            variant="ghost"
            onClick={() => { logout(); navigate('/login'); }}
            className="w-full justify-start gap-3 text-red-400 hover:bg-red-500/10 hover:text-red-400"
          >
            <LogOut className="h-5 w-5 shrink-0" />
            {!sidebarCollapsed && <span>Sign Out</span>}
          </Button>
        </div>
      </motion.aside>

      {/* Mobile Overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/60 lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* CENTER & RIGHT WORKSPACE */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* HEADER */}
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-white/5 bg-background/40 backdrop-blur-md px-6">
          {/* Active Model Selector */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5 rounded-lg border border-white/5 bg-secondary/30 p-1">
              <button
                onClick={() => setActiveModel('qwen')}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-semibold transition-all",
                  activeModel === 'qwen'
                    ? "bg-primary text-primary-foreground shadow"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <Cpu className="h-3.5 w-3.5" />
                Qwen3
              </button>
              <button
                onClick={() => setActiveModel('deepseek')}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-semibold transition-all",
                  activeModel === 'deepseek'
                    ? "bg-primary text-primary-foreground shadow"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <Activity className="h-3.5 w-3.5" />
                DeepSeek-R1
              </button>
            </div>

            {/* Agent Live Status */}
            <div className="hidden items-center gap-2 rounded-full border border-white/5 bg-card/40 px-3 py-1 lg:flex">
              <span className={cn("relative flex h-2 w-2 rounded-full", getStatusColorClass())}>
                <span className={cn("absolute inline-flex h-full w-full animate-ping rounded-full opacity-75", getStatusColorClass())}></span>
              </span>
              <span className="text-xs font-medium text-muted-foreground">{getAgentStatusText()}</span>
            </div>
          </div>

          {/* Right Header actions */}
          <div className="flex items-center gap-4">
            {/* Notifications */}
            <div className="relative">
              <Button
                variant="ghost"
                size="icon"
                className="relative"
                onClick={() => setNotificationsOpen(!notificationsOpen)}
              >
                <Bell className="h-5 w-5" />
                <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-primary shadow-sm shadow-primary/50"></span>
              </Button>

              <AnimatePresence>
                {notificationsOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    className="absolute right-0 mt-2 w-80 rounded-lg border border-white/5 bg-card p-4 shadow-xl"
                  >
                    <h3 className="mb-2 font-semibold">Notifications</h3>
                    <div className="space-y-2.5">
                      <div className="rounded-md bg-white/5 p-2 text-xs">
                        <p className="font-semibold text-primary">Ingestion Success</p>
                        <p className="text-muted-foreground mt-0.5">Constitution of India parsed and embedded successfully.</p>
                      </div>
                      <div className="rounded-md bg-white/5 p-2 text-xs">
                        <p className="font-semibold text-primary">Database Online</p>
                        <p className="text-muted-foreground mt-0.5">Qdrant connection verified. 522k vectors loaded.</p>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Toggle Insight Panel */}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setInsightPanelOpen(!insightPanelOpen)}
              className={cn(insightPanelOpen && "text-primary bg-primary/10")}
            >
              <PanelRight className="h-5 w-5" />
            </Button>
          </div>
        </header>

        {/* WORKSPACE & INSIGHT LAYOUT */}
        <div className="flex flex-1 overflow-hidden">
          {/* Main workspace */}
          <div className="flex-1 overflow-y-auto">
            <Outlet />
          </div>

          {/* RIGHT PANEL: Agent Insight Panel */}
          <AnimatePresence>
            {insightPanelOpen && (
              <motion.aside
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: 320, opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="hidden border-l border-white/5 bg-card/40 backdrop-blur-xl p-5 overflow-y-auto lg:flex flex-col gap-6"
              >
                <div className="flex items-center justify-between border-b border-white/5 pb-3">
                  <h3 className="font-semibold text-gradient-cyan">Agent Insights</h3>
                  <button onClick={() => setInsightPanelOpen(false)} className="text-muted-foreground hover:text-foreground">
                    <PanelRightClose className="h-4 w-4" />
                  </button>
                </div>

                {/* System Confidence Widget */}
                <div className="rounded-lg border border-white/5 bg-white/5 p-4">
                  <span className="text-xs font-semibold text-muted-foreground">Retrieval Confidence Score</span>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span className="text-3xl font-extrabold text-primary">94.8%</span>
                    <span className="text-xs text-emerald-400 font-medium">▲ Very High</span>
                  </div>
                  <div className="mt-2 h-1.5 w-full rounded-full bg-secondary">
                    <div className="h-1.5 rounded-full bg-gradient-to-r from-blue-500 to-cyan-400" style={{ width: '94.8%' }}></div>
                  </div>
                </div>

                {/* Agent Activity Steps */}
                <div className="flex-1 flex flex-col gap-4">
                  <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Active Reasoning Steps</span>
                  <div className="space-y-4">
                    <div className="flex gap-3">
                      <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                      <div className="text-xs">
                        <p className="font-semibold">Query reformulation</p>
                        <p className="text-muted-foreground mt-0.5">Reformulated user input into search vector keywords.</p>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                      <div className="text-xs">
                        <p className="font-semibold">Hybrid Search execution</p>
                        <p className="text-muted-foreground mt-0.5">Retrieved 12 vector points and 8 relational graph links.</p>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <div className="relative flex h-4 w-4 shrink-0 mt-0.5 items-center justify-center">
                        <span className="animate-ping absolute inline-flex h-2.5 w-2.5 rounded-full bg-primary opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                      </div>
                      <div className="text-xs">
                        <p className="font-semibold text-primary">Cross-referencing precedents</p>
                        <p className="text-muted-foreground mt-0.5">Verifying case judgments for statutory conflicts.</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Citations Panel */}
                <div className="rounded-lg border border-white/5 bg-secondary/20 p-4">
                  <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">Live References</h4>
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between text-muted-foreground">
                      <span>Constitution:</span>
                      <span className="font-semibold text-foreground">Article 21</span>
                    </div>
                    <div className="flex justify-between text-muted-foreground">
                      <span>BNS Code:</span>
                      <span className="font-semibold text-foreground">Section 302</span>
                    </div>
                  </div>
                </div>
              </motion.aside>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
