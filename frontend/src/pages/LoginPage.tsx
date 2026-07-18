export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-md rounded-lg border bg-card p-8 shadow-lg">
        <h1 className="text-2xl font-bold text-legal-navy">LexOrch-KG</h1>
        <p className="mt-1 text-sm text-muted-foreground">Sign in to your account</p>
        <form className="mt-6 space-y-4">
          <div>
            <label className="text-sm font-medium">Email</label>
            <input type="email" className="mt-1 w-full rounded-md border px-3 py-2" placeholder="advocate@example.com" />
          </div>
          <div>
            <label className="text-sm font-medium">Password</label>
            <input type="password" className="mt-1 w-full rounded-md border px-3 py-2" placeholder="Your password" />
          </div>
          <button type="submit" className="w-full rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90">
            Sign In
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-muted-foreground">
          Don't have an account? <a href="/register" className="text-primary hover:underline">Register</a>
        </p>
      </div>
    </div>
  );
}
