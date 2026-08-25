import { useState } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  Briefcase,
  Settings as SettingsIcon,
  LogOut,
  Menu,
  X,
  Bell,
  Scale,
  Search,
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
  const { sidebarCollapsed, setSidebarCollapsed } = useAppStore();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  const currentNav = navItems.find(
    (item) => location.pathname === item.href || location.pathname.startsWith(item.href + '/')
  );
  const pageTitle = currentNav?.label ?? 'Workspace';

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      {/* Soft parchment ambient wash */}
      <div className="aurora-bg" />

      {/* Mobile menu trigger */}
      <button
        aria-label="Toggle navigation"
        className="fixed left-4 top-4 z-50 rounded-lg border border-border bg-card p-2 text-muted-foreground shadow-sm lg:hidden"
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
      >
        {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {/* ── Sidebar ─────────────────────────────────────────────── */}
      <motion.aside
        animate={{ width: sidebarCollapsed ? 76 : 248 }}
        transition={{ duration: 0.25, ease: 'easeInOut' }}
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex flex-col border-r border-border bg-card transition-transform lg:relative lg:translate-x-0',
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        {/* Brand */}
        <div className="flex h-[68px] items-center justify-between border-b border-border px-5">
          <Link to="/dashboard" className="flex items-center gap-3 overflow-hidden">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
              <Scale className="h-[18px] w-[18px]" strokeWidth={1.8} />
            </div>
            {!sidebarCollapsed && (
              <div className="flex flex-col leading-tight">
                <span className="font-serif text-[17px] font-semibold tracking-tight text-foreground">
                  LexOrch<span className="text-brass">-KG</span>
                </span>
                <span className="font-mono text-[9px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                  Legal Intelligence
                </span>
              </div>
            )}
          </Link>
          {!sidebarCollapsed && (
            <button
              onClick={() => setSidebarCollapsed(true)}
              className="hidden rounded p-1 text-muted-foreground/60 transition hover:bg-secondary hover:text-foreground lg:block"
              aria-label="Collapse sidebar"
            >
              <X className="hidden" />
              <span className="font-mono text-xs text-muted-foreground">«</span>
            </button>
          )}
        </div>
        {sidebarCollapsed && (
          <button
            onClick={() => setSidebarCollapsed(false)}
            className="absolute -right-6 top-[76px] hidden rounded-r-md border border-l-0 border-border bg-card px-1 py-2 text-muted-foreground shadow-sm hover:text-foreground lg:block"
            aria-label="Expand sidebar"
          >
            <span className="font-mono text-xs">»</span>
          </button>
        )}

        {/* Navigation */}
        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-6">
          {!sidebarCollapsed && <p className="eyebrow mb-2 px-3">Workspace</p>}
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              location.pathname === item.href || location.pathname.startsWith(item.href + '/');
            return (
              <Link
                key={item.href}
                to={item.href}
                onClick={() => setMobileMenuOpen(false)}
                title={sidebarCollapsed ? item.label : undefined}
                className={cn(
                  'group relative flex items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm transition-colors duration-200',
                  isActive
                    ? 'bg-primary text-primary-foreground font-medium shadow-sm'
                    : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
                )}
              >
                <Icon
                  className={cn('h-[18px] w-[18px] shrink-0', isActive && 'text-brass-light')}
                  strokeWidth={isActive ? 2 : 1.7}
                />
                {!sidebarCollapsed && <span>{item.label}</span>}
                {isActive && !sidebarCollapsed && (
                  <span className="ml-auto h-1.5 w-1.5 rounded-full bg-brass-light" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Footer: user card + sign out */}
        <div className="space-y-1 border-t border-border p-4">
          <div
            className={cn(
              'flex items-center gap-3 rounded-lg px-2 py-2',
              sidebarCollapsed && 'justify-center'
            )}
          >
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-brass/40 bg-secondary font-serif text-sm font-semibold text-primary">
              {(user?.full_name || 'A').charAt(0).toUpperCase()}
            </div>
            {!sidebarCollapsed && (
              <div className="min-w-0 flex-1 text-left">
                <p className="truncate text-[13px] font-medium text-foreground">
                  {user?.full_name || 'Legal Advocate'}
                </p>
                <p className="truncate font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  {user?.role || 'Counsel'}
                </p>
              </div>
            )}
          </div>
          <Button
            variant="ghost"
            onClick={() => {
              logout();
              navigate('/login');
            }}
            className={cn(
              'h-9 w-full justify-start gap-2.5 rounded-lg text-[13px] font-medium text-muted-foreground hover:bg-destructive/10 hover:text-destructive',
              sidebarCollapsed && 'justify-center'
            )}
          >
            <LogOut className="h-4 w-4 shrink-0" />
            {!sidebarCollapsed && <span>Sign Out</span>}
          </Button>
        </div>
      </motion.aside>

      {/* Mobile overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-30 bg-foreground/30 backdrop-blur-[2px] lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* ── Main column ─────────────────────────────────────────── */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header className="sticky top-0 z-20 flex h-[68px] shrink-0 items-center justify-between border-b border-border bg-background/85 pl-16 pr-6 backdrop-blur-md lg:pl-8">
          <div className="flex items-baseline gap-3">
            <h1 className="font-serif text-lg font-semibold tracking-tight">{pageTitle}</h1>
            <span className="hidden h-3.5 w-px bg-border sm:block" />
            <p className="eyebrow hidden sm:block">LexOrch-KG Chambers</p>
          </div>

          <div className="flex items-center gap-2">
            {/* Command search */}
            <button
              onClick={() => {
                const event = new KeyboardEvent('keydown', { key: 'k', metaKey: true });
                document.dispatchEvent(event);
              }}
              className="hidden items-center gap-2.5 rounded-lg border border-input bg-card px-3.5 py-2 text-[13px] text-muted-foreground shadow-sm transition hover:border-brass/50 hover:text-foreground md:flex"
            >
              <Search className="h-3.5 w-3.5" />
              <span>Search cases &amp; statutes</span>
              <kbd className="rounded border border-border bg-secondary px-1.5 py-0.5 font-mono text-[10px] font-medium text-muted-foreground">
                ⌘K
              </kbd>
            </button>

            {/* Notifications */}
            <div className="relative">
              <Button
                variant="ghost"
                size="icon"
                className="relative rounded-lg text-muted-foreground hover:bg-secondary hover:text-foreground"
                onClick={() => setNotificationsOpen(!notificationsOpen)}
              >
                <Bell className="h-[18px] w-[18px]" strokeWidth={1.7} />
                <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-brass ring-2 ring-background" />
              </Button>

              <AnimatePresence>
                {notificationsOpen && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setNotificationsOpen(false)} />
                    <motion.div
                      initial={{ opacity: 0, y: 8, scale: 0.98 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 8, scale: 0.98 }}
                      transition={{ duration: 0.15 }}
                      className="absolute right-0 z-50 mt-2 w-80 rounded-xl border border-border bg-card p-4 shadow-xl"
                    >
                      <h3 className="mb-3 font-serif text-sm font-semibold text-foreground">
                        System Notifications
                      </h3>
                      <div className="space-y-2.5 text-left">
                        <div className="rounded-lg border border-sage/25 bg-sage/10 p-3">
                          <p className="text-[13px] font-semibold text-sage">Grounding Engine Online</p>
                          <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
                            FalkorDB and Qdrant multi-stage RAG indexed.
                          </p>
                        </div>
                        <div className="rounded-lg border border-brass/25 bg-brass/10 p-3">
                          <p className="text-[13px] font-semibold text-brass">Statute Corpus Active</p>
                          <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
                            BNS, BNSS, BSA, and IT Act loaded into vector memory.
                          </p>
                        </div>
                      </div>
                    </motion.div>
                  </>
                )}
              </AnimatePresence>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
