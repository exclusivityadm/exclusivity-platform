"use client";

export function HealthBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div
      className={[
        "inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs border",
        ok
          ? "bg-emerald-950/40 border-emerald-800 text-emerald-300"
          : "bg-red-950/40 border-red-800 text-red-300",
      ].join(" ")}
    >
      <span
        className={[
          "h-2 w-2 rounded-full",
          ok ? "bg-emerald-400" : "bg-red-400",
        ].join(" ")}
      />
      {label}
    </div>
  );
}
