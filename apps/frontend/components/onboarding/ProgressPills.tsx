"use client";

export function ProgressPills({
  steps,
  index,
}: {
  steps: string[];
  index: number;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {steps.map((s, i) => (
        <span
          key={s}
          className={`px-3 py-1 rounded-full text-xs border ${
            i === index
              ? "bg-neutral-50 text-neutral-950 border-neutral-50"
              : "bg-neutral-900 border-neutral-700 text-neutral-300"
          }`}
        >
          {s}
        </span>
      ))}
    </div>
  );
}
