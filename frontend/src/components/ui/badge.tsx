import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default:
          'border-transparent bg-primary text-primary-foreground shadow-sm hover:bg-primary/90',
        secondary:
          'border-slate-200 bg-slate-100 text-slate-700 hover:bg-slate-200',
        destructive:
          'border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100',
        outline: 'text-slate-700 border-slate-200 bg-white/80',
        success:
          'border-emerald-200 bg-emerald-50 text-emerald-700',
        warning:
          'border-amber-200 bg-amber-50 text-amber-700',
        statute:
          'border-sky-200 bg-sky-50 text-sky-700 font-mono',
        precedent:
          'border-purple-200 bg-purple-50 text-purple-700 font-mono',
        // Category Specific Daylight Chambers Variants
        criminal:
          'border-rose-200 bg-rose-50 text-rose-700 font-medium',
        cybercrime:
          'border-violet-200 bg-violet-50 text-violet-700 font-medium',
        arbitration:
          'border-amber-200 bg-amber-50 text-amber-800 font-medium',
        constitutional:
          'border-emerald-200 bg-emerald-50 text-emerald-800 font-medium',
        civil:
          'border-sky-200 bg-sky-50 text-sky-700 font-medium',
      },
      size: {
        default: 'px-2.5 py-0.5 text-xs',
        sm: 'px-2 py-0.5 text-[10px]',
        lg: 'px-3.5 py-1 text-sm',
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
  return (
    <div className={cn(badgeVariants({ variant, size }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
