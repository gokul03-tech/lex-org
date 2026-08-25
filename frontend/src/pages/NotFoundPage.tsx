import { Link } from 'react-router-dom';
import { Scale, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-6 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full border border-brass/30 bg-brass/10">
        <Scale className="h-6 w-6 text-brass" strokeWidth={1.6} />
      </div>
      <h1 className="mt-6 select-none font-serif text-[120px] font-semibold leading-none tracking-tight text-primary/10">
        404
      </h1>
      <p className="-mt-6 font-serif text-2xl font-semibold tracking-tight">This chamber does not exist.</p>
      <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">
        The page you are looking for has been adjourned or never filed.
      </p>
      <Link to="/dashboard" className="mt-7">
        <Button variant="outline" className="gap-2 rounded-lg bg-card">
          <ArrowLeft className="h-4 w-4" /> Return to Dashboard
        </Button>
      </Link>
    </div>
  );
}
