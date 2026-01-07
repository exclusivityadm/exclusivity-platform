"use client";

import React from "react";

export function ActionModal(props: {
  open: boolean;
  title: string;
  preview: any | null;
  executing: boolean;
  execResult: any | null;
  error: string | null;
  onClose: () => void;
  onExecute: () => void;
}) {
  if (!props.open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl rounded-2xl border border-neutral-800 bg-neutral-950 p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-neutral-50">{props.title}</h3>
            <p className="text-xs text-neutral-400 mt-1">
              Preview → Approve → Execute (tier-gated)
            </p>
          </div>
          <button
            className="rounded-lg border border-neutral-800 px-3 py-1 text-sm text-neutral-200"
            onClick={props.onClose}
          >
            Close
          </button>
        </div>

        <div className="mt-4 space-y-3">
          {props.error && (
            <div className="rounded-lg border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">
              {props.error}
            </div>
          )}

          <div className="rounded-xl border border-neutral-800 bg-neutral-900/40 p-4">
            <div className="text-xs text-neutral-400">Preview</div>
            <div className="mt-2 text-sm text-neutral-200 whitespace-pre-wrap">
              {props.preview?.summary || props.preview?.message || "No preview available."}
            </div>

            {props.preview?.risk && (
              <div className="mt-3 text-xs text-neutral-400">
                <span className="text-neutral-300">Risk:</span> {props.preview.risk}
              </div>
            )}
            {props.preview?.cost_estimate && (
              <div className="mt-1 text-xs text-neutral-400">
                <span className="text-neutral-300">Cost:</span> {props.preview.cost_estimate}
              </div>
            )}
            {props.preview?.requires_plan && (
              <div className="mt-1 text-xs text-neutral-400">
                <span className="text-neutral-300">Requires:</span> {props.preview.requires_plan}
              </div>
            )}
          </div>

          {props.execResult && (
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/40 p-4">
              <div className="text-xs text-neutral-400">Execution</div>
              <div className="mt-2 text-sm text-neutral-200 whitespace-pre-wrap">
                {props.execResult?.message || (props.execResult?.ok ? "Executed." : "Failed.")}
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              className="rounded-lg border border-neutral-800 px-4 py-2 text-sm text-neutral-200"
              onClick={props.onClose}
            >
              Cancel
            </button>
            <button
              className="rounded-lg bg-white px-4 py-2 text-sm text-black disabled:opacity-60"
              disabled={props.executing}
              onClick={props.onExecute}
            >
              {props.executing ? "Executing…" : "Approve & Execute"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
