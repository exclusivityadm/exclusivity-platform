export function downloadCsv(
  filename: string,
  rows: Array<Record<string, any>>
) {
  if (!rows || rows.length === 0) return;

  const headerSet: Record<string, true> = {};

  for (const row of rows) {
    if (!row) continue;
    for (const key of Object.keys(row)) {
      headerSet[key] = true;
    }
  }

  const headers = Object.keys(headerSet);

  const escape = (value: any) => {
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

  setTimeout(() => URL.revokeObjectURL(url), 500);
}
