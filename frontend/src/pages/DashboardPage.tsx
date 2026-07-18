export default function DashboardPage() {
  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold text-legal-navy">Dashboard</h1>
      <p className="mt-2 text-muted-foreground">
        Welcome to LexOrch-KG, your AI-powered legal advisory platform.
      </p>
      <div className="mt-8 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-lg border bg-card p-6 shadow-sm">
          <h3 className="font-semibold">Active Cases</h3>
          <p className="mt-2 text-3xl font-bold text-primary">0</p>
        </div>
        <div className="rounded-lg border bg-card p-6 shadow-sm">
          <h3 className="font-semibold">Reports Generated</h3>
          <p className="mt-2 text-3xl font-bold text-primary">0</p>
        </div>
        <div className="rounded-lg border bg-card p-6 shadow-sm">
          <h3 className="font-semibold">Documents Processed</h3>
          <p className="mt-2 text-3xl font-bold text-primary">0</p>
        </div>
      </div>
    </div>
  );
}
