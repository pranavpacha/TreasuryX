import type { ReactNode } from "react";

export function Panel({ title, children, right }: { title: string; children: ReactNode; right?: ReactNode }) {
  return (
    <div className="panel">
      <div className="panel-title">
        <span>{title}</span>
        {right}
      </div>
      {children}
    </div>
  );
}

export function Metric({
  label, value, unit, sub, tone,
}: { label: string; value: string; unit?: string; sub?: string; tone?: "up" | "down" | "neutral" }) {
  return (
    <div className="metric">
      <div className="metric-label">{label}</div>
      <div className={`metric-value ${tone ?? ""}`}>
        {value}
        {unit && <span style={{ fontSize: 12, marginLeft: 4, color: "var(--text-mid)" }}>{unit}</span>}
      </div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  );
}

export function Tooltip({ text }: { text: string }) {
  return <span className="tooltip-icon" title={text}>?</span>;
}

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return <div className="loading-state">{label}</div>;
}

export function ErrorState({ message }: { message: string }) {
  return <div className="error-state">Error: {message}</div>;
}

export function EmptyState({ label = "No data available." }: { label?: string }) {
  return <div className="empty-state">{label}</div>;
}

export function Badge({ children, kind = "info" }: { children: ReactNode; kind?: "info" | "warn" | "sim" }) {
  return <span className={`badge badge-${kind}`}>{children}</span>;
}

export function fmtNumber(v: number, decimals = 2): string {
  return v.toLocaleString("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export function fmtInr(v: number): string {
  const abs = Math.abs(v);
  const sign = v < 0 ? "-" : "";
  if (abs >= 10_000_000) return `${sign}₹${(abs / 10_000_000).toFixed(2)}Cr`;
  if (abs >= 100_000) return `${sign}₹${(abs / 100_000).toFixed(2)}L`;
  return `${sign}₹${fmtNumber(abs, 0)}`;
}

export function toneFor(v: number): "up" | "down" | "neutral" {
  if (v > 0) return "up";
  if (v < 0) return "down";
  return "neutral";
}
