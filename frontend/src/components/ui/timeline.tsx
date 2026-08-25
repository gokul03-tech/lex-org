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
      <div className="flex flex-col items-center justify-center p-8 text-center text-muted-foreground">
        <Calendar className="mb-2 h-7 w-7 opacity-50" strokeWidth={1.5} />
        <p className="text-sm font-medium">No chronological timeline entries recorded.</p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'relative space-y-5 pl-6 before:absolute before:bottom-2 before:left-[9px] before:top-2 before:w-px before:bg-gradient-to-b before:from-brass/60 before:via-border before:to-sage/50',
        className
      )}
    >
      {items.map((item, idx) => {
        const isLast = idx === items.length - 1;
        return (
          <div key={idx} className="group relative">
            <div
              className={cn(
                'absolute -left-6 top-1 flex h-5 w-5 items-center justify-center rounded-full border bg-card shadow-sm transition-transform duration-200 group-hover:scale-110',
                isLast ? 'border-sage/50 text-sage ring-4 ring-sage/10' : 'border-brass/50'
              )}
            >
              {isLast ? (
                <CheckCircle2 className="h-3 w-3" />
              ) : (
                <div className="h-1.5 w-1.5 rounded-full bg-brass" />
              )}
            </div>

            <div className="rounded-lg border border-border bg-card p-4 shadow-sm transition-all duration-200 hover:border-brass/40 hover:shadow-md">
              <div className="mb-1.5 flex items-center justify-between gap-2">
                <span className="rounded border border-primary/20 bg-primary/5 px-2 py-0.5 font-mono text-[11px] font-medium text-primary">
                  {item.date}
                </span>
                {item.page && (
                  <span className="inline-flex items-center gap-1 rounded border border-border bg-secondary px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
                    <FileText className="h-2.5 w-2.5" />
                    p.{item.page}
                  </span>
                )}
              </div>
              <p className="text-[13px] leading-relaxed text-foreground/85">{item.event}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default VerticalTimeline;
