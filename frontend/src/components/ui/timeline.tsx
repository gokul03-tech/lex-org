import * as React from 'react';
import { Calendar, CheckCircle2, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface TimelineItem {
  date: string;
  event: string;
  page?: number | string;
  source?: string;
}

interface VerticalTimelineProps {
  items: TimelineItem[];
  className?: string;
}

export function VerticalTimeline({ items, className }: VerticalTimelineProps) {
  if (!items || items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center text-slate-400">
        <Calendar className="h-8 w-8 mb-2 stroke-1 opacity-50 text-slate-400" />
        <p className="text-sm font-medium">No chronological timeline entries recorded.</p>
      </div>
    );
  }

  return (
    <div className={cn('relative space-y-5 pl-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-[2px] before:bg-gradient-to-b before:from-sky-500 before:via-indigo-300 before:to-emerald-400', className)}>
      {items.map((item, idx) => {
        const isLast = idx === items.length - 1;
        return (
          <div key={idx} className="group relative">
            {/* Timeline Node Icon */}
            <div className={cn(
              'absolute -left-6 top-1 flex h-5 w-5 items-center justify-center rounded-full border bg-white transition-all duration-300 shadow-2xs',
              isLast
                ? 'border-emerald-500 text-emerald-600 ring-2 ring-emerald-100'
                : 'border-sky-500 text-sky-600 group-hover:scale-110'
            )}>
              {isLast ? (
                <CheckCircle2 className="h-3.5 w-3.5" />
              ) : (
                <div className="h-2 w-2 rounded-full bg-sky-600" />
              )}
            </div>

            {/* Event Content Card in Daylight Chambers light styling */}
            <div className="rounded-2xl border border-slate-200/80 bg-white/90 p-4 shadow-xs backdrop-blur-xs transition duration-200 hover:border-slate-300 hover:shadow-md">
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <span className="font-mono text-xs font-bold text-sky-800 bg-sky-50 px-2 py-0.5 rounded-md border border-sky-100">
                  {item.date}
                </span>
                {item.page && (
                  <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 font-mono text-[10px] text-slate-600 border border-slate-200 font-medium">
                    <FileText className="h-2.5 w-2.5" />
                    p.{item.page}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-700 leading-relaxed font-sans">
                {item.event}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default VerticalTimeline;
