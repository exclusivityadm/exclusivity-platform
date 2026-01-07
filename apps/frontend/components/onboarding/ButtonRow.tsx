"use client";

export function ButtonRow(props: {
  backLabel?: string;
  nextLabel?: string;
  onBack?: () => void;
  onNext?: () => void;
  nextDisabled?: boolean;
  busy?: boolean;
}) {
  return (
    <div className="flex justify-between gap-3">
      <button
        onClick={props.onBack}
        className="px-4 py-2 rounded-xl border border-neutral-700 text-neutral-200 hover:bg-neutral-800"
      >
        {props.backLabel || "Back"}
      </button>

      <button
        onClick={props.onNext}
        disabled={props.nextDisabled || props.busy}
        className={`px-4 py-2 rounded-xl font-medium ${
          props.nextDisabled || props.busy
            ? "bg-neutral-700 text-neutral-300"
            : "bg-neutral-50 text-neutral-950 hover:bg-neutral-200"
        }`}
      >
        {props.busy ? "Working…" : props.nextLabel || "Continue"}
      </button>
    </div>
  );
}
