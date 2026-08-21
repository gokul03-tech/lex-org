import * as React from 'react';
import { motion } from 'framer-motion';
import {
  FileText,
  BookOpen,
  Scale,
  Network,
  ShieldAlert,
  Download,
  MessageSquare,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export interface DockItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  count?: number;
}

interface DockProps {
  items: DockItem[];
  activeId: string;
  onSelect: (id: string) => void;
  onOpenChat?: () => void;
  onOpenCommand?: () => void;
  className?: string;
}

export function Dock({
  items,
  activeId,
  onSelect,
  onOpenChat,
  onOpenCommand,
  className,
}: DockProps) {
  return (
    <div
      className={cn(
        'fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-1.5 rounded-2xl border border-white/10 bg-slate-950/80 p-2 shadow-2xl backdrop-blur-xl',
        className
      )}
    >
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = item.id === activeId;

        return (
          <button
            key={item.id}
            onClick={() => onSelect(item.id)}
            className={cn(
              'group relative flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-medium transition-all duration-200',
              isActive
                ? 'bg-sky-500/20 text-sky-300 shadow-sm shadow-sky-500/10 border border-sky-500/30'
                : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
            )}
          >
            <Icon className="h-4 w-4 shrink-0 transition group-hover:scale-110" />
            <span className="font-sans hidden sm:inline">{item.label}</span>
            {item.count !== undefined && item.count > 0 && (
              <span className="ml-1 rounded-full bg-white/10 px-1.5 py-0.2 font-mono text-[10px] text-slate-300">
                {item.count}
              </span>
            )}
            {isActive && (
              <motion.div
                layoutId="dock-indicator"
                className="absolute -bottom-1 left-1/2 -translate-x-1/2 h-1 w-4 rounded-full bg-sky-400"
              />
            )}
          </button>
        );
      })}

      <div className="h-5 w-[1px] bg-white/10 mx-1" />

      {onOpenChat && (
        <button
          onClick={onOpenChat}
          className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-medium text-purple-300 bg-purple-500/10 border border-purple-500/20 hover:bg-purple-500/20 transition"
          title="Open AI Legal Assistant"
        >
          <MessageSquare className="h-4 w-4" />
          <span className="hidden md:inline font-sans">Ask LexOS</span>
        </button>
      )}
    </div>
  );
}

export default Dock;
