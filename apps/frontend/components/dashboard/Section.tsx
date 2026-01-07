"use client";

export function Section(props: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
      <div className="mb-3">
        <h2 className="text-lg font-semibold text-neutral-50">{props.title}</h2>
        {props.subtitle && (
          <p className="mt-1 text-xs text-neutral-400">{props.subtitle}</p>
        )}
      </div>
      <div className="space-y-3">{props.children}</div>
    </section>
  );
}
