import { cn } from "@/lib/utils";
import { useState } from "react";

export const Component = () => {
  const [count, setCount] = useState(0);

  return (
    <div className={cn("flex flex-col items-center gap-4 p-4 rounded-lg bg-card/40 border border-white/10 backdrop-blur-md")}>
      <h1 className="text-2xl font-bold font-serif text-slate-100 mb-2">LexOS Feature Counter</h1>
      <h2 className="text-xl font-mono text-primary font-semibold">{count}</h2>
      <div className="flex gap-2">
        <button
          className="px-4 py-1.5 rounded-md bg-secondary hover:bg-secondary/80 text-sm font-medium transition"
          onClick={() => setCount((prev) => prev - 1)}
        >
          -
        </button>
        <button
          className="px-4 py-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 text-sm font-medium transition"
          onClick={() => setCount((prev) => prev + 1)}
        >
          +
        </button>
      </div>
    </div>
  );
};

export default Component;
