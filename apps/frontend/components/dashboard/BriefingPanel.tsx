"use client";

import { Section } from "./Section";

export function BriefingPanel({
  briefing,
}: {
  briefing: any | null;
}) {
  if (!briefing) {
    return (
      <Section title="Daily Briefing">
        <div className="text-sm text-neutral-400">
          No briefing available yet.
        </div>
      </Section>
    );
  }

  const summary: string[] = briefing.summary || [];

  return (
    <Section
      title="Daily Briefing"
      subtitle="AI-generated merchant intelligence"
    >
      {summary.length === 0 ? (
        <div className="text-sm text-neutral-400">No insights yet.</div>
      ) : (
        <ul className="list-disc pl-5 space-y-1 text-sm text-neutral-200">
          {summary.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      )}
    </Section>
  );
}
