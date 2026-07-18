export default function RegisterPage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-md rounded-lg border bg-card p-8 shadow-lg">
        <h1 className="text-2xl font-bold text-legal-navy">Create Account</h1>
        <p className="mt-1 text-sm text-muted-foreground">Register for LexOrch-KG</p>
        <form className="mt-6 space-y-4">
          <div>
            <label className="text-sm font-medium">Full Name</label>
            <input type="text" className="mt-1 w-full rounded-md border px-3 py-2" placeholder="John Doe" />
          </div>
          <div>
            <label className="text-sm font-medium">Email</label>
            <input type="email" className="mt-1 w-full rounded-md border px-3 py-2" placeholder="advocate@example.com" />
          </div>
          <div>
            <label className="text-sm font-medium">Password</label>
            <input type="password" className="mt-1 w-full rounded-md border px-3 py-2" placeholder="Min 8 characters" />
          </div>
          <div>
            <label className="text-sm font-medium">Role</label>
            <select className="mt-1 w-full rounded-md border px-3 py-2">
              <option value="advocate">Advocate</option>
              <option value="researcher">Researcher</option>
              <option value="student">Law Student</option>
            </select>
          </div>
          <button type="submit" className="w-full rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90">
            Register
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-muted-foreground">
          Already have an account? <a href="/login" className="text-primary hover:underline">Sign In</a>
        </p>
      </div>
    </div>
  );
}
