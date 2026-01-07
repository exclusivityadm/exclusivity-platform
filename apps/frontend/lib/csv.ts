/**
 * CSV download helper
 * Canonical, TS-safe, non-iterable-based implementation
 */

export function downloadCsv(
  filename: string,
  rows: Array<Record<string, any>>
): void {
  if (!rows || rows.length === 0) return;

  // Collect headers deterministically
  const headerMap: Record<string, true> = {};

  for (const row of rows) {
    if (!row) continue;
    for (const key of Object.keys(row)) {
      headerMap[key] = true;
    }
  }

  const headers = Object.keys(headerMap);

  const escape = (value: any): string => {
    const s = value == null ? "" : String(value);
    if (s.includes('"') || s.includes(",") || s.includes("\n")) {
      return `"${s.replace(/"/g, '""')}"`;
    }
    return s;
  };

  const lines: string[] = [];
  lines.push(headers.join(","));

  for (const row of rows) {
    const line = headers.map((h) => escape(row?.[h]));
    lines.push(line.join(","));
  }

  const blob = new Blob([lines.join("\n")], {
    type: "text/csv;charset=utf-8",
  });

  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  setTimeout(() => {
    URL.revokeObjectURL(url);
  }, 500);
}
