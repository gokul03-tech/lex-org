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
        'fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-1.5 rounded-2xl border border-slate-200 bg-white/95 p-1.5 shadow-2xl backdrop-blur-xl max-w-[95vw] overflow-x-auto',
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
              'group relative flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-semibold transition-all duration-200 cursor-pointer whitespace-nowrap',
              isActive
                ? 'bg-sky-50 text-sky-800 shadow-xs border border-sky-200'
                : 'text-slate-600 hover:bg-slate-100/80 hover:text-slate-900'
            )}
          >
            <Icon className={cn('h-4 w-4 shrink-0 transition group-hover:scale-110', isActive ? 'text-sky-600' : 'text-slate-500')} />
            <span className="font-sans hidden sm:inline">{item.label}</span>
            {item.count !== undefined && item.count > 0 && (
              <span className={cn(
                'ml-1 rounded-md px-1.5 py-0.2 font-mono text-[10px]',
                isActive ? 'bg-sky-100 text-sky-800' : 'bg-slate-100 text-slate-500'
              )}>
                {item.count}
              </span>
            )}
            {isActive && (
              <motion.div
                layoutId="dock-indicator"
                className="absolute -bottom-1 left-1/2 -translate-x-1/2 h-1 w-4 rounded-full bg-sky-600"
              />
            )}
          </button>
        );
      })}

      <div className="h-5 w-[1px] bg-slate-200 mx-1" />

      {onOpenChat && (
        <button
          onClick={onOpenChat}
          className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold text-purple-800 bg-purple-50 border border-purple-200 hover:bg-purple-100 transition shadow-2xs cursor-pointer whitespace-nowrap"
          title="Open AI Legal Assistant"
        >
          <MessageSquare className="h-4 w-4 text-purple-600" />
          <span className="hidden md:inline font-sans">Ask LexOS</span>
        </button>
      )}
    </div>
  );
}

export default Dock;
