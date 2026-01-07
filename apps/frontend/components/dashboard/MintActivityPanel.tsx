"use client";

import { Section } from "./Section";

export function MintActivityPanel({ jobs }: { jobs: any[] | null }) {
  return (
    <Section title="Blockchain Activity" subtitle="Recent mint jobs">
      {!jobs || jobs.length === 0 ? (
        <div className="text-sm text-neutral-400">
          No blockchain activity yet.
        </div>
      ) : (
        <ul className="space-y-2">
          {jobs.slice(0, 5).map((j) => (
            <li
              key={j.id}
              className="flex items-center justify-between rounded-lg border border-neutral-800 p-3"
            >
              <div className="text-sm">
                <span className="text-neutral-300">Status:</span>{" "}
                <span className="font-medium">{j.status}</span>
              </div>
              <div className="text-xs text-neutral-400">
                {j.created_at
                  ? new Date(j.created_at).toLocaleTimeString()
                  : "—"}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}
