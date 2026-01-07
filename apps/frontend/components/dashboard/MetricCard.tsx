"use client";

export function MetricCard(props: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-950/40 p-4">
      <div className="text-xs text-neutral-400">{props.label}</div>
      <div className="mt-1 text-xl font-semibold text-neutral-50">
        {props.value}
      </div>
      {props.hint && (
        <div className="mt-1 text-xs text-neutral-500">{props.hint}</div>
      )}
    </div>
  );
}
