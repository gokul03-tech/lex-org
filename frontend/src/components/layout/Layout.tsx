import { useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Briefcase,
  FileText,
  BarChart3,
  Settings,
  LogOut,
  Menu,
  X,
  Scale,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/cases', label: 'Cases', icon: Briefcase },
  { href: '/admin', label: 'Admin', icon: Settings },
];

export default function Layout() {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex min-h-screen">
      {/* Mobile sidebar toggle */}
      <button
        className="fixed left-4 top-4 z-50 rounded-md border p-2 lg:hidden"
        onClick={() => setSidebarOpen(!sidebarOpen)}
      >
        {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 w-64 transform border-r bg-card transition-transform duration-200 lg:relative lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex h-16 items-center gap-2 border-b px-6">
          <Scale className="h-6 w-6 text-legal-gold" />
          <span className="text-lg font-bold text-legal-navy">LexOrch-KG</span>
        </div>

        <nav className="mt-4 space-y-1 px-3">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.href || location.pathname.startsWith(item.href + '/');
            return (
              <Link
                key={item.href}
                to={item.href}
                className={cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )}
                onClick={() => setSidebarOpen(false)}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="absolute bottom-4 left-0 w-full px-6">
          <Button variant="ghost" className="w-full justify-start gap-3" onClick={() => {}}>
            <LogOut className="h-4 w-4" />
            Sign Out
          </Button>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b bg-background/95 backdrop-blur px-6">
          <div />
          <div className="flex items-center gap-4">
            <Link to="/dashboard">
              <Button variant="ghost" size="sm">
                <BarChart3 className="mr-2 h-4 w-4" />
                Dashboard
              </Button>
            </Link>
            <Link to="/cases">
              <Button variant="ghost" size="sm">
                <FileText className="mr-2 h-4 w-4" />
                Cases
              </Button>
            </Link>
          </div>
        </header>
        <Outlet />
      </main>
    </div>
  );
}
