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
  PanelRight,
  Activity,
  Search,
  Sparkles
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/stores/appStore';
import { useAuthStore } from '@/stores/authStore';

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/cases', label: 'Case Dossiers', icon: Briefcase },
  { href: '/admin', label: 'System Admin', icon: SettingsIcon },
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
      default: return 'Engine Idle';
    }
  };

  const getStatusColorClass = () => {
    switch (agentStatus) {
      case 'thinking': return 'bg-amber-500';
      case 'analyzing': return 'bg-sky-500';
      case 'verifying': return 'bg-purple-500';
      case 'complete': return 'bg-emerald-500';
      default: return 'bg-slate-400';
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#FAF9F6] text-slate-900 font-sans relative">
      {/* Daylight Chambers Aurora Background Ambient Blobs */}
      <div className="aurora-bg">
        <div className="absolute -top-32 -left-32 h-[450px] w-[450px] rounded-full bg-sky-200/40 blur-3xl" />
        <div className="absolute top-1/3 -right-32 h-[400px] w-[400px] rounded-full bg-amber-200/35 blur-3xl" />
        <div className="absolute -bottom-32 left-1/3 h-[450px] w-[450px] rounded-full bg-emerald-200/30 blur-3xl" />
      </div>

      {/* Mobile Menu Button */}
      <button
        className="fixed left-4 top-4 z-50 rounded-xl border border-slate-200 bg-white/90 p-2 text-slate-700 shadow-sm lg:hidden"
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
      >
        {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {/* LEFT PANEL: Sidebar */}
      <motion.aside
        animate={{ width: sidebarCollapsed ? 76 : 260 }}
        transition={{ duration: 0.2 }}
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex flex-col border-r border-slate-200/80 bg-white/80 backdrop-blur-xl shadow-xs transition-transform lg:relative lg:translate-x-0",
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* Brand / Logo */}
        <div className="flex h-16 items-center justify-between border-b border-slate-100 px-6">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 text-white shadow-sm">
              <Scale className="h-5 w-5 shrink-0" />
            </div>
            {!sidebarCollapsed && (
              <div className="flex flex-col">
                <span className="font-serif text-lg font-bold tracking-tight text-slate-900">
                  LexOrch-KG
                </span>
                <span className="font-mono text-[9px] font-semibold text-sky-600 uppercase tracking-wider">
                  Daylight Chambers
                </span>
              </div>
            )}
          </div>
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="hidden text-slate-400 hover:text-slate-700 lg:block cursor-pointer transition"
          >
            <PanelLeftClose className={cn("h-4 w-4 transition-transform", sidebarCollapsed && "rotate-180")} />
          </button>
        </div>

        {/* Navigation items */}
        <nav className="flex-1 space-y-1.5 overflow-y-auto px-3 py-5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.href || location.pathname.startsWith(item.href + '/');
            return (
              <Link
                key={item.href}
                to={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition-all duration-200",
                  isActive
                    ? "bg-sky-50 text-sky-700 font-semibold border border-sky-200 shadow-2xs"
                    : "text-slate-600 hover:bg-slate-100/70 hover:text-slate-900"
                )}
              >
                <Icon className={cn("h-4.5 w-4.5 shrink-0", isActive ? "text-sky-600" : "text-slate-500")} />
                {!sidebarCollapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* User profile / Logout card */}
        <div className="border-t border-slate-100 p-4 space-y-2">
          <div className="flex items-center gap-3 rounded-xl p-2 text-sm bg-slate-50/70 border border-slate-100">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-sky-100 text-sky-700 font-bold text-xs">
              <User className="h-4 w-4" />
            </div>
            {!sidebarCollapsed && (
              <div className="flex flex-col overflow-hidden text-left">
                <span className="truncate font-semibold text-slate-800 text-xs">{user?.full_name || 'Legal Advocate'}</span>
                <span className="truncate text-[10px] font-mono text-slate-500">{user?.role || 'Senior Counsel'}</span>
              </div>
            )}
          </div>
          <Button
            variant="ghost"
            onClick={() => { logout(); navigate('/login'); }}
            className="w-full justify-start gap-2.5 text-rose-600 hover:bg-rose-50 hover:text-rose-700 text-xs font-medium rounded-xl h-9"
          >
            <LogOut className="h-4 w-4 shrink-0" />
            {!sidebarCollapsed && <span>Sign Out</span>}
          </Button>
        </div>
      </motion.aside>

      {/* Mobile Overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/30 backdrop-blur-xs lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* CENTER WORKSPACE & HEADER */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* HEADER */}
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200/80 bg-[#FAF9F6]/80 backdrop-blur-md px-6">
          {/* Active Model Selector */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1 rounded-xl border border-slate-200 bg-white/90 p-1 shadow-2xs text-xs font-mono">
              <button
                onClick={() => setActiveModel('qwen')}
                className={cn(
                  "flex items-center gap-1.5 rounded-lg px-2.5 py-1 font-semibold transition-all cursor-pointer",
                  activeModel === 'qwen'
                    ? "bg-sky-50 text-sky-700 border border-sky-200 shadow-xs"
                    : "text-slate-500 hover:text-slate-800"
                )}
              >
                <Cpu className="h-3.5 w-3.5" />
                Qwen3
              </button>
              <button
                onClick={() => setActiveModel('deepseek')}
                className={cn(
                  "flex items-center gap-1.5 rounded-lg px-2.5 py-1 font-semibold transition-all cursor-pointer",
                  activeModel === 'deepseek'
                    ? "bg-purple-50 text-purple-700 border border-purple-200 shadow-xs"
                    : "text-slate-500 hover:text-slate-800"
                )}
              >
                <Activity className="h-3.5 w-3.5" />
                DeepSeek-R1
              </button>
            </div>

            {/* Agent Live Status Badge */}
            <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-white/80 px-3 py-1 text-xs lg:flex shadow-2xs">
              <span className={cn("relative flex h-2 w-2 rounded-full", getStatusColorClass())}>
                <span className={cn("absolute inline-flex h-full w-full animate-ping rounded-full opacity-75", getStatusColorClass())}></span>
              </span>
              <span className="font-mono text-[11px] text-slate-600 font-medium">{getAgentStatusText()}</span>
            </div>
          </div>

          {/* Right Header actions */}
          <div className="flex items-center gap-3">
            {/* Quick ⌘K Search Trigger */}
            <button
              onClick={() => {
                const event = new KeyboardEvent('keydown', { key: 'k', metaKey: true });
                document.dispatchEvent(event);
              }}
              className="hidden md:flex items-center gap-2 rounded-xl border border-slate-200 bg-white/90 px-3.5 py-1.5 font-mono text-xs text-slate-600 hover:border-slate-300 hover:bg-white shadow-2xs transition cursor-pointer"
            >
              <Search className="h-3.5 w-3.5 text-slate-400" />
              <span>Search cases & statutes...</span>
              <kbd className="rounded-md border border-slate-200 bg-slate-100 px-1.5 py-0.2 text-[10px] text-slate-500 font-semibold">⌘K</kbd>
            </button>

            {/* Notifications */}
            <div className="relative">
              <Button
                variant="ghost"
                size="icon"
                className="relative rounded-xl hover:bg-slate-100 text-slate-600"
                onClick={() => setNotificationsOpen(!notificationsOpen)}
              >
                <Bell className="h-4.5 w-4.5" />
                <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-sky-500"></span>
              </Button>

              <AnimatePresence>
                {notificationsOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    className="absolute right-0 mt-2 w-80 rounded-2xl border border-slate-200 bg-white p-4 shadow-xl z-50 text-left"
                  >
                    <h3 className="mb-2 font-serif font-bold text-slate-900 text-sm">System Notifications</h3>
                    <div className="space-y-2 text-xs">
                      <div className="rounded-xl bg-emerald-50 border border-emerald-100 p-2.5">
                        <p className="font-semibold text-emerald-800">Grounding Engine Online</p>
                        <p className="text-emerald-600 mt-0.5 text-[11px]">FalkorDB and Qdrant multi-stage RAG indexed.</p>
                      </div>
                      <div className="rounded-xl bg-sky-50 border border-sky-100 p-2.5">
                        <p className="font-semibold text-sky-800">Statute Corpus Active</p>
                        <p className="text-sky-600 mt-0.5 text-[11px]">BNS, BNSS, BSA, and IT Act loaded into vector memory.</p>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </header>

        {/* Main workspace view */}
        <div className="flex-1 overflow-y-auto">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
