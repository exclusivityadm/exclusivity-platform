export const metadata = {
  title: "Exclusivity Dashboard",
  description: "Merchant console — system status, voice, and chain diagnostics",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{
        margin: 0,
        fontFamily: "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial",
        background: "#0b0c10",
        color: "#e5e7eb"
      }}>
        {children}
      </body>
    </html>
  );
}
