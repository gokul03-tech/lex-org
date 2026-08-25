import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-primary-foreground shadow-sm',
        secondary: 'border-border bg-secondary text-secondary-foreground',
        destructive: 'border-destructive/25 bg-destructive/10 text-destructive',
        outline: 'border-border bg-card text-muted-foreground',
        success: 'border-sage/30 bg-sage/10 text-sage',
        warning: 'border-brass/35 bg-brass/10 text-brass',
        statute: 'border-border bg-secondary text-muted-foreground font-mono',
        precedent: 'border-primary/20 bg-primary/5 text-primary font-mono',
        // Practice-area variants — Daylight Chambers colorful accents
        criminal: 'border-rose-200 bg-rose-50 text-rose-700',
        cybercrime: 'border-violet-200 bg-violet-50 text-violet-700',
        arbitration: 'border-amber-200 bg-amber-50 text-amber-800',
        constitutional: 'border-emerald-200 bg-emerald-50 text-emerald-800',
        civil: 'border-sky-200 bg-sky-50 text-sky-700',
      },
      size: {
        default: 'px-2.5 py-0.5 text-xs',
        sm: 'px-2 py-0.5 text-[11px]',
        lg: 'px-3.5 py-1 text-[13px]',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, size, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant, size }), className)} {...props} />;
}

export { Badge, badgeVariants };
