"use client";

import React from "react";

export function StepShell(props: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-neutral-950 text-neutral-50">
      <div className="w-full max-w-2xl p-6">
        <div className="rounded-2xl bg-neutral-900/60 border border-neutral-800 p-6">
          <h1 className="text-2xl font-semibold">{props.title}</h1>
          {props.subtitle && (
            <p className="mt-2 text-sm text-neutral-300">{props.subtitle}</p>
          )}
          <div className="mt-6 space-y-4">{props.children}</div>
          {props.footer && (
            <div className="mt-8 pt-6 border-t border-neutral-800 text-xs text-neutral-400">
              {props.footer}
            </div>
          )}
        </div>
        <div className="mt-4 text-xs text-neutral-500">
          Exclusivity is invisible to customers by design.
        </div>
      </div>
    </div>
  );
}
