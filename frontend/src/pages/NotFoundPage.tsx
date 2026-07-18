import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center">
      <h1 className="text-6xl font-bold text-legal-navy">404</h1>
      <p className="mt-4 text-lg text-muted-foreground">Page not found</p>
      <Link to="/dashboard" className="mt-6 text-primary hover:underline">
        Return to Dashboard
      </Link>
    </div>
  );
}
